import os
import yt_dlp
from typing import Dict, Any, Callable, Optional

class YouTubeDownloader:
    """Handles downloading YouTube videos and extracting audio."""
    
    def __init__(self, temp_dir: str = "temp"):
        """Initialize the downloader with a temporary directory."""
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
    
    def validate_url(self, url: str) -> bool:
        """Validate if the URL is a valid YouTube URL."""
        if not url.startswith(('https://www.youtube.com/', 'https://youtu.be/', 'www.youtube.com/', 'youtu.be/')):
            return False
        
        # Try to fetch video info to verify the URL is valid
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                ydl.extract_info(url, download=False)
            return True
        except:
            return False
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video metadata without downloading."""
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'id': info.get('id'),
                'title': info.get('title'),
                'duration': info.get('duration'),
                'description': info.get('description'),
                'uploader': info.get('uploader'),
                'view_count': info.get('view_count')
            }
    
    def download_audio(self, url: str, progress_callback: Optional[Callable[[float, str], None]] = None) -> str:
        """
        Download only the audio from a YouTube video.
        
        Args:
            url: YouTube video URL
            progress_callback: Function to call with progress updates
            
        Returns:
            Path to the downloaded audio file
        """
        video_id = self.get_video_info(url)['id']
        output_file = os.path.join(self.temp_dir, f"{video_id}.mp3")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.temp_dir, f"{video_id}.%(ext)s"),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }
        
        if progress_callback:
            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent = d.get('_percent_str', '0%').strip()
                    try:
                        percent_float = float(percent.replace('%', '')) / 100
                    except:
                        percent_float = 0
                    progress_callback(percent_float, f"Downloading: {percent}")
                elif d['status'] == 'finished':
                    progress_callback(1.0, "Download complete, processing audio...")
            
            ydl_opts['progress_hooks'] = [progress_hook]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        return output_file
    
    def cleanup(self) -> None:
        """Remove temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            os.makedirs(self.temp_dir, exist_ok=True)