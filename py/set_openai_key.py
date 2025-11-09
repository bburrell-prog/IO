#!/usr/bin/env python3
"""
Helper to securely set OPENAI_API_KEY in a project-local .env file.
This script prompts for the API key (hidden input) and writes a .env at the
project root. It ensures .env is listed in .gitignore.

Usage:
    python3 py/set_openai_key.py

The script does NOT print the key anywhere.
"""
from __future__ import annotations
import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / '.env'
GITIGNORE = ROOT / '.gitignore'

def main():
    print("This will write your OpenAI API key to a local .env file in the project root.")
    print("The value will NOT be shown on screen and .env will be added to .gitignore if missing.")
    key = getpass.getpass("OpenAI API key (input hidden): ")
    if not key:
        print("No key entered. Aborting.")
        return

    # write .env
    content = f"OPENAI_API_KEY={key}\n"
    ENV_PATH.write_text(content, encoding='utf-8')
    # set restrictive permissions (owner read/write only) where possible
    try:
        ENV_PATH.chmod(0o600)
    except Exception:
        # ignore if OS doesn't allow chmod
        pass

    # ensure .gitignore contains .env
    if GITIGNORE.exists():
        gitignore_text = GITIGNORE.read_text(encoding='utf-8')
        if '.env' not in gitignore_text.splitlines():
            with open(GITIGNORE, 'a', encoding='utf-8') as f:
                f.write('\n.env\n')
            print("Added .env to .gitignore")
    else:
        GITIGNORE.write_text('.env\n', encoding='utf-8')
        print("Created .gitignore and added .env to it")

    print(f"Wrote .env to {ENV_PATH} (permissions set to 600 where supported).")
    print("Run your app in the project root (in the same shell) and it will pick up the key via dotenv.")

if __name__ == '__main__':
    main()
