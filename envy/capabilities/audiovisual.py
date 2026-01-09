import requests
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class VoiceSynthesizer:
    """
    Implements 'The Voice' using XTTS-v2 (Text-to-Speech).
    Assumes a local XTTS server is running (e.g., via Docker).
    """
    def __init__(self, server_url: str = "http://localhost:8020"):
        self.server_url = server_url
        self.speaker_wav = "path/to/reference_voice.wav" # User's voice sample

    def speak(self, text: str, output_path: str = "output.wav") -> Optional[str]:
        """
        Sends text to the XTTS server and saves the audio.
        """
        try:
            payload = {
                "text": text,
                "speaker_wav": self.speaker_wav,
                "language_id": "en"
            }
            response = requests.post(f"{self.server_url}/tts_to_audio/", json=payload)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return output_path
            else:
                logger.error(f"TTS Error: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to connect to TTS server: {e}")
            return None

class AvatarAnimator:
    """
    Implements 'The Face' using LivePortrait.
    Assumes a local LivePortrait server is running.
    """
    def __init__(self, server_url: str = "http://localhost:8888"):
        self.server_url = server_url
        self.source_image = "path/to/user_photo.jpg"

    def animate(self, audio_path: str, output_video_path: str = "output.mp4") -> Optional[str]:
        """
        Sends audio to the LivePortrait server to animate the source image.
        """
        try:
            files = {'audio': open(audio_path, 'rb')}
            data = {'source_image': self.source_image}
            response = requests.post(f"{self.server_url}/animate", files=files, data=data)
            
            if response.status_code == 200:
                with open(output_video_path, "wb") as f:
                    f.write(response.content)
                return output_video_path
            else:
                logger.error(f"Avatar Error: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to connect to Avatar server: {e}")
            return None
