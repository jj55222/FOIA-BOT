#!/usr/bin/env python3
"""
LLM Transcript Processor with Scaffolded Prompts
Supports: OpenRouter, OpenAI, Anthropic
"""

import os
import json
import re
from typing import Dict, List, Optional


# ============================================
# PROMPT SCAFFOLDING
# ============================================

TRANSCRIPT_ANALYSIS_PROMPT = """You are a legal transcript analyst helping with investigative journalism.

<task>
Analyze this criminal case video transcript and extract structured information about:
1. Defendant names and key people
2. Time segments where court proceedings are discussed
3. Time segments where police evidence (bodycam, 911, interrogations) is discussed
4. Key topics and themes
</task>

<instructions>
Think step-by-step:
1. First, read through and identify all person names mentioned
2. Then, scan for any timestamps or time markers in the transcript
3. Categorize segments by content type (court/FOIA/general)
4. Extract key themes and topics
</instructions>

<examples>
Example 1 - Court Segment:
"At 5 minutes 30 seconds into the video, the narrator discusses the indictment, stating that the defendant was charged with first-degree murder..."
→ Classification: COURT segment from 00:05:30 to ~00:06:00

Example 2 - FOIA Segment:
"The bodycam footage, shown at the 12-minute mark, reveals the moment of arrest..."
→ Classification: FOIA segment from 00:12:00 to ~00:13:00

Example 3 - Name Extraction:
"The trial of John Smith and his co-defendant Michael Johnson..."
→ Defendants: ["John Smith", "Michael Johnson"]
</examples>

<transcript>
{transcript_text}
</transcript>

<output_format>
Return ONLY valid JSON in this exact structure:

{{
  "reasoning": "Brief explanation of what you found",
  "defendants": [
    {{"name": "Primary Defendant Name", "role": "defendant"}},
    {{"name": "Co-defendant Name", "role": "co-defendant"}}
  ],
  "court_segments": [
    {{
      "start_time": "00:05:30",
      "end_time": "00:08:45",
      "topic": "Indictment reading and charges",
      "keywords": ["indictment", "charges", "count I"]
    }}
  ],
  "foia_segments": [
    {{
      "start_time": "00:12:00",
      "end_time": "00:15:30",
      "topic": "Bodycam footage analysis",
      "keywords": ["bodycam", "arrest", "officer"]
    }}
  ],
  "key_topics": [
    {{"topic": "Murder charges", "importance": "high"}},
    {{"topic": "Police investigation", "importance": "medium"}}
  ],
  "summary": "One-sentence summary of the case"
}}
</output_format>

<guidelines>
- If no explicit timestamps exist, estimate based on content order
- Use "00:00:00" format for times
- List defendants by importance (primary first)
- Only include segments explicitly discussed in transcript
- Be conservative - only mark as COURT/FOIA if clearly relevant
</guidelines>

Now analyze the transcript and return the JSON:"""


# ============================================
# LLM PROVIDER ABSTRACTION
# ============================================

