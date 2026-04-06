"""
Google Cloud Text-to-Speech Service
Provides professional, natural-sounding voices for English and Hindi
"""
import os
import base64
from typing import Optional
from google.cloud import texttospeech


class TTSService:
    def __init__(self):
        """Initialize Google Cloud TTS client"""
        # Note: Requires GOOGLE_APPLICATION_CREDENTIALS environment variable
        # or service account key file
        try:
            self.client = texttospeech.TextToSpeechClient()
            # Test if TTS is actually working (check billing)
            try:
                test_input = texttospeech.SynthesisInput(text="test")
                test_voice = texttospeech.VoiceSelectionParams(
                    language_code='en-US',
                    name='en-US-Standard-A'
                )
                test_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3
                )
                # Try a test synthesis
                self.client.synthesize_speech(
                    input=test_input,
                    voice=test_voice,
                    audio_config=test_config
                )
                self.enabled = True
                print("✅ Google Cloud TTS initialized and verified successfully")
            except Exception as test_error:
                if "BILLING_DISABLED" in str(test_error) or "403" in str(test_error):
                    print("⚠️ Google Cloud TTS requires billing to be enabled")
                    print("   Voice will fall back to browser TTS (free)")
                    self.enabled = False
                else:
                    raise test_error
        except Exception as e:
            print(f"⚠️ Google Cloud TTS not available: {e}")
            print("   Voice will fall back to browser TTS")
            self.enabled = False
    
    def get_voice_config(self, language: str) -> tuple:
        """
        Get the most natural, human-like voice
        Using Studio/Wavenet voices - Google's best voices
        Returns: (language_code, voice_name)
        """
        voice_map = {
            # Studio voices - Most natural and expressive
            'English': ('en-US', 'en-US-Studio-O'),     # Female, warm, very natural
            'Hindi': ('hi-IN', 'hi-IN-Wavenet-D')       # Female, clear, natural
        }
        
        lang_code, voice_name = voice_map.get(language, ('en-US', 'en-US-Studio-O'))
        return lang_code, voice_name
    
    def synthesize_speech(
        self, 
        text: str, 
        language: str = 'English',
        speaking_rate: float = 1.0,   # Normal speed for better sync
        pitch: float = 0.0             # Natural pitch
    ) -> Optional[str]:
        """
        Convert text to speech using Google Cloud TTS with natural settings
        
        Args:
            text: Text to convert to speech
            language: Language name ('English' or 'Hindi')
            speaking_rate: Speed (1.0 = natural, conversational)
            pitch: Pitch adjustment (0.0 = natural)
        
        Returns:
            Base64-encoded audio data (MP3 format) or None if failed
        """
        if not self.enabled:
            return None
        
        try:
            # Clean text to prevent TTS from reading punctuation marks
            # Remove or normalize problematic patterns
            cleaned_text = text
            
            # Remove markdown-style formatting
            cleaned_text = cleaned_text.replace('**', '')
            cleaned_text = cleaned_text.replace('__', '')
            cleaned_text = cleaned_text.replace('*', '')
            cleaned_text = cleaned_text.replace('_', '')
            
            # Normalize punctuation - keep only basic punctuation
            # This prevents TTS from saying "exclamation point" or "question mark"
            import re
            # Remove multiple punctuation marks (e.g., "!!" -> "!")
            cleaned_text = re.sub(r'([!?.])\1+', r'\1', cleaned_text)
            
            # Remove special characters that TTS might read literally
            cleaned_text = re.sub(r'[#@$%^&*()_+=\[\]{}|\\<>~`]', '', cleaned_text)
            
            # Get voice configuration
            lang_code, voice_name = self.get_voice_config(language)
            
            # Set up the synthesis input with cleaned text
            synthesis_input = texttospeech.SynthesisInput(text=cleaned_text)
            
            # Build the voice request with Studio/Wavenet voice
            voice = texttospeech.VoiceSelectionParams(
                language_code=lang_code,
                name=voice_name
            )
            
            # Select the audio configuration for natural, friendly speech
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,  # Natural conversational speed
                pitch=pitch,                   # Natural pitch
                volume_gain_db=0.0,
                effects_profile_id=['headphone-class-device']  # Best quality
            )
            
            # Perform the text-to-speech request
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Encode audio to base64
            audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
            
            print(f"✅ Generated speech for '{text[:50]}...' in {language}")
            return audio_base64
        
        except Exception as e:
            print(f"❌ TTS error: {e}")
            return None


# Global TTS service instance
tts_service = TTSService()
