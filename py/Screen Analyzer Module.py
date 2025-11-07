#!/usr/bin/env python3
"""
Screen Analysis Module
Handles screenshot capture and content analysis using OpenCV and Tesseract.
"""
import cv2
import pyautogui
import pytesseract
from pytesseract import Output
import time
import logging
from config import Config

logger = logging.getLogger(__name__)

class ScreenAnalyzer:
    """Captures and analyzes the content of the screen."""

    def __init__(self, config: Config):
        """Initializes the ScreenAnalyzer."""
        self.config = config
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Screen dimensions detected: {self.screen_width}x{self.screen_height}")

    def capture_screenshot(self) -> str:
        """Captures a screenshot of the entire screen."""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = self.config.screenshots_dir / filename
            
            filepath.parent.mkdir(exist_ok=True)
            
            # Temporarily disable failsafe for capture
            pyautogui.FAILSAFE = False
            
            # Try macOS-specific screenshot method first
            import platform
            if platform.system() == 'Darwin':  # macOS
                import subprocess
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    temp_path = tmp_file.name
                
                # Use macOS screencapture command
                subprocess.run(['screencapture', '-x', temp_path], check=True)
                
                # Load the image with PIL
                from PIL import Image
                screenshot = Image.open(temp_path)
                screenshot.save(filepath)
                
                # Clean up temp file
                import os
                os.unlink(temp_path)
            else:
                # Use PyAutoGUI for other platforms
                screenshot = pyautogui.screenshot()
                screenshot.save(filepath)
            
            pyautogui.FAILSAFE = True
            
            logger.info(f"Screenshot saved to: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}", exc_info=True)
            raise

    def analyze_screen(self, image_path: str) -> dict:
        """Analyzes a screenshot to extract text, UI elements, and interaction points."""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image from path: {image_path}")

            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Extract text and UI elements
            text_elements = self._extract_text_with_ocr(gray_image)
            ui_elements = self._detect_ui_elements(gray_image)

            # Compile the final report
            report = {
                "timestamp": time.time(),
                "screen_dimensions": {"width": self.screen_width, "height": self.screen_height},
                "elements": {
                    "text": text_elements,
                    **ui_elements
                }
            }
            
            report["interaction_points"] = self._find_interaction_points(report["elements"])
            report["summary"] = self._generate_summary(report)
            
            return report

        except Exception as e:
            logger.error(f"Error analyzing screen: {e}", exc_info=True)
            raise

    def _extract_text_with_ocr(self, image) -> list:
        """Uses Tesseract OCR to find and extract text from an image."""
        logger.info("Extracting text with Tesseract OCR...")
        ocr_data = pytesseract.image_to_data(image, output_type=Output.DICT, config=self.config.get_tesseract_config()['config'])
        
        text_elements = []
        n_boxes = len(ocr_data['level'])
        for i in range(n_boxes):
            conf = int(ocr_data['conf'][i])
            if conf > self.config.ocr_confidence_threshold:
                text = ocr_data['text'][i].strip()
                if text:
                    (x, y, w, h) = (ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i])
                    text_elements.append({
                        "type": "text",
                        "text": text,
                        "coordinates": {"x": x, "y": y, "width": w, "height": h},
                        "confidence": conf
                    })
        logger.info(f"Found {len(text_elements)} text elements.")
        return text_elements

    def _detect_ui_elements(self, gray_image) -> dict:
        """Uses OpenCV to detect basic UI elements like buttons and windows."""
        logger.info("Detecting UI elements with OpenCV...")
        # Basic contour detection for buttons/windows
        blurred = cv2.GaussianBlur(gray_image, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        buttons = []
        windows = []

        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
            x, y, w, h = cv2.boundingRect(approx)

            # Filter based on size and aspect ratio
            if w > 20 and h > 10 and 100 > w > 20 and 50 > h > 10:
                 buttons.append({
                    "type": "button",
                    "coordinates": {"x": x, "y": y, "width": w, "height": h}
                })
            elif w > 100 and h > 100:
                windows.append({
                    "type": "window",
                    "coordinates": {"x": x, "y": y, "width": w, "height": h}
                })
        
        logger.info(f"Detected {len(buttons)} potential buttons and {len(windows)} potential windows.")
        return {"buttons": buttons, "windows": windows, "icons": []} # Icons would need more advanced detection

    def _find_interaction_points(self, elements: dict) -> list:
        """Identifies potential points of interaction from detected elements."""
        interaction_points = []
        # Add text elements as clickable points
        for text_elem in elements.get("text", []):
            coords = text_elem["coordinates"]
            interaction_points.append({
                "type": "text_click",
                "description": f"Click text: '{text_elem['text']}'",
                "coordinates": (coords['x'] + coords['width'] // 2, coords['y'] + coords['height'] // 2)
            })
        # Add buttons as clickable points
        for button in elements.get("buttons", []):
            coords = button["coordinates"]
            interaction_points.append({
                "type": "button_click",
                "description": "Click button",
                "coordinates": (coords['x'] + coords['width'] // 2, coords['y'] + coords['height'] // 2)
            })
        return interaction_points

    def _generate_summary(self, report: dict) -> str:
        """Generates a human-readable summary of the analysis."""
        dims = report['screen_dimensions']
        counts = {key: len(value) for key, value in report['elements'].items()}
        
        summary = (
            f"Screen resolution: {dims['width']}x{dims['height']}. "
            f"Detected elements: {counts.get('text', 0)} text blocks, {counts.get('buttons', 0)} buttons, "
            f"{counts.get('windows', 0)} windows. "
            f"Found {len(report['interaction_points'])} potential interaction points."
        )
        return summary