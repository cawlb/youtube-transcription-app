import os
import whisper
import torch
from typing import Callable, Optional, Dict, List, Union
from pydub import AudioSegment

class WhisperTranscriber:
    """Handles transcription of audio files using OpenAI's Whisper model."""
    
    def __init__(self, model_name: str = "base"):
        """
        Initialize the transcriber with a Whisper model.
        
        Args:
            model_name: Size of the Whisper model to use 
                        (tiny, base, small, medium, large)
        """
        self.model_name = model_name
        self.model = None
        # Deferred loading of model to save resources until needed
    
    def _load_model(self):
        """Load the Whisper model on first use."""
        if self.model is None:
            self.model = whisper.load_model(self.model_name)
    
    def _segment_audio(self, audio_path: str, segment_length_ms: int = 10 * 60 * 1000) -> List[str]:
        """
        Segment large audio files into smaller chunks.
        
        Args:
            audio_path: Path to the audio file
            segment_length_ms: Length of each segment in milliseconds
            
        Returns:
            List of paths to temporary segment files
        """
        audio = AudioSegment.from_file(audio_path)
        total_length_ms = len(audio)
        
        # If the audio is shorter than the segment length, return the original
        if total_length_ms <= segment_length_ms:
            return [audio_path]
        
        # Create temp directory for segments if it doesn't exist
        segments_dir = os.path.join(os.path.dirname(audio_path), "segments")
        os.makedirs(segments_dir, exist_ok=True)
        
        # Split and save segments
        segment_paths = []
        for i in range(0, total_length_ms, segment_length_ms):
            end = min(i + segment_length_ms, total_length_ms)
            segment = audio[i:end]
            segment_path = os.path.join(segments_dir, f"segment_{i}_{end}.mp3")
            segment.export(segment_path, format="mp3")
            segment_paths.append(segment_path)
        
        return segment_paths
    
    def transcribe(
        self, 
        audio_path: str, 
        progress_callback: Optional[Callable[[float, str], None]] = None,
        include_timestamps: bool = False
    ) -> Union[str, Dict]:
        """
        Transcribe an audio file.
        
        Args:
            audio_path: Path to the audio file
            progress_callback: Function to call with progress updates
            include_timestamps: Whether to include timestamps in the output
            
        Returns:
            If include_timestamps is True, returns a dict with 'text' and 'segments'.
            Otherwise, returns just the transcribed text as a string.
        """
        self._load_model()
        
        # Check if we need to segment the audio
        segment_paths = self._segment_audio(audio_path)
        
        # Process each segment and combine results
        full_text = ""
        segments_info = []
        
        for i, segment_path in enumerate(segment_paths):
            if progress_callback:
                progress = i / len(segment_paths)
                progress_callback(progress, f"Transcribing segment {i+1} of {len(segment_paths)}")
            
            # Transcribe the segment
            result = self.model.transcribe(segment_path)
            
            # Add to full text
            full_text += result["text"] + " "
            
            # Add segment info if needed
            if include_timestamps:
                for segment in result["segments"]:
                    # Adjust timestamp if not the first segment
                    if i > 0:
                        segment_ms = segment_paths[i-1].split("_")[2].split(".")[0]
                        offset = int(segment_ms) / 1000  # Convert ms to seconds
                        segment["start"] += offset
                        segment["end"] += offset
                    segments_info.append(segment)
        
        if progress_callback:
            progress_callback(1.0, "Transcription complete")
        
        # Clean up segment files if they were created
        if len(segment_paths) > 1:
            segments_dir = os.path.dirname(segment_paths[0])
            for path in segment_paths:
                if os.path.exists(path) and path != audio_path:
                    os.remove(path)
            os.rmdir(segments_dir)
        
        if include_timestamps:
            return {
                "text": full_text.strip(),
                "segments": segments_info
            }
        
        return full_text.strip()
    
    def format_with_timestamps(self, result: Dict) -> str:
        """
        Format transcription with timestamps.
        
        Args:
            result: The result from transcribe() with include_timestamps=True
            
        Returns:
            Formatted string with timestamps
        """
        text_with_timestamps = ""
        
        for segment in result["segments"]:
            start_time = self._format_time(segment["start"])
            end_time = self._format_time(segment["end"])
            text_with_timestamps += f"[{start_time} --> {end_time}] {segment['text']}\n"
        
        return text_with_timestamps
    
    def _format_time(self, seconds: float) -> str:
        """Convert seconds to formatted time string (HH:MM:SS)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"