import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QProgressBar, 
    QTextEdit, QFileDialog, QCheckBox, QComboBox,
    QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

from ..utils import YouTubeDownloader, WhisperTranscriber

class TranscriptionWorker(QThread):
    """Worker thread to handle the transcription process."""
    progress_updated = pyqtSignal(float, str)
    completed = pyqtSignal(str, str)  # transcription, output_path
    error = pyqtSignal(str)
    
    def __init__(self, url, output_dir, model_name, include_timestamps):
        super().__init__()
        self.url = url
        self.output_dir = output_dir
        self.model_name = model_name
        self.include_timestamps = include_timestamps
        self.downloader = YouTubeDownloader()
        self.transcriber = WhisperTranscriber(model_name=model_name)
    
    def run(self):
        try:
            # Validate URL
            if not self.downloader.validate_url(self.url):
                self.error.emit("Invalid YouTube URL")
                return
            
            # Get video info
            try:
                video_info = self.downloader.get_video_info(self.url)
                video_title = video_info.get('title', 'untitled')
            except Exception as e:
                self.error.emit(f"Error fetching video info: {str(e)}")
                return
            
            # Download audio
            self.progress_updated.emit(0.0, "Starting download...")
            try:
                audio_path = self.downloader.download_audio(
                    self.url, 
                    lambda p, msg: self.progress_updated.emit(p * 0.4, msg)
                )
            except Exception as e:
                self.error.emit(f"Error downloading video: {str(e)}")
                return
            
            # Transcribe audio
            self.progress_updated.emit(0.4, "Starting transcription...")
            try:
                if self.include_timestamps:
                    result = self.transcriber.transcribe(
                        audio_path,
                        lambda p, msg: self.progress_updated.emit(0.4 + (p * 0.6), msg),
                        include_timestamps=True
                    )
                    transcription = self.transcriber.format_with_timestamps(result)
                else:
                    transcription = self.transcriber.transcribe(
                        audio_path,
                        lambda p, msg: self.progress_updated.emit(0.4 + (p * 0.6), msg)
                    )
            except Exception as e:
                self.error.emit(f"Error during transcription: {str(e)}")
                return
            
            # Save output
            safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in video_title)
            output_path = os.path.join(self.output_dir, f"{safe_title}.txt")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(transcription)
            
            # Clean up temporary files
            self.downloader.cleanup()
            
            # Signal completion
            self.completed.emit(transcription, output_path)
            
        except Exception as e:
            self.error.emit(f"Unexpected error: {str(e)}")


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Transcription App")
        self.setMinimumSize(800, 600)
        
        self.init_ui()
    
    def init_ui(self):
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Input section
        input_group = QGroupBox("YouTube Video")
        input_layout = QVBoxLayout()
        
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("YouTube URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        url_layout.addWidget(self.url_input)
        input_layout.addLayout(url_layout)
        
        # Options section
        options_layout = QHBoxLayout()
        
        # Model selection
        model_layout = QVBoxLayout()
        model_layout.addWidget(QLabel("Whisper Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("base")
        model_layout.addWidget(self.model_combo)
        options_layout.addLayout(model_layout)
        
        # Output directory
        output_dir_layout = QVBoxLayout()
        output_dir_label = QLabel("Output Directory:")
        output_dir_layout.addWidget(output_dir_label)
        
        output_dir_select = QHBoxLayout()
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setText(os.path.join(os.path.expanduser("~"), "Downloads"))
        output_dir_select.addWidget(self.output_dir_input)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_output_dir)
        output_dir_select.addWidget(browse_button)
        output_dir_layout.addLayout(output_dir_select)
        options_layout.addLayout(output_dir_layout)
        
        # Timestamp option
        timestamp_layout = QVBoxLayout()
        timestamp_layout.addWidget(QLabel("Options:"))
        self.timestamp_checkbox = QCheckBox("Include timestamps")
        timestamp_layout.addWidget(self.timestamp_checkbox)
        options_layout.addLayout(timestamp_layout)
        
        input_layout.addLayout(options_layout)
        
        # Transcribe button
        self.transcribe_button = QPushButton("Transcribe")
        self.transcribe_button.setMinimumHeight(40)
        self.transcribe_button.clicked.connect(self.start_transcription)
        input_layout.addWidget(self.transcribe_button)
        
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
        
        # Output section
        output_group = QGroupBox("Transcription Output")
        output_layout = QVBoxLayout()
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier New", 10))
        output_layout.addWidget(self.output_text)
        
        # Output actions
        output_actions = QHBoxLayout()
        
        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.copy_button.setEnabled(False)
        output_actions.addWidget(self.copy_button)
        
        self.save_button = QPushButton("Save As...")
        self.save_button.clicked.connect(self.save_as)
        self.save_button.setEnabled(False)
        output_actions.addWidget(self.save_button)
        
        output_layout.addLayout(output_actions)
        output_group.setLayout(output_layout)
        
        main_layout.addWidget(output_group)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Initialize worker as None
        self.worker = None
        self.last_transcription = None
        self.last_output_path = None
    
    def browse_output_dir(self):
        """Open directory browser to select output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Output Directory",
            self.output_dir_input.text()
        )
        if dir_path:
            self.output_dir_input.setText(dir_path)
    
    def start_transcription(self):
        """Start the transcription process in a background thread."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a YouTube URL")
            return
        
        output_dir = self.output_dir_input.text()
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create output directory: {str(e)}")
                return
        
        model_name = self.model_combo.currentText()
        include_timestamps = self.timestamp_checkbox.isChecked()
        
        # Disable UI elements
        self.transcribe_button.setEnabled(False)
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.output_text.clear()
        
        # Reset progress
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting...")
        
        # Create and start worker thread
        self.worker = TranscriptionWorker(url, output_dir, model_name, include_timestamps)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.completed.connect(self.transcription_completed)
        self.worker.error.connect(self.transcription_error)
        self.worker.start()
    
    def update_progress(self, progress, message):
        """Update progress bar and status message."""
        self.progress_bar.setValue(int(progress * 100))
        self.status_label.setText(message)
    
    def transcription_completed(self, transcription, output_path):
        """Handle completion of transcription."""
        self.last_transcription = transcription
        self.last_output_path = output_path
        
        self.output_text.setText(transcription)
        self.status_label.setText(f"Transcription saved to: {output_path}")
        self.progress_bar.setValue(100)
        
        # Re-enable UI elements
        self.transcribe_button.setEnabled(True)
        self.copy_button.setEnabled(True)
        self.save_button.setEnabled(True)
        
        # Show success message
        QMessageBox.information(
            self, 
            "Transcription Complete",
            f"Transcription complete and saved to:\n{output_path}"
        )
    
    def transcription_error(self, error_message):
        """Handle errors during transcription."""
        QMessageBox.critical(self, "Error", error_message)
        self.status_label.setText(f"Error: {error_message}")
        self.progress_bar.setValue(0)
        self.transcribe_button.setEnabled(True)
    
    def copy_to_clipboard(self):
        """Copy transcription text to clipboard."""
        if self.last_transcription:
            clipboard = self.clipboard()
            clipboard.setText(self.last_transcription)
            self.status_label.setText("Copied to clipboard")
    
    def save_as(self):
        """Save transcription to a new file."""
        if not self.last_transcription:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Transcription",
            self.last_output_path,
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.last_transcription)
                self.status_label.setText(f"Saved to: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.worker and self.worker.isRunning():
            # Ask for confirmation before closing
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "A transcription is in progress. Are you sure you want to exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Terminate worker thread
                self.worker.terminate()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()