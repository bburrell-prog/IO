"""
loop_wrapper.py

Simple wrapper that loads `Main Application.py` (which contains the
`DesktopAnalyzer` class) and provides a clean interactive loop:

- Press F9 to run a single analysis cycle (the analyzer will send to ChatGPT
  and then use ActionExecutor which will wait for F10 confirmation before
  executing actions).
- Press ESC to exit the wrapper.

This avoids modifying the original main file and achieves the requested
behaviour of returning to the F9/F10 start after each execution.
"""
from __future__ import annotations
import importlib.util
import pathlib
import sys
import time

try:
    import keyboard
except Exception:
    keyboard = None

HERE = pathlib.Path(__file__).resolve().parent
main_path = HERE / "Main Application.py"

if not main_path.exists():
    raise FileNotFoundError(f"Could not find Main Application at: {main_path}")

spec = importlib.util.spec_from_file_location("_main_app", str(main_path))
main_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_mod)

# Expect DesktopAnalyzer class in the main module
if not hasattr(main_mod, "DesktopAnalyzer"):
    raise AttributeError("Main Application.py does not expose 'DesktopAnalyzer' class")

DesktopAnalyzer = getattr(main_mod, "DesktopAnalyzer")

def main():
    analyzer = DesktopAnalyzer()

    print("Interactive wrapper started.")
    print("Press F9 to run analysis. Press ESC to exit the wrapper.")

    if keyboard is None:
        print("Warning: 'keyboard' module not available. This wrapper requires it for key listening.")
        # Fallback: run one cycle and exit
        analyzer.run_analysis_cycle()
        return

    try:
        while True:
            # Wait for F9 or ESC
            keyboard.wait('f9')
            # If ESC pressed before F9 returned (unlikely), break
            if keyboard.is_pressed('esc'):
                print('Exit requested. Shutting down.')
                break

            print('F9 pressed — running analysis cycle...')
            try:
                analyzer.run_analysis_cycle()
            except Exception as e:
                print('Error during analysis cycle:', e)

            # small pause to avoid immediate retrigger
            time.sleep(0.1)
            if keyboard.is_pressed('esc'):
                print('Exit requested. Shutting down.')
                break

    except KeyboardInterrupt:
        print('Interrupted by user (KeyboardInterrupt).')

if __name__ == '__main__':
    main()
