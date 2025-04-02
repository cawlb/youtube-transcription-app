#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.ui import MainWindow

def check_dependencies():
    """Check if required dependencies are installed."""
    print("Checking dependencies...")
    try:
        import whisper
        print("Whisper imported successfully")
        import yt_dlp
        print("yt-dlp imported successfully")
        import ffmpeg
        print("ffmpeg-python imported successfully")
    except ImportError as e:
        print(f"Error: Missing dependency - {str(e)}")
        print("Please install all required dependencies with: pip install -r requirements.txt")
        return False
        
    # Check if FFmpeg is installed
    try:
        import subprocess
        print("Checking FFmpeg executable...")
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("FFmpeg executable found")
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print(f"Error: FFmpeg check failed - {str(e)}")
        print("Please install FFmpeg and ensure it's in your system PATH.")
        return False
        
    print("All dependencies verified successfully")
    return True

def main():
    """Main application entry point."""
    print("Starting YouTube Transcription App...")
    
    # Check dependencies before starting
    if not check_dependencies():
        print("Dependency check failed. Exiting.")
        sys.exit(1)
        
    # Create application
    print("Initializing PyQt application...")
    app = QApplication(sys.argv)
    app.setApplicationName("YouTube Transcription App")
    app.setOrganizationName("YouTube Transcription App")
    
    # Create and show main window
    print("Creating main window...")
    window = MainWindow()
    print("Showing main window...")
    window.show()
    
    print("Entering Qt event loop...")
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()