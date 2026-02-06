"""
Audio Utilities
Helper functions for audio format conversion and processing.
"""

import io
import logging
from typing import Optional, Literal

logger = logging.getLogger(__name__)

AudioFormat = Literal["wav", "mp3", "ogg", "webm"]


def convert_audio_format(
    audio_bytes: bytes,
    input_format: AudioFormat = "webm",
    output_format: AudioFormat = "wav",
    sample_rate: int = 16000
) -> Optional[bytes]:
    """
    Convert audio between formats.
    
    Args:
        audio_bytes: Input audio data
        input_format: Input format
        output_format: Output format
        sample_rate: Target sample rate for WAV
        
    Returns:
        Converted audio bytes or None if failed
    """
    try:
        from pydub import AudioSegment
        
        # Load audio
        audio = AudioSegment.from_file(
            io.BytesIO(audio_bytes),
            format=input_format
        )
        
        # Convert to mono if needed
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        # Set sample rate
        audio = audio.set_frame_rate(sample_rate)
        
        # Export
        output = io.BytesIO()
        audio.export(output, format=output_format)
        output.seek(0)
        
        logger.info(f"Converted audio: {input_format} -> {output_format}")
        return output.read()
        
    except ImportError:
        logger.error("pydub not installed for audio conversion")
        return None
    except Exception as e:
        logger.error(f"Audio conversion failed: {str(e)}")
        return None


def get_audio_duration(audio_bytes: bytes, format: AudioFormat = "wav") -> float:
    """
    Get duration of audio in seconds.
    
    Args:
        audio_bytes: Audio data
        format: Audio format
        
    Returns:
        Duration in seconds
    """
    try:
        from pydub import AudioSegment
        
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=format)
        return len(audio) / 1000.0  # milliseconds to seconds
        
    except Exception as e:
        logger.error(f"Failed to get audio duration: {str(e)}")
        return 0.0


def normalize_audio(
    audio_bytes: bytes,
    format: AudioFormat = "wav",
    target_dbfs: float = -20.0
) -> Optional[bytes]:
    """
    Normalize audio volume.
    
    Args:
        audio_bytes: Input audio data
        format: Audio format
        target_dbfs: Target decibels relative to full scale
        
    Returns:
        Normalized audio bytes
    """
    try:
        from pydub import AudioSegment
        
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=format)
        
        # Calculate adjustment needed
        change_in_dbfs = target_dbfs - audio.dBFS
        
        # Apply gain
        normalized = audio.apply_gain(change_in_dbfs)
        
        # Export
        output = io.BytesIO()
        normalized.export(output, format=format)
        output.seek(0)
        
        return output.read()
        
    except Exception as e:
        logger.error(f"Audio normalization failed: {str(e)}")
        return audio_bytes  # Return original if normalize fails
