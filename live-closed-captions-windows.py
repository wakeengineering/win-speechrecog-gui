"""
Windows Live Captions Scraper
Captures text from Windows Live Captions and displays in a custom overlay.
"""

import tkinter as tk
from tkinter import ttk
import time
import threading
import configparser
import os
import sys
import atexit
from collections import deque

try:
    import pygetwindow as gw
    from pywinauto import Application
    from pywinauto.findwindows import ElementNotFoundError
    import win32gui
    import win32con
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please install: pip install pywinauto pygetwindow pywin32")
    sys.exit(1)

# Global state
caption_text = ""
running = True
config = {}
live_captions_window = None

def cleanup_on_exit():
    """Cleanup handler for atexit"""
    global running
    running = False
    show_live_captions()
    print("Cleanup complete")

# Register cleanup handler
atexit.register(cleanup_on_exit)

def load_config():
    """Load configuration from config.ini"""
    global config
    config_parser = configparser.ConfigParser()
    
    # Default values
    defaults = {
        'update_interval_ms': '100',
        'window_width': '800',
        'window_height': '150',
        'window_opacity': '0.75',
        'font_family': 'proportional_sans_serif',
        'font_size': '18',
        'max_caption_lines': '3',
        'bg_color': '#000000',
        'text_color': '#FFFFFF',
        'text_outline': 'true',
        'outline_color': '#000000',
        'text_shadow': 'false',
        'shadow_color': '#000000',
        'hide_live_captions': 'false',
        'debug_output': 'false',
        'idle_timeout_seconds': '10',
        'transparent_background': 'false',
        'transparent_color': '#ff00ff',
        'show_status_bar': 'true'
    }
    
    if os.path.exists('config.ini'):
        config_parser.read('config.ini')
    
    # Get values with defaults (section name is case-insensitive)
    for key, default in defaults.items():
        if config_parser.has_section('WINDOWS'):
            config[key] = config_parser.get('WINDOWS', key, fallback=default)
        else:
            config[key] = default
    
    # Convert types
    config['update_interval_ms'] = int(config['update_interval_ms'])
    config['window_width'] = int(config['window_width'])
    config['window_height'] = int(config['window_height'])
    config['window_opacity'] = float(config['window_opacity'])
    config['font_size'] = int(config['font_size'])
    config['max_caption_lines'] = max(1, min(5, int(config['max_caption_lines'])))  # Clamp 1-5
    config['idle_timeout_seconds'] = int(config['idle_timeout_seconds'])
    config['hide_live_captions'] = config['hide_live_captions'].lower() == 'true'
    config['debug_output'] = config['debug_output'].lower() == 'true'
    config['text_outline'] = config['text_outline'].lower() == 'true'
    config['text_shadow'] = config['text_shadow'].lower() == 'true'
    config['transparent_background'] = config['transparent_background'].lower() == 'true'
    config['show_status_bar'] = config.get('show_status_bar', 'true').lower() == 'true'
    
    # Map font family names to actual font families
    font_map = {
        'mono_sans_serif': ('Consolas', 'Courier New', 'monospace'),
        'small_caps': ('Arial', 'normal'),  # We'll handle small caps via font styling
        'proportional_sans_serif': ('Arial', 'Segoe UI', 'Helvetica')
    }
    
    font_family_key = config.get('font_family', 'proportional_sans_serif')
    if font_family_key in font_map:
        config['font_tuple'] = font_map[font_family_key][0]  # Use first font in tuple
    else:
        config['font_tuple'] = 'Arial'
    
    if config['debug_output']:
        print(f"Config loaded: hide_live_captions={config['hide_live_captions']}")
        print(f"  Font: {config['font_tuple']}, Size: {config['font_size']}")
        print(f"  Max lines: {config['max_caption_lines']}")

def find_live_captions_window():
    """Find the Windows Live Captions window"""
    try:
        # Try to find the window by exact title match only
        # Windows Live Captions typically has this exact title
        titles = [
            "Live captions",
            "Live Captions",
        ]
        
        for title in titles:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                # Additional validation: check if it's a small window
                # Live Captions is typically a small overlay
                for window in windows:
                    try:
                        # Live Captions is usually < 1000px wide
                        if window.width < 1000 and window.height < 400:
                            hwnd = window._hWnd
                            class_name = win32gui.GetClassName(hwnd)
                            print(f"Found candidate: '{window.title}' (class: {class_name}, size: {window.width}x{window.height})")
                            return window
                    except:
                        continue
                
    except Exception as e:
        print(f"Error finding Live Captions window: {e}")
    
    return None

