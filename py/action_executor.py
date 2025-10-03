"""
ActionExecutor implementation.
This file provides a robust ActionExecutor class that:
- Parses plain-text ChatGPT responses for actions (currently supports CLICK x,y patterns)
- Waits for confirmation (F10) unless AUTO_EXECUTE_ACTIONS=True in environment
- Executes actions using PyAutoGUI with a configurable delay

Note: This replaces the previous shim loader. If you prefer to keep the original
'Action Executor Module.py', we can revert to a shim approach instead.
"""
from __future__ import annotations
import os
import re
import time
import json
import glob
import logging
import random
from typing import List, Dict, Any, Optional

# Optional: lazy import GUI automation libraries so module can be imported on systems
# without GUI support when not executing actions.
try:
    import pyautogui
except Exception:  # pragma: no cover - runtime environment dependent
    pyautogui = None
try:
    import keyboard
except Exception:  # pragma: no cover
    keyboard = None

# Load environment via dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

LOG = logging.getLogger(__name__)

DEFAULT_ACTION_DELAY = float(os.getenv("ACTION_DELAY", "0.5"))
AUTO_EXECUTE = os.getenv("AUTO_EXECUTE_ACTIONS", "False").lower() in ("1", "true", "yes")
CONFIRM_KEY = os.getenv("CONFIRM_KEY", "F10")  # allow overriding confirm key via .env
CANCEL_KEY = os.getenv("CANCEL_KEY", "esc")
MAX_ACTIONS = int(os.getenv("EXECUTE_MAX_ACTIONS", "1"))
REPORTS_DIR = os.getenv("REPORTS_DIR", "reports")

