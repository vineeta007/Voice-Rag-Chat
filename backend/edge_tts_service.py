"""
Microsoft Edge Text-to-Speech Service
FREE, high-quality, natural-sounding voices for English and Hindi
No authentication or billing required!
"""
import asyncio
import base64
import io
from typing import Optional
import edge_tts


class EdgeTTSService:
    def __init__(self):
        """Initialize Edge TTS - no setup needed!"""
        self.enabled = True
        print("✅ Microsoft Edge TTS initialized (FREE)")
    
    def get_voice_config(self, language: str) -> str:
        """
        Get the most natural, human-like voice for Edge TTS
        Returns: voice_name
        """
        voice_map = {
            # Premium quality voices from Microsoft Edge
            'English': 'en-US-AriaNeural',      # Female, warm, very natural
            'Hindi': 'hi-IN-SwaraNeural'        # Female, clear, natural Hindi
            
            # Alternative voices:
            # English: 'en-US-JennyNeural' (Female, friendly)
            #          'en-US-GuyNeural' (Male, professional)
            # Hindi:   'hi-IN-MadhurNeural' (Male, clear)
        }
        
        return voice_map.get(language, 'en-US-AriaNeural')
    
    async def _synthesize_async(
        self, 
        text: str, 
        voice: str,
        rate: str = "+0%",  # Normal speed
        pitch: str = "+0Hz"  # Normal pitch
    ) -> Optional[bytes]:
        """Async synthesis helper"""
        try:
            # Create Edge TTS communicator
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch
            )
            
            # Collect audio chunks
            audio_data = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.write(chunk["data"])
            
            return audio_data.getvalue()
        
        except Exception as e:
            print(f"❌ Edge TTS error: {e}")
            return None
    
    async def _synthesize_with_timings_async(
        self, 
        text: str, 
        voice: str,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> Optional[dict]:
        """Async synthesis with word-level timing information"""
        try:
            # Create Edge TTS communicator
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch
            )
            
            # Collect audio chunks and word boundaries
            audio_data = io.BytesIO()
            word_timings = []
            total_duration = 0.0
            
            async for chunk in communicate.stream():
                chunk_type = chunk.get("type", "unknown")
                
                if chunk_type == "audio":
                    audio_data.write(chunk["data"])
                elif chunk_type == "WordBoundary":
                    # Word boundaries (if available from Edge TTS)
                    offset_seconds = chunk["offset"] / 10_000_000
                    duration_seconds = chunk["duration"] / 10_000_000
                    
                    word_timings.append({
                        "word": chunk["text"],
                        "start": offset_seconds,
                        "end": offset_seconds + duration_seconds,
                        "textOffset": chunk["text_offset"],
                        "wordLength": chunk["word_length"]
                    })
                elif chunk_type == "SentenceBoundary":
                    # Track total duration from sentence boundary
                    offset_seconds = chunk["offset"] / 10_000_000
                    duration_seconds = chunk["duration"] / 10_000_000
                    total_duration = offset_seconds + duration_seconds
            
            # If no word boundaries were provided, estimate them
            if len(word_timings) == 0 and total_duration > 0:
                print(f"  ⚠️  No word boundaries from Edge TTS, estimating based on total duration: {total_duration:.2f}s")
                # Split text into words
                words = text.split()
                if len(words) > 0:
                    # Distribute time evenly across words (simple estimation)
                    time_per_word = total_duration / len(words)
                    current_time = 0.0
                    
                    for i, word in enumerate(words):
                        # Add slight pause between words (10% of word duration)
                        word_duration = time_per_word * 0.9
                        pause_duration = time_per_word * 0.1
                        
                        word_timings.append({
                            "word": word,
                            "start": current_time,
                            "end": current_time + word_duration,
                            "textOffset": text.find(word),
                            "wordLength": len(word)
                        })
                        
                        current_time += time_per_word
            
            print(f"  🎯 Total word timings: {len(word_timings)}")
            return {
                "audio": audio_data.getvalue(),
                "timings": word_timings
            }
        
        except Exception as e:
            print(f"❌ Edge TTS error: {e}")
            return None
    
    def synthesize_speech(
        self, 
        text: str, 
        language: str = 'English',
        speaking_rate: float = 1.0,
        pitch: float = 0.0
    ) -> Optional[str]:
        """
        Convert text to speech using Microsoft Edge TTS (SYNC wrapper)
        
        Args:
            text: Text to convert to speech
            language: Language name ('English' or 'Hindi')
            speaking_rate: Speed multiplier (1.0 = normal)
            pitch: Pitch adjustment (0.0 = normal)
        
        Returns:
            Base64-encoded audio data (MP3 format) or None if failed
        """
        if not self.enabled:
            return None
        
        try:
            # Clean text
            cleaned_text = text.replace('**', '').replace('*', '').replace('_', '')
            
            # Get voice
            voice = self.get_voice_config(language)
            
            # Convert rate to Edge TTS format (percentage)
            rate_percent = int((speaking_rate - 1.0) * 100)
            rate_str = f"{rate_percent:+d}%"
            
            # Convert pitch to Edge TTS format (Hz)
            pitch_hz = int(pitch * 50)
            pitch_str = f"{pitch_hz:+d}Hz"
            
            # Run async synthesis in a new event loop (for sync context)
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                # If we're already in an async context, this will fail
                # So we need to use a different approach
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._synthesize_async(cleaned_text, voice, rate_str, pitch_str)
                    )
                    audio_bytes = future.result()
            except RuntimeError:
                # No running loop, create new one
                audio_bytes = asyncio.run(
                    self._synthesize_async(cleaned_text, voice, rate_str, pitch_str)
                )
            
            if not audio_bytes:
                return None
            
            # Encode to base64
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            print(f"✅ Generated Edge TTS speech: '{text[:50]}...' in {language}")
            return audio_base64
        
        except Exception as e:
            print(f"❌ Edge TTS error: {e}")
            return None
    
    async def synthesize_speech_async(
        self, 
        text: str, 
        language: str = 'English',
        speaking_rate: float = 1.0,
        pitch: float = 0.0
    ) -> Optional[str]:
        """
        Convert text to speech using Microsoft Edge TTS (ASYNC version)
        Use this in async contexts like FastAPI endpoints
        """
        if not self.enabled:
            return None
        
        try:
            # Clean text
            cleaned_text = text.replace('**', '').replace('*', '').replace('_', '')
            
            # Get voice
            voice = self.get_voice_config(language)
            
            # Convert rate/pitch
            rate_percent = int((speaking_rate - 1.0) * 100)
            rate_str = f"{rate_percent:+d}%"
            pitch_hz = int(pitch * 50)
            pitch_str = f"{pitch_hz:+d}Hz"
            
            # Call async synthesis directly
            audio_bytes = await self._synthesize_async(cleaned_text, voice, rate_str, pitch_str)
            
            if not audio_bytes:
                return None
            
            # Encode to base64
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            print(f"✅ Generated Edge TTS speech: '{text[:50]}...' in {language}")
            return audio_base64
        
        except Exception as e:
            print(f"❌ Edge TTS error: {e}")
            return None
    
    async def synthesize_speech_with_timings_async(
        self, 
        text: str, 
        language: str = 'English',
        speaking_rate: float = 1.0,
        pitch: float = 0.0
    ) -> Optional[dict]:
        """
        Convert text to speech with word-level timing information
        Returns dict with 'audio' (base64) and 'timings' (word timing data)
        Use this for synced text-to-speech where words highlight as they're spoken
        """
        if not self.enabled:
            return None
        
        try:
            # Clean text
            cleaned_text = text.replace('**', '').replace('*', '').replace('_', '')
            
            # Get voice
            voice = self.get_voice_config(language)
            
            # Convert rate/pitch
            rate_percent = int((speaking_rate - 1.0) * 100)
            rate_str = f"{rate_percent:+d}%"
            pitch_hz = int(pitch * 50)
            pitch_str = f"{pitch_hz:+d}Hz"
            
            # Call async synthesis with timings
            result = await self._synthesize_with_timings_async(
                cleaned_text, voice, rate_str, pitch_str
            )
            
            if not result or not result["audio"]:
                return None
            
            # Encode audio to base64
            audio_base64 = base64.b64encode(result["audio"]).decode('utf-8')
            
            print(f"✅ Generated synced Edge TTS: '{text[:50]}...' with {len(result['timings'])} word timings")
            
            return {
                "audio": audio_base64,
                "timings": result["timings"],
                "format": "mp3"
            }
        
        except Exception as e:
            print(f"❌ Edge TTS sync error: {e}")
            return None


# Global Edge TTS service instance
edge_tts_service = EdgeTTSService()
