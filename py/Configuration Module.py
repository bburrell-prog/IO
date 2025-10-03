#!/usr/bin/env python3
"""
Configuration Module
Handles application configuration from environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    """Loads and validates application configuration from a .env file."""
    def __init__(self):
        """Loads environment variables and sets configuration attributes."""
        load_dotenv()

        # API Configuration
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')

        # Analysis Configuration
        self.ocr_confidence_threshold = int(os.getenv('OCR_CONFIDENCE_THRESHOLD', '30'))

        # Action Execution Configuration
        self.auto_execute_actions = os.getenv('AUTO_EXECUTE_ACTIONS', 'False').lower() == 'true'
        self.action_delay = float(os.getenv('ACTION_DELAY', '0.5'))

        # File Path Configuration
        self.screenshots_dir = Path(os.getenv('SCREENSHOTS_DIR', 'screenshots'))
        self.reports_dir = Path(os.getenv('REPORTS_DIR', 'reports'))
        self.logs_dir = Path(os.getenv('LOGS_DIR', 'logs'))
        
        self._create_directories()
        self._validate_config()

    def _create_directories(self):
        """Creates necessary directories if they don't exist."""
        for directory in [self.screenshots_dir, self.reports_dir, self.logs_dir]:
            directory.mkdir(exist_ok=True)

    def _validate_config(self):
        """Validates critical configuration settings."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        if not self.openai_api_key.startswith('sk-'):
            raise ValueError("OPENAI_API_KEY appears to be invalid.")

    def get_tesseract_config(self) -> dict:
        """Returns Tesseract OCR configuration."""
        return {
            'lang': os.getenv('TESSERACT_LANG', 'eng'),
            'config': os.getenv('TESSERACT_CONFIG', '--oem 3 --psm 6')
        }

