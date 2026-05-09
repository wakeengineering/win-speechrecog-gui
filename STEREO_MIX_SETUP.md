# Setting Up Stereo Mix for Game Audio Capture

## Option 1: Enable Stereo Mix (Windows 11)

### ✅ Stereo Mix (Best for Game Audio)
This captures everything coming OUT of your speakers WITHOUT muting game audio.

**Windows 11 Steps:**
1. Press `Windows Key` and search for **"Sound settings"**
2. Click **"Sound settings"** to open Settings app
3. Scroll down to **"Advanced"** section
4. Click **"Volume mixer"**
5. Scroll down to find **"Stereo Mix"** or **"Stereo Mix (Your Audio Device)"**
6. If it shows with a red X or "disabled":
   - Click on it
   - Click **"Enable"** button at the top
7. If you don't see it at all:
   - Use the old Sound Control Panel (see Alternative below)

**Alternative: Old Sound Control Panel (If app method fails)**
1. Press `Windows Key + R`
2. Type: `mmsys.cpl` and press Enter
3. Go to **"Recording"** tab
4. Right-click empty space → ☑️ **"Show Disabled Devices"**
5. Right-click **"Stereo Mix"** → **"Enable"**
6. Right-click **"Stereo Mix"** → **"Set as Default Device"**
7. Click "Apply" → "OK"

## Option 2: Virtual Audio Cable (If Stereo Mix Not Available)

If Stereo Mix is greyed out/unavailable:

1. Download **VB-Audio Virtual Cable** (free): https://vb-audio.com/Cable/
2. Install and restart Windows
3. In the app, select "VB-Audio Virtual Cable" from the device dropdown
4. In Windows Sound settings, set VB-Cable as your default playback device
5. Game audio now routes through Virtual Cable → Capture it

## Testing Your Setup

**Run the application:**
```powershell
.venv\Scripts\Activate.ps1
python win-speechrecog.py
```

**Test procedures:**
1. **Game/Party Chat Audio:**
   - Open Discord, Teams, or game voice chat
   - Launch the caption app
   - Click "Refresh" to list devices
   - Select "Stereo Mix" or your audio device from the dropdown
   - Speak or play audio - captions should appear
   - ✅ Game audio continues playing normally

2. **Microphone Input:**
   - Select your microphone from the device dropdown
   - Speak into your mic
   - Captions should appear in real-time

## Device ID Reference

**Common Device Names:**
- `Stereo Mix` - Built-in game/system audio capture
- `Microphone` - Your mic input
- `VB-Audio Virtual Cable` - Virtual audio routing
- `Loopback Audio` - Alternative virtual audio

The app will list ALL available devices - pick whichever you want to transcribe.

## Troubleshooting

**No devices showing?**
- Click "Refresh" button in the app
- Check Windows Sound settings to verify devices exist

**Stereo Mix disabled/greyed out?**
- Your audio driver may not support it
- Use VB-Audio Virtual Cable instead (see Option 2)

**Audio is muted when Stereo Mix enabled?**
- In Sound settings, right-click Stereo Mix → "Disable"
- Try VB-Cable instead (doesn't mute)

**Captions not appearing?**
- Make sure your selected device has active audio
- Check terminal for error messages
- Try a different device
