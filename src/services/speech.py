import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
import uuid

from src.config import settings
from src.core.exceptions import SpeechServiceException

logger = logging.getLogger(__name__)


class ISpeechService(ABC):
    """
    Handles local Speech-to-Text (Whisper) and Text-to-Speech (Piper) pipelines.
    Runs locally to preserve privacy and minimize third-party API exposure.
    """

    @abstractmethod
    async def transcribe_audio(self, audio_file_path: Path) -> str:
        """
        Transcribes incoming audio file (WAV/MP3) to text using Whisper.
        Returns the transcription string.
        """
        pass

    @abstractmethod
    async def synthesize_speech(self, text: str, output_directory: Path) -> Path:
        """
        Synthesizes spoken audio from text using Piper TTS.
        Saves output WAV file to output_directory and returns absolute Path.
        """
        pass


class LocalSpeechService(ISpeechService):
    """
    Concrete implementation of local speech service executing Whisper and Piper.
    Uses asyncio subprocess calls for performance and non-blocking execution.
    """

    def __init__(
        self,
        whisper_model_path: str = settings.WHISPER_MODEL_PATH,
        piper_model_path: str = settings.PIPER_MODEL_PATH,
        piper_voice: str = settings.PIPER_VOICE,
    ) -> None:
        self.whisper_model_path = whisper_model_path
        self.piper_model_path = piper_model_path
        self.piper_voice = piper_voice

    async def transcribe_audio(self, audio_file_path: Path) -> str:
        """
        Transcribes incoming audio using Groq Whisper API (fast) or local Whisper.
        """
        if not audio_file_path.exists():
            raise SpeechServiceException(
                message=f"Audio file does not exist: {audio_file_path}",
                details={"audio_file_path": str(audio_file_path)}
            )

        # 1. Use Groq Whisper API if API key is provided
        if settings.GROQ_API_KEY and not settings.MOCK_LLM:
            try:
                import httpx
                url = f"{settings.GROQ_BASE_URL.rstrip('/')}/audio/transcriptions"
                headers = {
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}"
                }
                logger.info(f"Submitting audio to Groq Whisper API: {audio_file_path}")
                async with httpx.AsyncClient(timeout=30.0) as client:
                    with open(audio_file_path, "rb") as audio_file:
                        files = {"file": (audio_file_path.name, audio_file, "audio/wav")}
                        data = {"model": "whisper-large-v3"}
                        response = await client.post(url, headers=headers, files=files, data=data)
                        response.raise_for_status()
                        result = response.json()
                        transcription = result.get("text", "").strip()
                        if transcription:
                            return transcription
            except Exception as e:
                logger.warning(f"Groq Whisper API failed ({e}), falling back to local transcription", exc_info=True)

        # 2. Local Whisper CLI fallback
        audio_dir = audio_file_path.parent
        cmd = [
            "whisper",
            str(audio_file_path),
            "--model",
            self.whisper_model_path,
            "--output_dir",
            str(audio_dir),
            "--output_format",
            "txt",
        ]

        try:
            logger.info(f"Running Whisper STT command: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                logger.error(f"Whisper subprocess failed with code {process.returncode}: {error_msg}")
                raise SpeechServiceException(
                    message="Whisper transcription subprocess failed",
                    details={"return_code": process.returncode, "stderr": error_msg}
                )

            txt_path = audio_dir / f"{audio_file_path.stem}.txt"
            if not txt_path.exists():
                alternative_txt_path = audio_dir / f"{audio_file_path.name}.txt"
                if alternative_txt_path.exists():
                    txt_path = alternative_txt_path
                else:
                    raise SpeechServiceException(
                        message="Whisper completed but transcription output file not found",
                        details={"expected_path": str(txt_path)}
                    )

            with open(txt_path, "r", encoding="utf-8") as f:
                transcription = f.read().strip()

            try:
                os.remove(txt_path)
            except Exception as e:
                logger.warning(f"Failed to clean up Whisper text file: {e}")

            return transcription

        except Exception as e:
            if isinstance(e, SpeechServiceException):
                raise
            logger.error("Unexpected error during Whisper transcription", exc_info=True)
            raise SpeechServiceException(
                message="Whisper transcription failed due to internal error",
                details={"original_error": str(e)}
            )

    async def synthesize_speech(self, text: str, output_directory: Path) -> Optional[Path]:
        """
        Synthesizes audio using Piper TTS CLI if ENABLE_TTS is True.
        If ENABLE_TTS is False, immediately returns None (disabling Piper TTS per design).
        """
        if not settings.ENABLE_TTS:
            logger.info("Piper TTS is disabled (ENABLE_TTS=False). Returning text-only response.")
            return None

        if not text.strip():
            raise SpeechServiceException(
                message="Cannot synthesize empty text",
                details={"text": text}
            )

        try:
            output_directory.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise SpeechServiceException(
                message="Failed to create output directory for TTS",
                details={"output_directory": str(output_directory), "original_error": str(e)}
            )

        output_file_path = output_directory / f"tts_{uuid.uuid4().hex}.wav"
        cmd = [
            "piper",
            "--model",
            self.piper_model_path,
            "--output_file",
            str(output_file_path),
        ]

        try:
            logger.info(f"Running Piper TTS command: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate(input=text.encode("utf-8"))

            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                logger.error(f"Piper subprocess failed with code {process.returncode}: {error_msg}")
                raise SpeechServiceException(
                    message="Piper speech synthesis subprocess failed",
                    details={"return_code": process.returncode, "stderr": error_msg}
                )

            if not output_file_path.exists() or output_file_path.stat().st_size == 0:
                raise SpeechServiceException(
                    message="Piper completed but output audio file is missing or empty",
                    details={"output_file_path": str(output_file_path)}
                )

            return output_file_path

        except Exception as e:
            if isinstance(e, SpeechServiceException):
                raise
            logger.error("Unexpected error during Piper synthesis", exc_info=True)
            raise SpeechServiceException(
                message="Piper speech synthesis failed due to internal error",
                details={"original_error": str(e)}
            )

