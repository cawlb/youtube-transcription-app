# YouTube Video Transcription App

A desktop application that allows users to transcribe YouTube videos using OpenAI's Whisper model.

## Features

- Transcribe YouTube videos by URL
- Automatic language detection
- Progress tracking for download and transcription
- Save transcriptions to your local file system

## Installation

1. Ensure you have Python 3.8+ installed
2. Install FFmpeg (required for audio processing)
3. Clone this repository
4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```
python app.py
```

## Dependencies

- OpenAI Whisper - For transcription
- yt-dlp - For YouTube video downloading
- FFmpeg - For audio processing
- PyQt6 - For the GUI interface