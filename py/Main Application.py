#!/usr/bin/env python3
"""
Desktop Screen Analyzer with ChatGPT Integration
Main application entry point
"""
import sys
import time
import json
import logging
from pathlib import Path

# Import project modules
from screen_analyzer import ScreenAnalyzer
from chatgpt_client import ChatGPTClient
from action_executor import ActionExecutor
from config import Config

# Configure logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('desktop_analyzer.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class DesktopAnalyzer:
    """Orchestrates the screen analysis and action execution process."""
    def __init__(self):
        """Initializes all components of the analyzer."""
        self.config = Config()
        self.screen_analyzer = ScreenAnalyzer(self.config)
        self.chatgpt_client = ChatGPTClient(self.config.openai_api_key)
        self.action_executor = ActionExecutor(self.config)
        logger.info("Desktop Analyzer initialized.")

    def run_analysis_cycle(self):
        """Runs a single, complete analysis cycle."""
        try:
            logger.info("Starting new screen analysis cycle...")

            # 1. Capture and analyze the screen
            logger.info("Capturing screenshot...")
            screenshot_path = self.screen_analyzer.capture_screenshot()

            logger.info("Analyzing screen content...")
            analysis_report = self.screen_analyzer.analyze_screen(screenshot_path)

            # 2. Save the detailed analysis report
            report_path = self._save_analysis_report(analysis_report)
            logger.info(f"Analysis report saved to: {report_path}")

            # 3. Get insights from ChatGPT
            logger.info("Sending analysis to ChatGPT for action generation...")
            chatgpt_response = self.chatgpt_client.get_actions_from_report(analysis_report, screenshot_path)

            if chatgpt_response:
                logger.info("Received response from ChatGPT.")
                print("\n--- ChatGPT Proposed Actions ---\n")
                print(chatgpt_response)
                print("\n--------------------------------\n")

                # 4. Execute the actions
                self.action_executor.execute_from_response(chatgpt_response)
            else:
                logger.error("Failed to get a valid response from ChatGPT.")

        except Exception as e:
            logger.error(f"An error occurred during the analysis cycle: {e}", exc_info=True)

    def _save_analysis_report(self, report: dict) -> Path:
        """Saves the analysis report to a JSON file."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"screen_analysis_{timestamp}.json"
        filepath = self.config.reports_dir / filename
        
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        return filepath

    def run_interactive_mode(self):
        """Runs the analyzer in interactive mode, waiting for a key press."""
        try:
            import keyboard
        except ImportError:
            logger.error("The 'keyboard' library is not installed. Please run 'pip install keyboard'.")
            return

        logger.info("Starting interactive mode.")
        logger.info("Press 'F9' to trigger a screen analysis cycle.")
        logger.info("Press 'ESC' to exit.")

        try:
            while True:
                if keyboard.is_pressed('f9'):
                    self.run_analysis_cycle()
                    time.sleep(1)  # Debounce to prevent multiple triggers
                elif keyboard.is_pressed('esc'):
                    logger.info("Exit key pressed. Shutting down...")
                    break
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Interactive mode interrupted by user.")

def main():
    """Main entry point for the application."""
    try:
        analyzer = DesktopAnalyzer()
        # Run once if '--once' argument is provided, otherwise run in interactive mode
        if len(sys.argv) > 1 and sys.argv[1] == '--once':
            analyzer.run_analysis_cycle()
        else:
            analyzer.run_interactive_mode()
    except Exception as e:
        logger.critical(f"A critical error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

