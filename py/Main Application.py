#!/usr/bin/env python3
"""
Desktop Screen Analyzer with ChatGPT Integration
Main application entry point
"""
import sys
import time
import json
import logging
from collections import Counter
from statistics import mean
from pathlib import Path
from typing import Any

# Import project modules
from screen_analyzer import ScreenAnalyzer
from chatgpt_client import ChatGPTClient
from action_executor import ActionExecutor
from config import Config
from database import CycleDatabase

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
        # Construct ChatGPTClient explicitly: pass api_key by name to avoid
        # it being treated as the 'model' positional argument.
        self.chatgpt_client = ChatGPTClient(api_key=self.config.openai_api_key, model="gpt-4o-mini")
        self.action_executor = ActionExecutor(self.config)
        self.db = CycleDatabase()
        logger.info("Desktop Analyzer initialized.")

    def run_analysis_cycle(self):
        """Runs a single, complete analysis cycle."""
        try:
            logger.info("Starting new screen analysis cycle...")

            timestamp = time.strftime("%Y%m%d_%H%M%S")

            # 1. Capture and analyze the screen
            logger.info("Capturing screenshot...")
            screenshot_path = self.screen_analyzer.capture_screenshot()

            logger.info("Analyzing screen content...")
            analysis_report = self.screen_analyzer.analyze_screen(screenshot_path)

            # 2. Derive statistics for quick insight
            statistics_summary = self._compute_statistics(analysis_report)
            self._print_statistics(statistics_summary)

            # 3. Save the detailed analysis report
            report_path = self._save_analysis_report(analysis_report)
            logger.info(f"Analysis report saved to: {report_path}")

            # 4. Get insights from ChatGPT
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

        # Save cycle to database regardless of success/failure
        try:
            self.db.insert_cycle(
                timestamp=timestamp,
                screenshot_path=str(screenshot_path) if 'screenshot_path' in locals() else None,
                report_path=str(report_path) if 'report_path' in locals() else None,
                chatgpt_response=chatgpt_response if 'chatgpt_response' in locals() else None,
                statistics=statistics_summary if 'statistics_summary' in locals() else None
            )
            logger.info("Cycle data saved to database.")
        except Exception as e:
            logger.error(f"Failed to save cycle to database: {e}")

    def _save_analysis_report(self, report: dict) -> Path:
        """Saves the analysis report to a JSON file."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"screen_analysis_{timestamp}.json"
        filepath = self.config.reports_dir / filename
        
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        return filepath

    def _compute_statistics(self, report: dict) -> dict:
        """Derive high-level statistics about detected titles and UI objects."""
        elements = report.get("elements", {}) or {}
        text_elements = [item for item in elements.get("text", []) if isinstance(item, dict)]

        texts = []
        confidences = []
        title_registry: dict[str, dict[str, Any]] = {}

        for item in text_elements:
            raw_text = str(item.get("text", "")).strip()
            if not raw_text:
                continue

            conf = item.get("confidence")
            if isinstance(conf, (int, float)):
                confidences.append(conf)

            texts.append(raw_text)

            if self._looks_like_title(raw_text, conf):
                registry_entry = title_registry.setdefault(raw_text, {"count": 0, "confidences": []})
                registry_entry["count"] += 1
                if isinstance(conf, (int, float)):
                    registry_entry["confidences"].append(conf)

        object_counter = Counter()
        for key, value in elements.items():
            if isinstance(value, list):
                object_counter[key] += len(value)

        cv_analysis = report.get("cv_analysis", {}) or {}
        if isinstance(cv_analysis, dict):
            for key, value in cv_analysis.items():
                if isinstance(value, list):
                    object_counter[f"cv_{key}"] += len(value)

        interaction_points = report.get("interaction_points", []) or []

        top_titles = []
        for title, meta in sorted(title_registry.items(), key=lambda item: (-item[1]["count"], -self._safe_mean(item[1]["confidences"]))):
            top_titles.append({
                "text": title,
                "count": meta["count"],
                "avg_confidence": round(self._safe_mean(meta["confidences"]), 1) if meta["confidences"] else None
            })
            if len(top_titles) >= 5:
                break

        text_counter = Counter(texts)
        top_text_fragments = [
            {"text": text, "count": count}
            for text, count in text_counter.most_common(5)
        ]

        stats = {
            "total_text_elements": len(text_elements),
            "unique_text_entries": len(text_counter),
            "average_text_confidence": round(mean(confidences), 1) if confidences else None,
            "title_candidates": top_titles,
            "top_text_fragments": top_text_fragments,
            "object_counts": dict(object_counter),
            "interaction_points": len(interaction_points)
        }

        report["statistics"] = stats
        return stats

    def _looks_like_title(self, text: str, confidence: Any) -> bool:
        """Heuristic to decide whether a text fragment is likely a title/heading."""
        if len(text) < 3:
            return False

        alpha_chars = sum(ch.isalpha() for ch in text)
        has_letters = alpha_chars >= 3
        if not has_letters:
            return False

        words = text.split()
        confidence_ok = isinstance(confidence, (int, float)) and confidence >= 75
        stylistic_hint = text.isupper() or text.istitle()
        reasonable_length = 1 <= len(words) <= 10 and len(text) <= 80

        return (confidence_ok or stylistic_hint) and reasonable_length

    def _safe_mean(self, values: list[float]) -> float:
        return mean(values) if values else 0.0

    def _print_statistics(self, stats: dict) -> None:
        """Pretty-print statistics to the console for quick insight."""
        print("\n=== Screen Statistics ===")
        print(f"Text elements detected: {stats.get('total_text_elements', 0)} (unique: {stats.get('unique_text_entries', 0)})")

        avg_conf = stats.get("average_text_confidence")
        if avg_conf is not None:
            print(f"Average OCR confidence: {avg_conf:.1f}")
        else:
            print("Average OCR confidence: n/a")

        print("Top titles / headings:")
        titles = stats.get("title_candidates", []) or []
        if titles:
            for entry in titles:
                avg = entry.get("avg_confidence")
                avg_display = f"{avg:.1f}" if isinstance(avg, (int, float)) else "n/a"
                print(f"  • {entry.get('text')} (count: {entry.get('count')}, avg conf: {avg_display})")
        else:
            print("  • None detected")

        print("Most common text fragments:")
        fragments = stats.get("top_text_fragments", []) or []
        if fragments:
            for fragment in fragments:
                print(f"  • {fragment.get('text')} (count: {fragment.get('count')})")
        else:
            print("  • n/a")

        print("UI object counts:")
        obj_counts = stats.get("object_counts", {}) or {}
        if obj_counts:
            for name, count in obj_counts.items():
                print(f"  • {name}: {count}")
        else:
            print("  • No UI elements detected")

        print(f"Interaction points suggested: {stats.get('interaction_points', 0)}")
        print("==========================\n")

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
        # Database controller flags:
        #  --db       : open the web-based controller (default, safe)
        #  --db-gui   : attempt to open the Tkinter GUI controller (may abort on some macOS setups)
        if len(sys.argv) > 1 and sys.argv[1] in ('--db', '--db-gui'):
            import subprocess
            script_dir = Path(__file__).parent
            gui_script = script_dir / 'database_controller.py'
            web_script = script_dir / 'database_controller_web.py'

            # If user explicitly requested the GUI, try it; otherwise default to web
            want_gui = sys.argv[1] == '--db-gui'

            if want_gui and gui_script.exists():
                try:
                    proc = subprocess.run([sys.executable, str(gui_script)], timeout=8)
                    if proc.returncode == 0:
                        return
                    else:
                        logger.warning(f"GUI controller exited with code {proc.returncode}, falling back to web controller")
                except subprocess.TimeoutExpired:
                    # The GUI probably started and is running; assume success
                    return
                except Exception:
                    logger.exception("Failed to launch GUI controller; falling back to web controller")

            # Default/web controller path
            if web_script.exists():
                try:
                    from database_controller_web import main as web_main
                    web_main()
                    return
                except Exception as e:
                    logger.error(f"Failed to start web DB controller: {e}", exc_info=True)
            else:
                logger.error("No database controller available (neither GUI nor web).")

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

