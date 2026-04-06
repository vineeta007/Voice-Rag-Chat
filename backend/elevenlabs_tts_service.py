"""
ElevenLabs Text-to-Speech Service
Natural-sounding voices for English and Hindi.
"""
import asyncio
import base64
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import requests


class ElevenLabsTTSService:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        self.base_url = "https://api.elevenlabs.io/v1"
        self.model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

        # You can override these in .env for your preferred natural voices.
        self.voice_en = os.getenv("ELEVENLABS_VOICE_ID_EN", "EXAVITQu4vr4xnSDxMaL")
        self.voice_hi = os.getenv("ELEVENLABS_VOICE_ID_HI", "EXAVITQu4vr4xnSDxMaL")

        self.enabled = bool(self.api_key)
        if self.enabled:
            print("✅ ElevenLabs TTS initialized")
        else:
            print("⚠️ ElevenLabs TTS not configured (missing ELEVENLABS_API_KEY)")

    def get_voice_id(self, language: str) -> str:
        if language == "Hindi":
            return self.voice_hi
        return self.voice_en

    def _headers(self) -> Dict[str, str]:
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def _build_payload(self, text: str) -> Dict[str, Any]:
        return {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.8,
                "style": 0.25,
                "use_speaker_boost": True,
            },
        }

    def _estimate_word_timings(self, text: str, seconds_per_word: float = 0.38) -> List[Dict[str, Any]]:
        words = [w for w in re.split(r"\s+", text.strip()) if w]
        timings: List[Dict[str, Any]] = []
        current = 0.0
        for word in words:
            start = current
            end = start + seconds_per_word
            timings.append({
                "word": word,
                "start": start,
                "end": end,
                "textOffset": max(text.find(word), 0),
                "wordLength": len(word),
            })
            current = end
        return timings

    def _synthesize(self, text: str, language: str) -> Optional[bytes]:
        if not self.enabled:
            return None

        cleaned_text = text.replace("**", "").replace("*", "").replace("_", "")
        voice_id = self.get_voice_id(language)
        url = f"{self.base_url}/text-to-speech/{voice_id}"

        response = requests.post(
            url,
            headers=self._headers(),
            json=self._build_payload(cleaned_text),
            timeout=30,
        )

        if response.status_code != 200:
            print(f"❌ ElevenLabs TTS error {response.status_code}: {response.text[:300]}")
            return None

        return response.content

    def _synthesize_with_timestamps(self, text: str, language: str) -> Optional[Tuple[bytes, List[Dict[str, Any]]]]:
        if not self.enabled:
            return None

        cleaned_text = text.replace("**", "").replace("*", "").replace("_", "")
        voice_id = self.get_voice_id(language)
        url = f"{self.base_url}/text-to-speech/{voice_id}/with-timestamps"

        response = requests.post(
            url,
            headers=self._headers(),
            json=self._build_payload(cleaned_text),
            timeout=45,
        )

        if response.status_code != 200:
            print(f"❌ ElevenLabs TTS timestamp error {response.status_code}: {response.text[:300]}")
            audio_bytes = self._synthesize(cleaned_text, language)
            if not audio_bytes:
                return None
            return (audio_bytes, self._estimate_word_timings(cleaned_text))

        data = response.json()
        audio_b64 = data.get("audio_base64")
        if not audio_b64:
            return None

        audio_bytes = base64.b64decode(audio_b64)

        alignment = data.get("alignment") or data.get("normalized_alignment")
        if not alignment:
            return (audio_bytes, self._estimate_word_timings(cleaned_text))

        chars = alignment.get("chars", [])
        start_times = alignment.get("char_start_times_seconds", [])
        durations = alignment.get("char_durations_seconds", [])

        if not chars or not start_times:
            return (audio_bytes, self._estimate_word_timings(cleaned_text))

        # Build word timings from character-level alignment.
        timings: List[Dict[str, Any]] = []
        for match in re.finditer(r"\S+", cleaned_text):
            word = match.group(0)
            start_idx = match.start()
            end_idx = match.end() - 1

            if start_idx >= len(start_times):
                continue

            start = start_times[start_idx]
            if end_idx < len(start_times):
                end = start_times[end_idx]
                if end_idx < len(durations):
                    end += durations[end_idx]
                else:
                    end += 0.08
            else:
                end = start + 0.38

            if end <= start:
                end = start + 0.08

            timings.append({
                "word": word,
                "start": float(start),
                "end": float(end),
                "textOffset": start_idx,
                "wordLength": len(word),
            })

        if not timings:
            timings = self._estimate_word_timings(cleaned_text)

        return (audio_bytes, timings)

    async def synthesize_speech_async(
        self,
        text: str,
        language: str = "English",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> Optional[str]:
        _ = speaking_rate
        _ = pitch

        audio_bytes = await asyncio.to_thread(self._synthesize, text, language)
        if not audio_bytes:
            return None

        return base64.b64encode(audio_bytes).decode("utf-8")

    async def synthesize_speech_with_timings_async(
        self,
        text: str,
        language: str = "English",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        _ = speaking_rate
        _ = pitch

        result = await asyncio.to_thread(self._synthesize_with_timestamps, text, language)
        if not result:
            return None

        audio_bytes, timings = result
        return {
            "audio": base64.b64encode(audio_bytes).decode("utf-8"),
            "timings": timings,
            "format": "mp3",
        }

    def get_subscription_status(self) -> Optional[Dict[str, Any]]:
        """Fetch ElevenLabs account subscription and character usage."""
        if not self.enabled:
            return None

        try:
            url = f"{self.base_url}/user/subscription"
            response = requests.get(url, headers=self._headers(), timeout=10)

            if response.status_code != 200:
                print(f"❌ Failed to fetch subscription status {response.status_code}")
                return None

            data = response.json()
            characters_used = data.get("characters_used", 0)
            character_limit = data.get("character_limit", 0)
            remaining = character_limit - characters_used

            return {
                "tier": data.get("tier", "unknown"),
                "character_limit": character_limit,
                "characters_used": characters_used,
                "characters_remaining": remaining,
                "percentage_used": round((characters_used / character_limit * 100) if character_limit > 0 else 0, 1),
                "next_reset": data.get("next_character_reset_unix"),
            }
        except Exception as e:
            print(f"❌ Error fetching subscription: {str(e)}")
            return None


elevenlabs_tts_service = ElevenLabsTTSService()
