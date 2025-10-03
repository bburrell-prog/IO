#!/usr/bin/env python3
"""
ChatGPT API Client Module
Handles all communication with the OpenAI API.
"""
import requests
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ChatGPTClient:
    """A client for interacting with the OpenAI ChatGPT API."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        """Initializes the ChatGPT client."""
        if not api_key or not api_key.startswith('sk-'):
            raise ValueError("OpenAI API key is missing or invalid.")
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.model = model
        logger.info(f"ChatGPTClient initialized for model: {self.model}")

    def send_analysis(self, analysis_report: Dict) -> Optional[str]:
        """Formats and sends the screen analysis report to ChatGPT."""
        try:
            formatted_report = json.dumps(analysis_report, indent=2)
            
            system_prompt = (
                "You are an expert desktop automation assistant. Your task is to analyze a JSON "
                "report of a computer screen's content and generate a sequence of actions to "
                "accomplish a goal. The report includes text, UI elements, and their coordinates. "
                "Your response must be a clear, ordered list of actions like 'CLICK', 'TYPE', "
                "'PRESS', etc., with precise coordinates or text to interact with. Be concise and "
                "only output the actions."
            )
            
            user_prompt = (
                "Here is the screen analysis report. Your goal is to find the 'File' menu and click on it. "
                "Based on the report, what is the sequence of actions to perform this task?\n\n"
                f"{formatted_report}"
            )
            
            return self._make_api_request(system_prompt, user_prompt)

        except Exception as e:
            logger.error(f"Error sending analysis to ChatGPT: {e}", exc_info=True)
            return None

    def _make_api_request(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Makes the HTTP POST request to the OpenAI API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.5
        }
        
        try:
            logger.info("Sending request to OpenAI API...")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=90
            )
            response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
            
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content")
            
            if content:
                logger.info("Successfully received response from API.")
                return content.strip()
            else:
                logger.error(f"API response is empty or malformed: {result}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during API request: {e}", exc_info=True)
            return None

    def test_connection(self) -> bool:
        """Tests the connection to the OpenAI API."""
        logger.info("Testing OpenAI API connection...")
        response = self._make_api_request("You are a test assistant.", "Respond with 'OK'")
        if response and "OK" in response:
            logger.info("API connection successful.")
            return True
        else:
            logger.error("API connection test failed.")
            return False