def hide_live_captions():
    """Hide the original Live Captions window"""
    global live_captions_window
    
    if not config.get('hide_live_captions', False):
        print("Not hiding Live Captions (hide_live_captions=false)")
        return
    
    if live_captions_window:
        try:
            # Double-check the window title before hiding (safety check)
            title = live_captions_window.title.lower()
            if "live captions" in title or "captions" == title:
                hwnd = live_captions_window._hWnd
                # Don't use SW_HIDE - it prevents UI Automation from reading the window
                # Instead, move it off-screen so it's not visible but still readable
                win32gui.SetWindowPos(hwnd, 0, -10000, -10000, 0, 0, 
                                    win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
                print(f"✓ Moved Live Captions window off-screen: '{live_captions_window.title}'")
            else:
                print(f"⚠ Skipped hiding window '{live_captions_window.title}' - doesn't match Live Captions")
                live_captions_window = None
        except Exception as e:
            print(f"Error hiding Live Captions window: {e}")

def show_live_captions():
    """Show the original Live Captions window (for cleanup)"""
    global live_captions_window
    
    if live_captions_window:
        try:
            hwnd = live_captions_window._hWnd
            
            # Verify window still exists
            if not win32gui.IsWindow(hwnd):
                print("Live Captions window no longer exists")
                return
            
            # Get screen dimensions using tkinter
            temp_root = tk.Tk()
            temp_root.withdraw()
            screen_width = temp_root.winfo_screenwidth()
            screen_height = temp_root.winfo_screenheight()
            temp_root.destroy()
            
            x = (screen_width - 600) // 2
            y = screen_height - 200
            
            # Show the window first
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            
            # Move it to visible location with topmost temporarily
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, x, y, 0, 0, 
                                win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            
            # Small delay to ensure it renders
            time.sleep(0.1)
            
            # Remove always-on-top
            win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            
            # Force window update
            win32gui.InvalidateRect(hwnd, None, True)
            win32gui.UpdateWindow(hwnd)
            
            print("✓ Restored original Live Captions window to center-bottom")
        except Exception as e:
            print(f"Error restoring Live Captions window: {e}")
            print("To manually restore: Press Win+Ctrl+L twice (toggle off/on)")

def extract_captions_ui_automation():
    """Extract captions using UI Automation via pywinauto"""
    global live_captions_window
    
    if not live_captions_window:
        live_captions_window = find_live_captions_window()
        if live_captions_window:
            print(f"Found Live Captions window: {live_captions_window.title}")
            hide_live_captions()
        else:
            return ""
    
    try:
        hwnd = live_captions_window._hWnd
        
        # Try to connect to the window using pywinauto
        app = Application(backend="uia").connect(handle=hwnd)
        window = app.window(handle=hwnd)
        
        # Try to find text elements
        text_elements = []
        button_texts = {'Settings', 'Close', 'settings', 'close'}  # Skip UI chrome
        
        try:
            # Get ALL descendants and check each one
            all_controls = window.descendants()
            
            for i, control in enumerate(all_controls):
                try:
                    control_type = control.element_info.control_type
                    content = control.window_text()
                    
                    if content and len(content.strip()) > 0:
                        # Skip buttons and known UI elements
                        if control_type == "Button" and content in button_texts:
                            continue
                        
                        # Prefer Text type controls, but capture others too
                        if control_type == "Text" or (control_type not in ["Button", "TitleBar"]):
                            if config.get('debug_output', False):
                                print(f"  Element {i}: {control_type} = '{content}'\"")
                            text_elements.append((control_type, content))
                except:
                    pass
        except Exception as e:
            print(f"Error enumerating controls: {e}")
        
        # Return the longest non-button, non-UI text element
        if text_elements:
            # Prefer Text type controls first
            text_controls = [content for ctype, content in text_elements if ctype == "Text"]
            if text_controls:
                result = max(text_controls, key=len)
            else:
                # Fall back to longest content from any type
                result = max(text_elements, key=lambda x: len(x[1]))[1]
            
            if config.get('debug_output', False):
                print(f"Extracted caption: '{result}'")
            return result
        else:
            if config.get('debug_output', False):
                print("No caption text elements found (found buttons/UI only)")
        
    except ElementNotFoundError:
        print("Live Captions window lost, will retry...")
        live_captions_window = None  # Reset, will try to find again
    except Exception as e:
        print(f"Error extracting captions: {e}")
    
    return ""

def extract_captions_fallback():
    """Fallback: Try to extract using window text directly"""
    global live_captions_window
    
    if not live_captions_window:
        return ""
    
    try:
        hwnd = live_captions_window._hWnd
        # Some windows store text in window title or window text
        length = win32gui.GetWindowTextLength(hwnd)
        if length > 0:
            text = win32gui.GetWindowText(hwnd)
            if text and text != live_captions_window.title:
                return text
    except Exception as e:
        print(f"Error in fallback extraction: {e}")
    
    return ""

def caption_worker():
    """Background thread to continuously extract captions"""
    global caption_text, running
    
    print("Caption worker started")
    print("Please ensure Windows Live Captions is enabled:")
    print("  Win+Ctrl+L to toggle Live Captions")
    print("  Or Settings > Accessibility > Captions")
    
    last_check = 0
    check_interval = config['update_interval_ms'] / 1000.0
    previous_text = ""
    last_update_time = time.time()
    
    while running:
        current_time = time.time()
        
        if current_time - last_check >= check_interval:
            # Try UI Automation first
            text = extract_captions_ui_automation()
            
            # Fallback to window text if UI Automation failed
            if not text:
                text = extract_captions_fallback()
            
            if text:
                # Detect new sentence: if new text doesn't start with previous text
                # or if new text is much shorter, it's a new sentence
                if previous_text and not text.startswith(previous_text) and len(text) > 3:
                    # New sentence detected, add newline separator
                    caption_text = caption_text + "\n" + text
                else:
                    # Same sentence continuing or first text
                    caption_text = text
                
                previous_text = text
                last_update_time = current_time  # Reset idle timer on new text
            
            last_check = current_time
        
        time.sleep(0.01)  # Small sleep to prevent CPU spinning

def create_overlay():
    """Create the caption overlay window"""
    root = tk.Tk()
    root.title("Live Captions")
    
    # Remove title bar for sleek look
    root.overrideredirect(True)
    
    # Window setup
    root.geometry(f"{config['window_width']}x{config['window_height']}")
    root.attributes('-topmost', True)
    
    # Handle transparent background mode
    if config.get('transparent_background', False):
        transparent_color = config.get('transparent_color', '#ff00ff')
        root.configure(bg=transparent_color)
        root.attributes('-transparentcolor', transparent_color)
        root.attributes('-alpha', 1.0)  # Full opacity for transparent mode
    else:
        root.configure(bg=config['bg_color'])
        root.attributes('-alpha', config['window_opacity'])
    
    # Enable window dragging
    def start_move(event):
        root._drag_start_x = event.x
        root._drag_start_y = event.y
    
    def do_move(event):
        x = root.winfo_x() + event.x - root._drag_start_x
        y = root.winfo_y() + event.y - root._drag_start_y
        root.geometry(f"+{x}+{y}")
    
    # Custom close button (subtle X in top-right corner)
    # Determine background color based on transparent mode
    label_bg = config.get('transparent_color', '#ff00ff') if config.get('transparent_background', False) else config['bg_color']
    
    close_button = tk.Label(
        root,
        text="×",
        font=("Arial", 16, "bold"),
        fg="#666666",
        bg=label_bg,
        cursor="hand2",
        padx=8,
        pady=2
    )
    close_button.place(relx=1.0, x=-5, y=5, anchor="ne")
    
    # Hover effects for close button
    def on_enter(e):
        close_button.config(fg="#FFFFFF")
    
    def on_leave(e):
        close_button.config(fg="#666666")
    
    close_button.bind("<Enter>", on_enter)
    close_button.bind("<Leave>", on_leave)
    
    # Make sure close button is on top
    close_button.lift()
    
    # Main content frame (for dragging)
    content_frame = tk.Frame(root, bg=label_bg)
    content_frame.pack(fill=tk.BOTH, expand=True)
    content_frame.bind("<Button-1>", start_move)
    content_frame.bind("<B1-Motion>", do_move)
    
    # Use Text widget for scrolling to bottom behavior
    text_wrap_length = config['window_width'] - 80
    caption_label = tk.Text(
        content_frame,
        font=(config['font_tuple'], config['font_size'], "bold"),
        fg=config['text_color'],
        bg=label_bg,
        wrap=tk.WORD,
        height=config.get('max_caption_lines', 3) * 2,  # Give enough height for text
        width=int(text_wrap_length / (config['font_size'] * 0.6)),
        borderwidth=0,
        highlightthickness=0,
        state=tk.DISABLED  # Read-only
    )
    caption_label.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
    caption_label.bind("<Button-1>", start_move)
    caption_label.bind("<B1-Motion>", do_move)
    
    # For compatibility with the rest of the code that expects caption_labels list
    caption_labels = [caption_label]
    
    # Status bar (optional)
    status_label = None
    if config.get('show_status_bar', True):
        status_frame = tk.Frame(root, bg=label_bg)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.bind("<Button-1>", start_move)
        status_frame.bind("<B1-Motion>", do_move)
        
        status_label = tk.Label(
            status_frame,
            text="Searching for Live Captions window...",
            font=("Arial", 8),
            fg="#555555",
            bg=label_bg,
            anchor="w"
        )
        status_label.pack(side=tk.LEFT, padx=15, pady=5)
        status_label.bind("<Button-1>", start_move)
        status_label.bind("<B1-Motion>", do_move)
    
    def update_captions():
        """Update the caption display - trim to configured max lines and clear if idle"""
        global live_captions_window, caption_text
        
        # Check if we should clear due to idle timeout
        if config.get('idle_timeout_seconds', 0) > 0 and caption_text:
            # Access the last update time from caption_worker's closure
            # We'll use a simpler approach: track it here instead
            if not hasattr(update_captions, 'last_activity'):
                update_captions.last_activity = time.time()
            
            current_time = time.time()
            idle_time = current_time - update_captions.last_activity
            
            if idle_time > config.get('idle_timeout_seconds', 0):
                caption_text = ""
                if config.get('debug_output', False):
                    print(f"Caption cleared due to {idle_time:.1f}s idle timeout")
        
        if caption_text:
            # Reset activity timer when there's new text
            update_captions.last_activity = time.time()
            
            # Update Text widget
            caption_label.config(state=tk.NORMAL)
            caption_label.delete("1.0", tk.END)
            caption_label.insert("1.0", caption_text)
            caption_label.config(state=tk.DISABLED)
            
            # Scroll to bottom to show latest text
            caption_label.see(tk.END)
            
            if status_label and live_captions_window:
                status_label.config(text="✓ Connected", fg="#00AA00")
        else:
            # Clear the text widget
            caption_label.config(state=tk.NORMAL)
            caption_label.delete("1.0", tk.END)
            caption_label.insert("1.0", "Waiting for captions...")
            caption_label.config(state=tk.DISABLED)
            
            if status_label:
                if live_captions_window:
                    status_label.config(text="✓ Connected | No speech", fg="#555555")
                else:
                    status_label.config(text="⚠ Searching...", fg="#AA6600")
        
        root.after(config['update_interval_ms'], update_captions)
    
    def on_closing():
        """Handle window close"""
        global running
        print("\nClosing overlay window...")
        running = False
        
        # Restore Live Captions BEFORE destroying our window
        print("Restoring Live Captions window...")
        show_live_captions()
        
        # Give it a moment to restore
        time.sleep(0.2)
        
        # Now destroy our window
        root.destroy()
        print("Overlay closed")
    
    # Bind close button click
    close_button.bind("<Button-1>", lambda e: on_closing())
    
    # Ensure close button stays on top
    close_button.lift()
    
    # Start caption updates
    root.after(config['update_interval_ms'], update_captions)
    
    print("\nOverlay window created!")
    print("Press Ctrl+C in terminal or close the window to exit")
    
    root.mainloop()

def main():
    """Main entry point"""
    global running
    
    print("=" * 60)
    print("Windows Live Captions Scraper")
    print("=" * 60)
    
    # Load config
    load_config()
    print(f"\nConfiguration loaded:")
    print(f"  Update interval: {config['update_interval_ms']}ms")
    print(f"  Window size: {config['window_width']}x{config['window_height']}")
    print(f"  Opacity: {config['window_opacity']}")
    print(f"  Hide original: {config['hide_live_captions']}")
    
    # Start caption worker thread
    worker_thread = threading.Thread(target=caption_worker, daemon=True)
    worker_thread.start()
    
    # Create and run overlay
    try:
        create_overlay()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        print("\nCleaning up...")
        running = False
        show_live_captions()  # Restore original window
        worker_thread.join(timeout=2)
    
    print("Exited successfully")
    print("\nIf Live Captions is still missing: Press Win+Ctrl+L twice to reset it")

if __name__ == "__main__":
    main()
