import asyncio
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from src.services.speech import LocalSpeechService, ISpeechService
from src.core.exceptions import SpeechServiceException


@pytest.fixture
def speech_service():
    return LocalSpeechService(
        whisper_model_path="tiny",
        piper_model_path="voice.onnx",
        piper_voice="voice"
    )


@pytest.mark.asyncio
async def test_transcribe_audio_file_not_found(speech_service):
    non_existent_file = Path("non_existent_file.wav")
    
    with pytest.raises(SpeechServiceException) as exc_info:
        await speech_service.transcribe_audio(non_existent_file)
        
    assert "Audio file does not exist" in exc_info.value.message


@pytest.mark.asyncio
async def test_transcribe_audio_success(speech_service, tmp_path):
    # Setup real audio file path in a temp directory
    audio_file_path = tmp_path / "user_response.wav"
    audio_file_path.write_bytes(b"dummy wav audio data")

    expected_txt_path = tmp_path / "user_response.txt"
    
    # Mock subprocess return code 0 and write the expected transcription text file
    mock_process = MagicMock()
    mock_process.returncode = 0
    
    async def mock_communicate():
        # Whisper writes the output txt file upon execution
        expected_txt_path.write_text("Hello, this is a transcribed response from mock whisper.", encoding="utf-8")
        return b"", b""
        
    mock_process.communicate = AsyncMock(side_effect=mock_communicate)

    with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
        transcript = await speech_service.transcribe_audio(audio_file_path)

        assert transcript == "Hello, this is a transcribed response from mock whisper."
        mock_exec.assert_called_once()
        called_args = mock_exec.call_args[0]
        assert called_args[0] == "whisper"
        assert called_args[1] == str(audio_file_path)
        assert "--model" in called_args
        assert "tiny" in called_args
        assert "--output_dir" in called_args
        assert str(tmp_path) in called_args
        assert "--output_format" in called_args
        assert "txt" in called_args

        # Ensure the transcript file was cleaned up/deleted
        assert not expected_txt_path.exists()


@pytest.mark.asyncio
async def test_transcribe_audio_subprocess_error(speech_service, tmp_path):
    audio_file_path = tmp_path / "user_response.wav"
    audio_file_path.write_bytes(b"dummy wav audio data")

    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.communicate = AsyncMock(return_value=(b"", b"Whisper model loading failed"))

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with pytest.raises(SpeechServiceException) as exc_info:
            await speech_service.transcribe_audio(audio_file_path)
            
        assert "Whisper transcription subprocess failed" in exc_info.value.message
        assert exc_info.value.details["return_code"] == 1
        assert "Whisper model loading failed" in exc_info.value.details["stderr"]


@pytest.mark.asyncio
async def test_transcribe_audio_file_missing_after_completion(speech_service, tmp_path):
    audio_file_path = tmp_path / "user_response.wav"
    audio_file_path.write_bytes(b"dummy wav audio data")

    mock_process = MagicMock()
    mock_process.returncode = 0
    # Do not write the transcript file to simulate whisper failing to output it
    mock_process.communicate = AsyncMock(return_value=(b"", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with pytest.raises(SpeechServiceException) as exc_info:
            await speech_service.transcribe_audio(audio_file_path)
            
        assert "Whisper completed but transcription output file not found" in exc_info.value.message


@pytest.mark.asyncio
async def test_synthesize_speech_disabled_returns_none(speech_service, tmp_path):
    with patch("src.config.settings.ENABLE_TTS", False):
        res = await speech_service.synthesize_speech("Hello", output_directory=tmp_path)
        assert res is None


@pytest.mark.asyncio
async def test_synthesize_speech_empty_text(speech_service, tmp_path):
    with patch("src.config.settings.ENABLE_TTS", True):
        with pytest.raises(SpeechServiceException) as exc_info:
            await speech_service.synthesize_speech("  ", output_directory=tmp_path)
            
        assert "Cannot synthesize empty text" in exc_info.value.message


@pytest.mark.asyncio
async def test_synthesize_speech_success(speech_service, tmp_path):
    text_to_speak = "Welcome to your AI voice interview."
    
    mock_process = MagicMock()
    mock_process.returncode = 0
    
    async def mock_communicate(input=None):
        return b"", b""

    mock_process.communicate = AsyncMock(side_effect=mock_communicate)

    with patch("src.config.settings.ENABLE_TTS", True):
        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            with patch("uuid.uuid4") as mock_uuid:
                mock_uuid_instance = MagicMock()
                mock_uuid_instance.hex = "fixed_uuid"
                mock_uuid.return_value = mock_uuid_instance
                
                expected_wav_file = tmp_path / "tts_fixed_uuid.wav"
                
                async def write_file_and_communicate(input=None):
                    expected_wav_file.write_bytes(b"RIFF dummy wav audio content")
                    return b"", b""
                    
                mock_process.communicate.side_effect = write_file_and_communicate
                
                result_path = await speech_service.synthesize_speech(text_to_speak, output_directory=tmp_path)

                assert result_path == expected_wav_file
                assert result_path.exists()
                assert result_path.stat().st_size > 0
                
                mock_exec.assert_called_once()
                called_args = mock_exec.call_args[0]
                assert called_args[0] == "piper"
                assert "--model" in called_args
                assert "voice.onnx" in called_args
                assert "--output_file" in called_args
                assert str(expected_wav_file) in called_args
                
                mock_process.communicate.assert_called_once_with(input=text_to_speak.encode("utf-8"))


@pytest.mark.asyncio
async def test_synthesize_speech_subprocess_error(speech_service, tmp_path):
    text_to_speak = "Welcome to your AI voice interview."
    
    mock_process = MagicMock()
    mock_process.returncode = -1
    mock_process.communicate = AsyncMock(return_value=(b"", b"Piper engine crash"))

    with patch("src.config.settings.ENABLE_TTS", True):
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(SpeechServiceException) as exc_info:
                await speech_service.synthesize_speech(text_to_speak, output_directory=tmp_path)
                
            assert "Piper speech synthesis subprocess failed" in exc_info.value.message
            assert exc_info.value.details["return_code"] == -1
            assert "Piper engine crash" in exc_info.value.details["stderr"]


@pytest.mark.asyncio
async def test_synthesize_speech_output_empty(speech_service, tmp_path):
    text_to_speak = "Welcome."
    
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"", b""))

    with patch("src.config.settings.ENABLE_TTS", True):
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(SpeechServiceException) as exc_info:
                await speech_service.synthesize_speech(text_to_speak, output_directory=tmp_path)
                
            assert "Piper completed but output audio file is missing or empty" in exc_info.value.message
