#!/usr/bin/env python3
"""
Action Executor Module
Parses ChatGPT responses and executes mouse and keyboard actions.
"""
import pyautogui
import time
import re
import logging
from typing import List, Dict
from config import Config

logger = logging.getLogger(__name__)

class ActionExecutor:
    """Parses and executes automation actions."""
    
    def __init__(self, config: Config):
        """Initializes the ActionExecutor."""
        self.config = config
        pyautogui.PAUSE = self.config.action_delay
        pyautogui.FAILSAFE = True
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"ActionExecutor initialized with action delay {self.config.action_delay}s.")

    def execute_from_response(self, chatgpt_response: str):
        """Parses a response from ChatGPT and executes the found actions."""
        try:
            logger.info("Parsing ChatGPT response for actions...")
            actions = self._parse_actions(chatgpt_response)

            if not actions:
                logger.warning("No valid actions found in the response.")
                return

            logger.info(f"Found {len(actions)} actions to execute.")
            
            if not self.config.auto_execute_actions:
                print("--- PROPOSED ACTIONS ---")
                for i, action in enumerate(actions, 1):
                    print(f"{i}. {action}")
                
                confirm = input("Do you want to execute these actions? (y/n): ")
                if confirm.lower() != 'y':
                    logger.info("Execution cancelled by user.")
                    return
            
            for i, action in enumerate(actions, 1):
                logger.info(f"Executing action {i}/{len(actions)}: {action}")
                self._execute_single_action(action)
                time.sleep(0.5)

            logger.info("All actions executed successfully.")

        except Exception as e:
            logger.error(f"Failed to execute actions from response: {e}", exc_info=True)

    def _parse_actions(self, response: str) -> List[Dict]:
        """Uses regex to parse action commands from the response string."""
        actions = []
        # Regex for CLICK (X, Y)
        click_matches = re.findall(r'CLICK\s*\((\d+),\s*(\d+)\)', response, re.IGNORECASE)
        for match in click_matches:
            actions.append({"type": "click", "x": int(match[0]), "y": int(match[1])})

        # Regex for TYPE "some text"
        type_matches = re.findall(r'TYPE\s*"([^"]+)"', response, re.IGNORECASE)
        for match in type_matches:
            actions.append({"type": "type", "text": match})
            
        # Regex for PRESS "key"
        press_matches = re.findall(r'PRESS\s*"([^"]+)"', response, re.IGNORECASE)
        for match in press_matches:
            actions.append({"type": "press", "key": match.lower()})

        return actions

    def _execute_single_action(self, action: Dict):
        """Executes a single parsed action dictionary."""
        action_type = action.get("type")
        if action_type == "click":
            self._execute_click(action)
        elif action_type == "type":
            self._execute_type(action)
        elif action_type == "press":
            self._execute_press(action)
        else:
            logger.warning(f"Unknown action type: {action_type}")

    def _execute_click(self, action: Dict):
        """Performs a mouse click at the given coordinates."""
        x, y = action['x'], action['y']
        if 0 <= x < self.screen_width and 0 <= y < self.screen_height:
            logger.info(f"Clicking at ({x}, {y})")
            pyautogui.click(x, y)
        else:
            logger.warning(f"Click coordinates ({x}, {y}) are out of screen bounds.")

    def _execute_type(self, action: Dict):
        """Types the given text using the keyboard."""
        text = action['text']
        logger.info(f"Typing text: '{text}'")
        pyautogui.typewrite(text, interval=0.05)

    def _execute_press(self, action: Dict):
        """Presses a special key."""
        key = action['key']
        if key in pyautogui.KEYBOARD_KEYS:
            logger.info(f"Pressing key: {key}")
            pyautogui.press(key)
        else:
            logger.warning(f"Invalid key specified for PRESS action: {key}")

