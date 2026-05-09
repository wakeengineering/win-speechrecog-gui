# Game Voice Chat Caption Overlay - Requirements

## System Requirements (Non-Python)

### Required
- [ ] **Windows 11** (tested on this OS)
- [ ] **RTX 5080** or NVIDIA GPU with CUDA Compute Capability 6.0+
- [ ] **20GB free disk space** (for Vosk large model ~1.8GB + buffer)
- [ ] **8GB+ RAM** (for large Vosk model loaded in memory)

### Audio Setup
- [ ] **Stereo Mix enabled** (Windows 11 Sound settings)
  - OR **VB-Audio Virtual Cable** if Stereo Mix not available
  - See `STEREO_MIX_SETUP.md` for detailed setup

### Build Tools (Required for webrtcvad)
- [ ] **Microsoft C++ Build Tools** 
  - Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
  - Install "Desktop development with C++"
  - Size: ~2-5GB
  - Required for: Voice Activity Detection (VAD)

### Optional Future Requirements
- [ ] **Docker Desktop** (only if switching to NVIDIA Riva path)
- [ ] **NVIDIA CUDA Toolkit 12.x** (only if switching to GPU-accelerated Riva)

---

## Python Requirements

### Core Packages
```
vosk==0.3.45          # Speech recognition engine
sounddevice==0.5.5    # Audio capture
numpy==2.4.2          # Audio processing
```

### Audio & VAD
```
webrtcvad==2.0.10     # Voice Activity Detection (requires C++ Build Tools)
pydub==0.25.1         # Audio processing utilities
```

### Configuration
```
configparser           # Built-in Python module (no install needed)
```

### UI
```
tkinter                # Built-in Python module (included with Python)
```

### Supporting Dependencies (auto-installed)
```
requests==2.32.5      # For model downloads
cffi==2.0.0           # C Foreign Function Interface
tqdm==4.67.2          # Progress bars
websockets==16.0      # Vosk communication
```

---

## Installation Checklist

### Step 1: System Setup
- [ ] Windows 11 installed
- [ ] RTX 5080 drivers up to date
- [ ] C++ Build Tools installed
- [ ] Stereo Mix enabled

### Step 2: Python Environment
```powershell
# Activate venv
.\venv\Scripts\activate.bat

# Install core packages
pip install vosk sounddevice numpy pydub webrtcvad

# Verify installation
python -c "import vosk, sounddevice, webrtcvad; print('All packages imported successfully')"
```

### Step 3: App Setup
- [ ] `config.ini` created (see `config.ini`)
- [ ] `win-speechrecog.py` in place
- [ ] Vosk model downloaded on first run (~1.8GB)

---

## Vosk Model Requirements

**Selected Model:** `large-en-us`
- **Size:** ~1.8GB
- **RAM:** ~2GB (loaded into memory)
- **Accuracy:** Best of the three options
- **Location:** Auto-downloaded to `./model/` on first run
- **Dependencies:** 
  - requests (for downloading)
  - NVME or HDD with 20GB free space

**Alternative Models (not recommended for gaming):**
- `base-en-us` - 200MB, moderate accuracy
- `tiny-en-us` - 40MB, poor accuracy

---

## Disk Space Breakdown

| Component | Size | Location |
|-----------|------|----------|
| Vosk model (large) | 1.8GB | `./model/` |
| Python venv | 1.5GB | `./venv/` |
| webrtcvad + deps | 200MB | venv site-packages |
| Source code | ~50KB | Root directory |
| **Total** | **~3.6GB** | Local directory |

---

## Runtime Requirements

### Per-Session (Vosk)
- GPU VRAM: None (Vosk is CPU-only)
- CPU: ~5-10% (lightweight audio processing)
- RAM: ~200-300MB (app overhead) + ~2GB (large model loaded)
- Network: None required (fully offline)

### Per-Session (Riva - if using GPU path)
- GPU VRAM: 3.6-13.4GB depending on model:
  - conformer-ctc (streaming): 3.6GB - recommended for gaming
  - parakeet-0-6b-ctc: 4GB
  - parakeet-1-1b-ctc: 5GB
  - canary-1b: 13.4GB - highest accuracy
  - whisper-large-v3-turbo: 11.3GB
- CPU: ~2-5% (minimal, offloaded to GPU)
- RAM: ~500MB-6.5GB depending on model
- Network: None (runs locally)

### Gaming Impact
- **Vosk**: CPU ~5-10%, no GPU usage
- **Riva (conformer-ctc)**: ~3.6GB VRAM, minimal CPU
  - With RTX 5080 (16GB): Leaves 12.4GB for gaming
- Frame rate impact: Minimal to unnoticeable

---

## Troubleshooting Requirements Issues

### If webrtcvad install fails
- Verify C++ Build Tools installed correctly
- Reinstall Visual Studio C++ Build Tools
- Restart terminal/IDE after install

### If Vosk model won't download
- Check internet connection
- Verify 20GB+ free disk space
- Check Windows Defender isn't blocking downloads
- Manual fallback: Download from https://alphacephei.com/vosk/models/

### If Stereo Mix not available
- Audio driver may not support it
- Use VB-Audio Virtual Cable instead (see `STEREO_MIX_SETUP.md`)
- Update NVIDIA/Realtek audio drivers

---

## Future Requirements (If Switching to Riva)

When ready to switch from Vosk to NVIDIA Riva:
```
nvidia-riva-client     # Riva client library
docker                 # Container runtime (Docker Desktop)
cuda-toolkit-12.x      # NVIDIA CUDA (if not already installed)
```

### WSL2 + Docker Notes (Optional)

You can run the Riva Docker container in **WSL2 Ubuntu** and keep the Python client OS-agnostic. The client only needs a host:port endpoint.

**Endpoint options for config.ini:**
- `endpoint=localhost:50051` (works if WSL2 port forwarding is enabled by Docker Desktop)
- `endpoint=<WSL_IP>:50051` (use this if `localhost` does not reach WSL)

**If you need the WSL IP:**
- In WSL: `hostname -I`

**Riva container must expose port 50051**
- Example: `-p 50051:50051`

Estimated additional disk space: **10-15GB** for Riva Docker image
Estimated setup time: **30-45 minutes**

---

## Version Compatibility

**Tested & Working:**
- Python 3.12.10
- Windows 11 (Build 22621+)
- NVIDIA drivers: Latest (2025+)

**Minimum Versions:**
- Python 3.8+
- Windows 10 or later (Stereo Mix support)

