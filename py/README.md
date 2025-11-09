# Desktop Screen Analyzer with ChatGPT Integration

An automated screen analysis tool that captures screenshots, analyzes them using OCR and computer vision, and generates actionable insights using ChatGPT.

## Prerequisites

### 1. Python 3.8 or higher
Check your Python version:
```bash
python3 --version
```

### 2. Tesseract OCR
Install Tesseract on macOS using Homebrew:
```bash
brew install tesseract
```

Verify installation:
```bash
tesseract --version
```

### 3. OpenAI API Key
You'll need an OpenAI API key. Get one from: https://platform.openai.com/api-keys

## Installation

### Step 1: Navigate to the project directory
```bash
cd "/Users/bburrell/Desktop/IO/py"
```

### Step 2: Create a virtual environment (recommended)
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Set up your environment configuration
```bash
cp .env.example .env
```

Then edit the `.env` file and add your OpenAI API key:
```bash
nano .env
```

Replace `sk-your-api-key-here` with your actual OpenAI API key.

## Running the Application

### Option 1: Run a single analysis cycle
This will capture one screenshot, analyze it, and exit:
```bash
python3 main.py --once
```

### Option 2: Run in interactive mode (macOS requires sudo)
This runs continuously and waits for key presses:

**⚠️ IMPORTANT for macOS users**: The `keyboard` library requires root access on macOS. You need to run with `sudo`:

```bash
sudo python3 main.py
```

In interactive mode:
- Press **F9** to trigger a screen analysis
- Press **ESC** to exit the program

**Note**: When running with sudo, you may need to specify the full path to your virtual environment's Python:
```bash
sudo /Users/bburrell/Desktop/IO/py/venv/bin/python3 main.py
```

### Option 3: Launch the Data Viewer
View all analysis cycle data in a web-based interface:
```bash
python3 main.py --viewer
```

This opens a web browser at `http://localhost:5000` with:
- 📊 Real-time statistics dashboard
- 🔍 Search and filter capabilities
- 📋 Detailed view of each analysis cycle
- 🖼️ Direct access to screenshots and reports
- 🔄 Auto-refresh every 30 seconds

## Configuration

Edit the `.env` file to customize:

- **OPENAI_API_KEY**: Your OpenAI API key (required)
- **AUTO_EXECUTE_ACTIONS**: Set to `True` to automatically execute actions without confirmation
- **ACTION_DELAY**: Delay in seconds between automated actions (default: 0.5)
- **OCR_CONFIDENCE_THRESHOLD**: Minimum confidence for OCR text detection (default: 30)
- **SCREENSHOTS_DIR**: Directory to save screenshots (default: screenshots)
- **REPORTS_DIR**: Directory to save analysis reports (default: reports)

## Output

The application generates:
- **Screenshots**: Saved in the `screenshots/` directory
- **Analysis Reports**: Saved as JSON files in the `reports/` directory
- **Logs**: Saved to `desktop_analyzer.log`

## Troubleshooting

### "keyboard library requires root access" on macOS
This is expected behavior. Either:
- Run with `sudo` as shown above
- Use `--once` mode instead of interactive mode
- Remove the keyboard dependency and modify the code

### "OPENAI_API_KEY not found"
Make sure you've:
1. Created the `.env` file from `.env.example`
2. Added your actual API key to the `.env` file
3. The key starts with `sk-`

### "Tesseract not found"
Install Tesseract using:
```bash
brew install tesseract
```

### Python module not found
Make sure you've activated your virtual environment and installed dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Project Structure

```
py/
├── main.py                      # Main entry point
├── Main Application.py          # Core application logic
├── screen_analyzer.py           # Screen capture and analysis
├── chatgpt_client.py           # OpenAI API client
├── action_executor.py          # Action execution module
├── config.py                   # Configuration loader
├── vision_processor.py         # Computer vision processing
├── data_container.py           # Aggregated data storage system
├── data_viewer.py              # Web-based data viewer application
├── requirements.txt            # Python dependencies
├── .env                        # Configuration (create from .env.example)
├── data_container.json         # Persistent storage of analysis cycles
├── screenshots/                # Captured screenshots
├── reports/                    # Analysis reports (JSON)
└── logs/                       # Application logs
```

## Data Storage & Viewer

The application includes a comprehensive data aggregation system:

### Data Container (`data_container.py`)
- **Aggregates all end-state data** from each analysis cycle
- **Stores persistently** in `data_container.json`
- **Tracks comprehensive metrics**:
  - Screenshots and file paths
  - Analysis reports and statistics
  - ChatGPT responses and AI insights
  - Processing times and error messages
  - Cycle metadata and timestamps

### Data Viewer (`data_viewer.py`)
Launch with `python3 main.py --viewer` to access:
- **📊 Real-time Statistics Dashboard**: Success rates, error rates, processing times
- **🔍 Advanced Search & Filtering**: Find cycles by content, status, or date
- **📋 Detailed Cycle Views**: Expandable cards showing full cycle information
- **🖼️ Direct Media Access**: View screenshots and download reports
- **🔄 Live Updates**: Auto-refreshes every 30 seconds as new data arrives

### What Gets Stored
Each analysis cycle captures:
- **Screenshot** (PNG file)
- **OCR Analysis** (text elements, confidence scores)
- **Computer Vision** (UI elements, buttons, windows)
- **Statistics** (element counts, processing metrics)
- **AI Response** (ChatGPT analysis and recommendations)
- **Metadata** (timestamps, processing time, errors)

## Example Usage

### Quick test run:
```bash
# Activate virtual environment
source venv/bin/activate

# Run a single analysis
python3 main.py --once
```

### Continuous monitoring (with sudo):
```bash
# Activate virtual environment
source venv/bin/activate

# Run in interactive mode
sudo /Users/bburrell/Desktop/IO/py/venv/bin/python3 main.py
```

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- The `keyboard` library requires elevated privileges on macOS
- Review generated actions before executing them if `AUTO_EXECUTE_ACTIONS` is enabled