class ActionExecutor:
    def __init__(self, action_delay: float | None = None):
        # action_delay may be:
        # - None -> use default
        # - a number or numeric string -> use that value
        # - a dict-like or object (e.g. Config) that provides ACTION_DELAY or action_delay
        resolved = None
        if action_delay is None:
            resolved = DEFAULT_ACTION_DELAY
        else:
            # try direct numeric conversion first
            try:
                resolved = float(action_delay)
            except Exception:
                # try attribute access (Config-like objects)
                try:
                    if hasattr(action_delay, "ACTION_DELAY"):
                        resolved = float(getattr(action_delay, "ACTION_DELAY"))
                    elif hasattr(action_delay, "action_delay"):
                        resolved = float(getattr(action_delay, "action_delay"))
                    elif isinstance(action_delay, dict):
                        resolved = float(action_delay.get("ACTION_DELAY", action_delay.get("action_delay", DEFAULT_ACTION_DELAY)))
                    else:
                        LOG.warning("Unrecognized action_delay type %s; using default %.2f", type(action_delay), DEFAULT_ACTION_DELAY)
                        resolved = DEFAULT_ACTION_DELAY
                except Exception:
                    LOG.exception("Failed to resolve action_delay from provided object; using default %.2f", DEFAULT_ACTION_DELAY)
                    resolved = DEFAULT_ACTION_DELAY

        self.action_delay = resolved
        LOG.info("ActionExecutor initialized with action delay %.2fs.", self.action_delay)
        # Configure pyautogui defaults if available
        if pyautogui is not None:
            pyautogui.PAUSE = self.action_delay
            pyautogui.FAILSAFE = True

    def parse_actions(self, text: str) -> List[Dict[str, Any]]:
        """Parse ChatGPT text for actions.

        Currently supports patterns like:
          CLICK button at coordinates [123, 456]
          CLICK button at [123,456]
          CLICK at [123, 456]

        Returns a list of action dicts: {'type': 'click', 'x': int, 'y': int}
        """
        if not text:
            return []

        actions: List[Dict[str, Any]] = []

        # Normalize text
        normalized = text.replace('\r', '\n')

        # Find all lines containing CLICK and coordinates
        click_pattern = re.compile(r"CLICK[^\[]*\[\s*(\d+)\s*,\s*(\d+)\s*\]", re.IGNORECASE)
        for m in click_pattern.finditer(normalized):
            x = int(m.group(1))
            y = int(m.group(2))
            actions.append({"type": "click", "x": x, "y": y})

        # Also support shorter pattern: "CLICK at 123,456" or "CLICK 123, 456"
        alt_pattern = re.compile(r"CLICK[^0-9]*(\d{1,4})\s*,\s*(\d{1,4})", re.IGNORECASE)
        for m in alt_pattern.finditer(normalized):
            x = int(m.group(1))
            y = int(m.group(2))
            # avoid duplicating coordinates already captured by bracket pattern
            if not any(a.get("x") == x and a.get("y") == y for a in actions):
                actions.append({"type": "click", "x": x, "y": y})

        LOG.info("Parsed %d actions from response.", len(actions))
        return actions

    def wait_for_confirmation(self) -> bool:
        """Wait for the user to confirm execution.

        Returns True to execute, False to cancel.
        Uses CONFIRM_KEY (default F10) and CANCEL_KEY (default esc).
        If AUTO_EXECUTE is True, returns True immediately.
        """
        if AUTO_EXECUTE:
            LOG.info("AUTO_EXECUTE_ACTIONS enabled — skipping confirmation.")
            return True

        if keyboard is None:
            LOG.warning("keyboard module not available — cannot wait for confirmation. Proceeding by default.")
            return True

        LOG.info("Waiting for confirmation: press %s to execute, or %s to cancel.", CONFIRM_KEY, CANCEL_KEY)
        try:
            # Busy-wait loop to allow cancel
            while True:
                if keyboard.is_pressed(CANCEL_KEY):
                    LOG.info("Cancel key pressed — aborting execution.")
                    return False
                if keyboard.is_pressed(CONFIRM_KEY):
                    LOG.info("Confirmation key pressed — proceeding with execution.")
                    # small debounce
                    time.sleep(0.2)
                    return True
                time.sleep(0.05)
        except Exception as e:
            LOG.exception("Error while waiting for confirmation: %s", e)
            return False

    def execute_actions(self, actions: List[Dict[str, Any]]) -> None:
        """Execute parsed actions using PyAutoGUI.

        Currently only supports 'click' actions.
        """
        if not actions:
            LOG.warning("No actions to execute.")
            return

        if pyautogui is None:
            LOG.error("PyAutoGUI not available — cannot execute actions.")
            return

        LOG.info("Executing %d actions...", len(actions))
        # attempt to get latest report info for bounds checking
        latest_report = self._load_latest_report()
        cv_info = None
        if latest_report:
            cv_info = latest_report.get("cv_analysis") or latest_report.get("cv") or None

        for idx, act in enumerate(actions, start=1):
            try:
                if act.get("type") == "click":
                    x = int(act.get("x"))
                    y = int(act.get("y"))
                    # verify coordinates are within latest report bounds if available
                    if cv_info and isinstance(cv_info, dict):
                        try:
                            w = int(cv_info.get("width", 0))
                            h = int(cv_info.get("height", 0))
                            if not (0 <= x < w and 0 <= y < h):
                                LOG.warning("Skipping click (%d,%d): outside latest report bounds %dx%d", x, y, w, h)
                                continue
                        except Exception:
                            pass
                    LOG.info("Action %d: clicking at (%d, %d)", idx, x, y)
                    pyautogui.moveTo(x, y)
                    pyautogui.click()
                    time.sleep(self.action_delay)
                elif act.get("type") == "type":
                    text = str(act.get("text", ""))
                    LOG.info("Action %d: typing text: %s", idx, text)
                    # Type with a small interval between keystrokes
                    pyautogui.write(text, interval=0.05)
                    time.sleep(self.action_delay)
                else:
                    LOG.warning("Unknown action type: %s", act)
            except Exception as e:
                LOG.exception("Failed to execute action %s: %s", act, e)

    def _load_latest_report(self) -> Optional[Dict[str, Any]]:
        """Load the most recent JSON analysis report from the reports directory."""
        try:
            pattern = os.path.join(REPORTS_DIR, "*.json")
            files = glob.glob(pattern)
            if not files:
                return None
            latest = max(files, key=os.path.getmtime)
            with open(latest, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            LOG.exception("Failed to load latest report from %s", REPORTS_DIR)
            return None

    def _extract_typing_text_from_report(self, report: Optional[Dict[str, Any]]) -> str:
        """Extract a short, sensible text string from the analysis report to type."""
        fallback = "Automated input"
        if not report:
            return fallback
        candidates: List[str] = []

        def collect(obj: Any):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, str) and len(v.strip()) > 2:
                        candidates.append(v.strip())
                    else:
                        collect(v)
            elif isinstance(obj, list):
                for it in obj:
                    collect(it)

        collect(report)
        # prefer shorter candidates
        candidates = [c for c in candidates if len(c) <= 120]
        if candidates:
            return candidates[0]
        return fallback

    def run_from_response(self, response_text: str) -> bool:
        """Parse a ChatGPT response and (optionally) execute the actions.

        Returns True if actions were executed, False otherwise.
        """
        actions = self.parse_actions(response_text)
        if not actions:
            LOG.warning("No valid actions found in the response.")
            return False

        # Decide between executing a click vs typing: 50/50 long-run.
        mode = random.choice(["click", "type"])
        LOG.info("Execution mode chosen: %s", mode)

        selected = actions
        if mode == "type":
            # create a single typing action using latest analysis report
            report = self._load_latest_report()
            typing_text = self._extract_typing_text_from_report(report)
            selected = [{"type": "type", "text": typing_text}]
        else:
            # Select up to MAX_ACTIONS click actions based on proximity to center
            try:
                if pyautogui is not None:
                    w, h = pyautogui.size()
                else:
                    w, h = 1920, 1080
                cx, cy = w // 2, h // 2

                def score(a: dict) -> float:
                    if a.get("type") == "click":
                        dx = int(a.get("x", 0)) - cx
                        dy = int(a.get("y", 0)) - cy
                        return abs(dx) + abs(dy)
                    return float('inf')

                selected = sorted(actions, key=score)[:MAX_ACTIONS]
                LOG.info("Selected %d action(s) to execute based on proximity to center.", len(selected))
                for idx, a in enumerate(selected, start=1):
                    LOG.info("Selected action %d: %s", idx, a)
            except Exception:
                LOG.exception("Error selecting top actions; falling back to executing all parsed actions.")
                selected = actions

        # Ask for confirmation if required
        ok = self.wait_for_confirmation()
        if not ok:
            LOG.info("Execution cancelled by user.")
            return False

        self.execute_actions(selected)
        LOG.info("Execution finished.")
        return True

    # Backwards-compatible alias used by older Main Application code
    def execute_from_response(self, response_text: str) -> bool:
        """Alias for run_from_response kept for backward compatibility.

        Older versions of the main application call `execute_from_response`. Keep
        this thin wrapper so upgrades are smooth.
        """
        return self.run_from_response(response_text)

# If this file is run directly for quick testing, provide a small CLI.
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ae = ActionExecutor()
    sample = (
        "1. CLICK button at coordinates [89, 17]\n"
        "2. CLICK button at coordinates [198, 17]\n"
        "3. CLICK button at [271, 17]\n"
    )
    LOG.info("Sample run: parsed actions=%s", ae.parse_actions(sample))
    LOG.info("AUTO_EXECUTE=%s", AUTO_EXECUTE)
