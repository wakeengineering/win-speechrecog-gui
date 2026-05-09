"""
Aggressive Live Captions Reset Utility
Finds and kills the Live Captions process to force a full reset
"""

import subprocess
import time
import os
import sys

def get_caption_processes():
    """Find processes related to Live Captions"""
    try:
        result = subprocess.run(
            ['tasklist', '/FO', 'LIST', '/V'],
            capture_output=True,
            text=True
        )
        lines = result.stdout.split('\n')
        
        # Look for caption-related processes
        caption_processes = []
        for line in lines:
            line_lower = line.lower()
            if any(term in line_lower for term in ['caption', 'narrator', 'accessibility']):
                print(f"Found: {line}")
                caption_processes.append(line)
        
        return caption_processes
    except Exception as e:
        print(f"Error listing processes: {e}")
        return []

def kill_process_by_name(process_name):
    """Kill a process by name"""
    try:
        # Use taskkill to force kill the process
        result = subprocess.run(
            ['taskkill', '/IM', process_name, '/F'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✓ Killed process: {process_name}")
            return True
        else:
            print(f"✗ Failed to kill {process_name}: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error killing process: {e}")
        return False

def reset_live_captions_via_settings():
    """Try to reset Live Captions via Windows settings"""
    print("\nAttempting reset via Settings...")
    try:
        # This opens Accessibility settings which might help reset it
        subprocess.Popen(['ms-settings:easeofaccess-display'])
        time.sleep(2)
        return True
    except Exception as e:
        print(f"Error opening settings: {e}")
        return False

def find_live_captions_window():
    """Find and try to manipulate the Live Captions window directly"""
    try:
        import win32gui
        import win32con
        
        # Find all windows
        windows = []
        def enum_windows(hwnd, lParam):
            title = win32gui.GetWindowText(hwnd)
            if "caption" in title.lower():
                windows.append((hwnd, title))
            return True
        
        win32gui.EnumWindows(enum_windows, None)
        
        if windows:
            print(f"\nFound caption windows:")
            for hwnd, title in windows:
                print(f"  HWND: {hwnd}, Title: '{title}'")
                
                # Try to kill the window
                try:
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    print(f"  → Sent WM_CLOSE to {title}")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"  → Error: {e}")
            
            return True
        else:
            print("No caption windows found")
            return False
            
    except ImportError:
        print("win32gui not available, skipping window manipulation")
        return False

def main():
    print("=" * 60)
    print("Windows Live Captions Aggressive Reset Utility")
    print("=" * 60)
    
    # Step 1: Find processes
    print("\n[1/4] Searching for Live Captions related processes...")
    processes = get_caption_processes()
    
    if not processes:
        print("No caption-related processes found")
    
    # Step 2: Try window-based reset
    print("\n[2/4] Attempting window-based reset...")
    find_live_captions_window()
    
    # Step 3: Kill common caption processes
    print("\n[3/4] Killing potential Live Captions processes...")
    potential_processes = [
        'narrator.exe',
        'WinCap.exe',
        'CaptionSettings.exe'
    ]
    
    for proc in potential_processes:
        try:
            kill_process_by_name(proc)
        except:
            pass
    
    # Step 4: Reinitialize via settings
    print("\n[4/4] Reinitializing via Settings...")
    time.sleep(1)
    
    print("\n" + "=" * 60)
    print("Reset attempted!")
    print("\nNext steps:")
    print("1. Close this window (or press Enter)")
    print("2. Open a terminal and run: python live-closed-captions-windows.py")
    print("3. Live Captions should now be properly initialized")
    print("\nIf it still doesn't work, restart your computer or try:")
    print("  - Settings > Accessibility > Captions")
    print("  - Toggle 'Live captions' OFF then back ON")
    print("=" * 60)
    
    input("\nPress Enter to close...")

if __name__ == "__main__":
    main()