class LLMProvider:
    """Base class for LLM providers"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        raise NotImplementedError


class OpenRouterProvider(LLMProvider):
    """OpenRouter API (supports multiple models)"""

    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        super().__init__(api_key, model)

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        import requests

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/yourusername/FOIA-BOT",
                "X-Title": "FOIA-BOT Transcript Processor",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,  # Lower temp for more consistent extraction
            }
        )

        response.raise_for_status()
        data = response.json()

        return data['choices'][0]['message']['content']


class OpenAIProvider(LLMProvider):
    """OpenAI API"""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(api_key, model)

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        import openai

        client = openai.OpenAI(api_key=self.api_key)

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )

        return response.choices[0].message.content


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        super().__init__(api_key, model)

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)

        message = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text


# ============================================
# TRANSCRIPT PROCESSOR
# ============================================

def get_llm_provider(
    provider: str = "openrouter",
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> LLMProvider:
    """
    Get LLM provider instance

    Args:
        provider: "openrouter", "openai", or "anthropic"
        api_key: API key (if None, reads from environment)
        model: Model name (if None, uses default)

    Returns:
        LLMProvider instance
    """
    if api_key is None:
        env_keys = {
            "openrouter": "OPENROUTER_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY"
        }
        api_key = os.environ.get(env_keys.get(provider, "OPENROUTER_API_KEY"))

    if not api_key:
        raise ValueError(f"No API key found for {provider}. Set environment variable or pass api_key parameter.")

    providers = {
        "openrouter": OpenRouterProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }

    provider_class = providers.get(provider.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider}")

    if model:
        return provider_class(api_key, model)
    else:
        return provider_class(api_key)


def process_transcript_with_llm(
    transcript_text: str,
    provider: str = "openrouter",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_transcript_chars: int = 15000
) -> Optional[Dict]:
    """
    Process transcript using LLM with scaffolded prompt

    Args:
        transcript_text: Raw transcript text
        provider: "openrouter", "openai", or "anthropic"
        api_key: API key (optional, reads from env)
        model: Model name (optional, uses default)
        max_transcript_chars: Max chars to send (to manage costs)

    Returns:
        Structured dict with analysis results
    """
    print(f"🤖 Processing with {provider}")

    try:
        # Get provider
        llm = get_llm_provider(provider, api_key, model)

        # Truncate transcript if too long
        if len(transcript_text) > max_transcript_chars:
            print(f"⚠️  Truncating transcript from {len(transcript_text)} to {max_transcript_chars} chars")
            transcript_text = transcript_text[:max_transcript_chars]

        # Build prompt
        prompt = TRANSCRIPT_ANALYSIS_PROMPT.format(
            transcript_text=transcript_text
        )

        # Generate
        print(f"📤 Sending to LLM ({len(prompt)} chars)...")
        response = llm.generate(prompt, max_tokens=2048)
        print(f"📥 Received response ({len(response)} chars)")

        # Extract JSON from response
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)
        elif not response.strip().startswith('{'):
            # Try to find JSON anywhere in response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)

        # Parse JSON
        result = json.loads(response)

        # Validate structure
        if "defendants" in result and "court_segments" in result:
            print("✅ LLM processing successful")
            return result
        else:
            print("⚠️  LLM response missing required fields")
            return None

    except Exception as e:
        print(f"❌ LLM processing failed: {e}")
        return None


# ============================================
# RECOMMENDED MODEL CONFIGURATIONS
# ============================================

RECOMMENDED_MODELS = {
    "openrouter": {
        # Best value: Fast and cheap
        "cheap": "anthropic/claude-3-haiku",  # ~$0.25/million tokens
        # Best quality
        "quality": "anthropic/claude-3.5-sonnet",  # ~$3/million tokens
        # Alternative: OpenAI
        "openai-cheap": "openai/gpt-4o-mini",  # ~$0.15/million tokens
        "openai-quality": "openai/gpt-4o",  # ~$2.50/million tokens
    },
    "openai": {
        "cheap": "gpt-4o-mini",
        "quality": "gpt-4o",
    },
    "anthropic": {
        "cheap": "claude-3-haiku-20240307",
        "quality": "claude-3-5-sonnet-20241022",
    }
}


def get_recommended_model(provider: str, tier: str = "cheap") -> str:
    """Get recommended model for provider and tier"""
    return RECOMMENDED_MODELS.get(provider, {}).get(tier, "")


# ============================================
# USAGE EXAMPLES
# ============================================

if __name__ == '__main__':
    import sys

    # Example 1: OpenRouter (recommended)
    print("Example 1: Using OpenRouter with Claude 3 Haiku (cheap)")
    print("Cost: ~$0.0003 per video transcript")
    print()
    print("export OPENROUTER_API_KEY='your_key'")
    print("python llm_processor.py transcript.txt")
    print()

    # Example 2: OpenRouter with GPT-4o-mini (even cheaper)
    print("Example 2: OpenRouter with GPT-4o-mini (cheapest)")
    print("Cost: ~$0.0002 per video transcript")
    print()

    # Example 3: Direct Anthropic (more expensive)
    print("Example 3: Direct Anthropic API")
    print("Cost: ~$0.0008 per video transcript")
    print()

    # Show pricing comparison
    print("="*60)
    print("PRICING COMPARISON (per 15k char transcript):")
    print("="*60)
    print("OpenRouter + Haiku:     $0.0003 ⭐ RECOMMENDED")
    print("OpenRouter + GPT-4o-mini: $0.0002 ⭐ CHEAPEST")
    print("OpenRouter + Sonnet:    $0.0045")
    print("Direct Anthropic:       $0.0008")
    print("Direct OpenAI:          $0.0004")
    print()
    print("All are highly accurate for this use case!")
    print("OpenRouter gives you access to all models with one API key.")
