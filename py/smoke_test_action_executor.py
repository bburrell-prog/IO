"""
Non-destructive smoke test for action_executor.py.
This script imports the module, patches pyautogui and keyboard to safe mocks,
then runs run_from_response with a sample ChatGPT response.
"""
import sys
from types import SimpleNamespace
p = r"c:/Users/Brody Burrell/Desktop/py"
if p not in sys.path:
    sys.path.insert(0, p)

# Safe mocks for pyautogui and keyboard
class MockPyAutoGUI:
    def size(self):
        return (1920, 1080)
    def moveTo(self, x, y):
        print(f"[pyautogui] moveTo({x},{y})")
    def click(self):
        print("[pyautogui] click()")
    def write(self, text, interval=0.05):
        print(f"[pyautogui] write({text!r}, interval={interval})")

class MockKeyboard:
    def is_pressed(self, key):
        return False

# inject mocks into sys.modules so action_executor imports them
import types
sys.modules['pyautogui'] = MockPyAutoGUI()
sys.modules['keyboard'] = MockKeyboard()

import action_executor

AE = action_executor.ActionExecutor(action_delay=0.01)

# Sample ChatGPT-style response containing click commands
sample_response = '''
CLICK [640, 360]
CLICK [100, 200]
CLICK [1280, 720]
'''

print('\nRunning smoke test (non-destructive):')
result = AE.run_from_response(sample_response)
print('Result:', result)

# Run a typing-mode path by forcing random.choice to return 'type'
import random
random_choice_orig = random.choice
random.choice = lambda seq: 'type'

# Create a fake report JSON file in reports/ for extraction
import os, json
reports_dir = os.getenv('REPORTS_DIR', 'reports')
if not os.path.isdir(reports_dir):
    os.makedirs(reports_dir, exist_ok=True)
with open(os.path.join(reports_dir, 'smoke_report.json'), 'w', encoding='utf-8') as f:
    json.dump({'summary': 'Hello from smoke test! Please enter this text.'}, f)

print('\nRunning typing-mode smoke test:')
result2 = AE.run_from_response(sample_response)
print('Result:', result2)

# restore
random.choice = random_choice_orig
print('\nSmoke test completed.')
