# Windows Speech Recognition GUI

Experimental scripts for live closed captions using various speech recognition backends. This repository contains attempts at implementing real-time speech-to-text overlays for Windows.

## Attempts Overview

### NVIDIA Riva Attempt (`live-closed-captions-riva.py`)
An early attempt using NVIDIA Riva for GPU-accelerated speech recognition. Requires Riva server setup and may have compatibility issues.

### Vosk Offline Attempt (`live-closed-captions-vosk.py`)
Uses Vosk for offline speech recognition. Includes large model files (ignored in .gitignore) for different accuracy levels:
- `model/`: Base model
- `model_base/`: Base model with additional components
- `model_large/`: Large model for higher accuracy

### Windows Live Captions Scraper (`live-closed-captions-windows.py`)
Scrapes text from Windows 11's built-in Live Captions feature to create a custom, minimalistic overlay window. This provides a cleaner, more customizable interface than the default Live Captions GUI.

**Note**: This script makes the Live Captions experience more minimalistic but may not function correctly after the latest Windows updates due to changes in the Live Captions window structure or accessibility APIs.

## Features

- **Custom Overlay**: Minimalistic caption display with configurable appearance
- **Window Scraping**: Extracts captions from Windows Live Captions using UI Automation
- **Configurable**: Settings via `config.ini` for window size, opacity, fonts, etc.
- **Auto-Hide Original**: Option to hide the default Live Captions window
- **Idle Timeout**: Automatically clears captions after periods of silence

## Installation

1. Install dependencies: `pip install -r REQUIREMENTS.md` (or manually install pywinauto, pygetwindow, pywin32)
2. Ensure Windows Live Captions is enabled: Win+Ctrl+L or Settings > Accessibility > Captions
3. Run the desired script: `python live-closed-captions-windows.py`

## Configuration

Edit `config.ini` to customize:
- Window size and opacity
- Font family and size
- Colors and styling
- Update intervals
- Hide/show options

## Requirements

- Windows 11
- Python 3.x
- Windows Live Captions enabled
- Dependencies listed in `REQUIREMENTS.md`

## Caveats

- **Experimental**: All implementations are proof-of-concepts and may be unstable
- **Windows Updates**: The Windows scraper may break with OS updates
- **Permissions**: May require elevated privileges for window manipulation
- **Compatibility**: Primarily tested on Windows 11

## License

MIT License - Intended for personal, non-commercial use. See LICENSE file for details.