import tkinter as tk
from tkinter import ttk
import threading
import queue
import time
import numpy as np
from vosk import Model, KaldiRecognizer
import json
import os
import configparser
import requests
import zipfile
import webrtcvad
import pyaudiowpatch as pyaudio

class GameCaptionOverlay:
    def __init__(self, root):
        self.root = root
        self.root.title("Game Caption Overlay")
        self.config = self.load_config()
        
        # Parse config options
        window_opacity = self.config.getfloat("UI", "window_opacity", fallback=0.75)
        window_width = self.config.getint("UI", "window_width", fallback=750)
        window_height = self.config.getint("UI", "window_height", fallback=150)
        font_size = self.config.getint("UI", "font_size", fallback=14)
        self.max_caption_lines = self.config.getint("UI", "max_caption_lines", fallback=3)
        self.idle_timeout = self.config.getint("UI", "idle_timeout_seconds", fallback=10)
        self.debug_output = self.config.getboolean("UI", "debug_output", fallback=False)
        self.text_outline = self.config.getboolean("UI", "text_outline", fallback=True)
        self.text_shadow = self.config.getboolean("UI", "text_shadow", fallback=False)
        self.outline_color = self.config.get("UI", "outline_color", fallback="#000000")
        self.shadow_color = self.config.get("UI", "shadow_color", fallback="#000000")
        self.transparent_background = self.config.getboolean("UI", "transparent_background", fallback=False)
        self.transparent_color = self.config.get("UI", "transparent_color", fallback="#ff00ff")
        self.show_status_bar = self.config.getboolean("UI", "show_status_bar", fallback=True)
        bg_color = self.config.get("UI", "bg_color", fallback="#000000")
        text_color = self.config.get("UI", "text_color", fallback="#FFFFFF")
        
        # Map font family
        font_family_key = self.config.get('UI', 'font_family', fallback='proportional_sans_serif')
        font_map = {
            'mono_sans_serif': 'Consolas',
            'small_caps': 'Arial',
            'proportional_sans_serif': 'Arial'
        }
        self.font_tuple = font_map.get(font_family_key, 'Arial')
        
        # Remove title bar for sleek look
        self.root.overrideredirect(True)
        
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.configure(bg=bg_color)
        
        # Handle transparent background mode
        if self.transparent_background:
            self.root.configure(bg=self.transparent_color)
            self.root.attributes('-transparentcolor', self.transparent_color)
            self.root.attributes('-alpha', 1.0)  # Full opacity for transparent mode
        else:
            self.root.configure(bg=bg_color)
            self.root.attributes('-alpha', window_opacity)
        
        self.root.attributes('-topmost', True)
        
        # Position at bottom center
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = screen_height - window_height - 100
        self.root.geometry(f"+{x}+{y}")
        
        # Store colors
        self.bg_color = bg_color
        self.text_color = text_color
        
        # Determine background color based on transparent mode
        label_bg = self.transparent_color if self.transparent_background else bg_color
        
        # Enable window dragging
        self.drag_data = {"x": 0, "y": 0}
        
        # Custom close button
        close_button = tk.Label(
            self.root,
            text="×",
            font=("Arial", 16, "bold"),
            fg="#666666",
            bg=label_bg,
            cursor="hand2",
            padx=8,
            pady=2
        )
        close_button.place(relx=1.0, x=-5, y=5, anchor="ne")
        
        def on_enter(e):
            close_button.config(fg="#FFFFFF")
        
        def on_leave(e):
            close_button.config(fg="#666666")
        
        close_button.bind("<Enter>", on_enter)
        close_button.bind("<Leave>", on_leave)
        close_button.bind("<Button-1>", lambda e: self.on_closing())
        
        # Main content frame
        content_frame = tk.Frame(self.root, bg=label_bg)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.bind('<Button-1>', self.start_drag)
        content_frame.bind('<B1-Motion>', self.do_drag)
        
        # Create layered labels for text effects
        self.caption_labels = []
        text_wrap_length = window_width - 80
        
        # In transparent mode, disable outline/shadow to prevent magenta bleeding
        use_outline = self.text_outline and not self.transparent_background
        use_shadow = self.text_shadow and not self.transparent_background
        
        # Drop shadow layer
        if use_shadow:
            shadow_label = tk.Label(
                content_frame,
                text="Initializing...",
                font=(self.font_tuple, font_size, "bold"),
                fg=self.shadow_color,
                bg=label_bg,
                wraplength=text_wrap_length,
                justify="left"
            )
            shadow_label.place(relx=0, rely=0, x=22, y=17, relwidth=1.0, relheight=1.0)
            shadow_label.bind('<Button-1>', self.start_drag)
            shadow_label.bind('<B1-Motion>', self.do_drag)
            self.caption_labels.append(shadow_label)
        
        # Outline layers
        if use_outline:
            outline_offsets = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
            for dx, dy in outline_offsets:
                outline_label = tk.Label(
                    content_frame,
                    text="Initializing...",
                    font=(self.font_tuple, font_size, "bold"),
                    fg=self.outline_color,
                    bg=label_bg,
                    wraplength=text_wrap_length,
                    justify="left"
                )
                outline_label.place(relx=0, rely=0, x=20+dx, y=15+dy, relwidth=1.0, relheight=1.0)
                outline_label.bind('<Button-1>', self.start_drag)
                outline_label.bind('<B1-Motion>', self.do_drag)
                self.caption_labels.append(outline_label)
        
        # Main caption label
        self.caption_label = tk.Label(
            content_frame,
            text="Initializing...",
            font=(self.font_tuple, font_size, "bold"),
            fg=text_color,
            bg=label_bg,
            wraplength=text_wrap_length,
            justify="left"
        )
        self.caption_label.place(relx=0, rely=0, x=20, y=15, relwidth=1.0, relheight=1.0)
        self.caption_label.bind('<Button-1>', self.start_drag)
        self.caption_label.bind('<B1-Motion>', self.do_drag)
        self.caption_labels.append(self.caption_label)
        
        # Status bar (optional)
        if self.show_status_bar:
            status_frame = tk.Frame(self.root, bg=label_bg)
            status_frame.pack(side=tk.BOTTOM, fill=tk.X)
            status_frame.bind('<Button-1>', self.start_drag)
            status_frame.bind('<B1-Motion>', self.do_drag)
            
            self.status_label = tk.Label(
                status_frame,
                text="Initializing...",
                font=("Arial", 8),
                fg="#555555",
                bg=label_bg,
                anchor="w"
            )
            self.status_label.pack(side=tk.LEFT, padx=15, pady=5)
            self.status_label.bind('<Button-1>', self.start_drag)
            self.status_label.bind('<B1-Motion>', self.do_drag)
        else:
            self.status_label = None
        
        # Ensure close button is on top
        close_button.lift()
        
        # Ensure close button is on top
        close_button.lift()
        
        # Audio queue and recognition
        self.audio_queue = queue.Queue()
        self.caption_queue = queue.Queue()
        self.running = True
        self.caption_text = ""
        self.current_partial = ""  # Track current partial result
        self.last_activity = time.time()
        self.model = None
        self.recognizer = None
        self.audio_thread = None
        self.recognition_thread = None
        self.vad = None
        self.vad_enabled = self.config.getboolean("SPEECH_RECOGNITION", "enable_vad", fallback=True)
        self.vad_aggressiveness = self.config.getint("SPEECH_RECOGNITION", "vad_aggressiveness", fallback=2)
        self.sample_rate = self.config.getint("AUDIO", "sample_rate", fallback=16000)
        self.chunk_size = self.config.getint("AUDIO", "chunk_size", fallback=4000)
        self.enable_normalization = self.config.getboolean("AUDIO", "enable_normalization", fallback=True)
        self.normalization_target = self.config.getfloat("AUDIO", "normalization_target", fallback=0.7)
        
        # Start recognition thread
        self.recognition_thread = threading.Thread(target=self.recognition_worker, daemon=True)
        self.recognition_thread.start()
        
        # Start audio capture thread
        self.audio_thread = threading.Thread(target=self.audio_worker, daemon=True)
        self.audio_thread.start()
        
        # Update caption display
        self.update_caption()
        
        # Window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def load_config(self):
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), "config.ini")
        config.read(config_path)
        
        # Set defaults for missing options
        if not config.has_section('UI'):
            config.add_section('UI')
        
        defaults = {
            'window_opacity': '0.75',
            'font_size': '14',
            'font_family': 'proportional_sans_serif',
            'max_caption_lines': '3',
            'text_outline': 'true',
            'outline_color': '#000000',
            'text_shadow': 'false',
            'shadow_color': '#000000',
            'idle_timeout_seconds': '10',
            'debug_output': 'false',
            'transparent_background': 'false',
            'transparent_color': '#ff00ff',
            'show_status_bar': 'true'
        }
        
        for key, value in defaults.items():
            if not config.has_option('UI', key):
                config.set('UI', key, value)
        
        return config
    
    def initialize_vosk(self):
        """Initialize Vosk speech recognition"""
        try:
            model_size = self.config.get("SPEECH_RECOGNITION", "model_size", fallback="small").lower()
            model_map = {
                "tiny": ("vosk-model-small-en-us-0.15", "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"),
                "small": ("vosk-model-small-en-us-0.15", "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"),
                "base": ("vosk-model-en-us-0.22", "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"),
                "large": ("vosk-model-en-us-0.22", "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"),
            }

            if model_size not in model_map:
                model_size = "small"

            extracted_name, model_url = model_map[model_size]
            model_path = f"model_{model_size}"
            
            # Download model if it doesn't exist
            if not os.path.exists(model_path):
                print("Downloading English model... (first time only)")
                self.caption_queue.put(("status", "Downloading speech model..."))
                
                zip_path = "vosk_model.zip"
                
                try:
                    # Download the model
                    response = requests.get(model_url, stream=True)
                    response.raise_for_status()
                    
                    total_size = int(response.headers.get('content-length', 0))
                    with open(zip_path, 'wb') as f:
                        downloaded = 0
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                percent = int((downloaded / total_size) * 100)
                                print(f"Download progress: {percent}%", end='\r')
                    
                    print("\nExtracting model...")
                    # Extract the model
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall()
                    
                    # Rename the extracted folder to model directory
                    if os.path.exists(extracted_name):
                        os.rename(extracted_name, model_path)
                    
                    # Clean up zip
                    os.remove(zip_path)
                    print("Model ready!")
                    
                except Exception as e:
                    print(f"Error downloading model: {e}")
                    self.caption_queue.put(("error", f"Model download failed: {e}"))
                    return False
            
            if self.sample_rate != 16000:
                self.sample_rate = 16000
            
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords([])  # Use full vocabulary
            return True
        except Exception as e:
            print(f"Error initializing Vosk: {e}")
            self.caption_queue.put(("error", f"Speech recognition error: {e}"))
            return False
    
    def initialize_vad(self):
        if not self.vad_enabled:
            return
        if self.sample_rate not in (8000, 16000, 32000, 48000):
            self.sample_rate = 16000
        self.vad = webrtcvad.Vad(self.vad_aggressiveness)

    def has_speech(self, audio_bytes):
        if not self.vad:
            return True

        frame_duration_ms = 30
        frame_size = int(self.sample_rate * frame_duration_ms / 1000) * 2
        if len(audio_bytes) < frame_size:
            return False

        total = len(audio_bytes) // frame_size
        for i in range(total):
            start = i * frame_size
            end = start + frame_size
            frame = audio_bytes[start:end]
            if self.vad.is_speech(frame, self.sample_rate):
                return True

        return False

    def resample_audio(self, audio_float, src_rate, dst_rate):
        if src_rate == dst_rate:
            return audio_float

        duration = len(audio_float) / float(src_rate)
        target_len = int(duration * dst_rate)
        if target_len <= 1:
            return audio_float

        x_old = np.linspace(0, duration, len(audio_float), endpoint=False)
        x_new = np.linspace(0, duration, target_len, endpoint=False)
        return np.interp(x_new, x_old, audio_float).astype(np.float32)
    
    def audio_worker(self):
        """Capture all system output (WASAPI loopback)"""
        try:
            self.caption_queue.put(("status", "Using system output capture"))
            self.capture_system_output()
        except Exception as e:
            print(f"Audio worker error: {e}")
            self.caption_queue.put(("error", f"Audio Error: {e}"))
    
    def capture_system_output(self):
        """Capture all system output using WASAPI loopback"""
        try:
            print("Starting system output capture via WASAPI loopback...")
            
            p = pyaudio.PyAudio()
            
            # Get WASAPI loopback info
            try:
                wasapi_info = p.get_default_wasapi_loopback()
            except Exception as e:
                print(f"Error getting WASAPI loopback: {e}")
                self.caption_queue.put(("error", "WASAPI loopback not available"))
                return
            
            # Open stream (captures all system audio for now)
            # Note: True per-process filtering requires low-level WASAPI APIs
            source_rate = int(wasapi_info['defaultSampleRate'])
            target_rate = self.sample_rate
            frames_per_buffer = max(256, int(source_rate * (self.chunk_size / float(target_rate))))

            stream = p.open(
                format=pyaudio.paInt16,
                channels=wasapi_info['maxInputChannels'],
                rate=source_rate,
                frames_per_buffer=frames_per_buffer,
                input=True,
                input_device_index=wasapi_info['index']
            )
            
            print("WASAPI loopback capture started (system audio)")
            self.caption_queue.put(("status", "Capturing system output"))
            
            while self.running:
                try:
                    data = stream.read(frames_per_buffer, exception_on_overflow=False)
                    audio_array = np.frombuffer(data, dtype=np.int16)
                    
                    # Convert to mono if stereo
                    if wasapi_info['maxInputChannels'] == 2:
                        audio_array = audio_array.reshape(-1, 2).mean(axis=1).astype(np.int16)
                    
                    audio_float = audio_array.astype(np.float32) / 32767.0
                    audio_float = self.resample_audio(audio_float, source_rate, target_rate)
                    
                    if self.enable_normalization:
                        peak = np.max(np.abs(audio_float))
                        if peak > 0:
                            scale = self.normalization_target / peak
                            audio_float = np.clip(audio_float * scale, -1.0, 1.0)
                    
                    audio_data = (audio_float * 32767).astype(np.int16).tobytes()
                    self.audio_queue.put(audio_data)
                except Exception as e:
                    if self.running:
                        print(f"WASAPI capture read error: {e}")
                    break
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
        except Exception as e:
            print(f"System output capture error: {e}")
            self.caption_queue.put(("error", f"System Output Error: {e}"))
    
    def recognition_worker(self):
        """Process audio and recognize speech"""
        if not self.initialize_vosk():
            self.caption_queue.put(("error", "Failed to initialize speech recognition"))
            return
        
        self.initialize_vad()
        
        self.caption_queue.put(("status", "Ready"))
        
        while self.running:
            try:
                audio_data = self.audio_queue.get(timeout=1)

                if self.vad_enabled and not self.has_speech(audio_data):
                    continue
                
                if self.recognizer.AcceptWaveform(audio_data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    if text:
                        # Final result - add as new line
                        self.caption_queue.put(("final", text))
                else:
                    # Partial result - update current line
                    partial = json.loads(self.recognizer.PartialResult())
                    text = partial.get('partial', '').strip()
                    if text:
                        self.caption_queue.put(("partial", text))
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Recognition error: {e}")
    
    
    def update_caption(self):
        """Update caption display from queue"""
        try:
            while True:
                msg = self.caption_queue.get_nowait()
                
                # Handle tuple messages (type, content)
                if isinstance(msg, tuple):
                    msg_type, content = msg
                    
                    if msg_type == "status":
                        if content == "Ready":
                            if self.status_label:
                                self.status_label.config(text="✓ Ready", fg="#00AA00")
                            for label in self.caption_labels:
                                label.config(text="Waiting for speech...")
                    elif msg_type == "error":
                        if self.status_label:
                            self.status_label.config(text=f"⚠ {content}", fg="#AA6600")
                    elif msg_type == "partial":
                        # Update current partial (don't add as new line yet)
                        self.current_partial = content
                        self.last_activity = time.time()
                        if self.status_label:
                            self.status_label.config(text="✓ Listening...", fg="#555555")
                    elif msg_type == "final":
                        # Final result - add as new line
                        if self.caption_text:
                            self.caption_text = self.caption_text + "\n" + content
                        else:
                            self.caption_text = content
                        self.current_partial = ""  # Clear partial
                        self.last_activity = time.time()
                        if self.status_label:
                            self.status_label.config(text="✓ Recording", fg="#00AA00")
                else:
                    # Handle old-style string messages
                    if msg.startswith("Downloading") or msg.startswith("Capturing"):
                        if self.status_label:
                            self.status_label.config(text=msg, fg="#555555")
                        for label in self.caption_labels:
                            label.config(text=msg)
        except queue.Empty:
            pass
        
        # Check idle timeout
        if self.idle_timeout > 0 and (self.caption_text or self.current_partial):
            current_time = time.time()
            idle_time = current_time - self.last_activity
            if idle_time > self.idle_timeout:
                self.caption_text = ""
                self.current_partial = ""
                if self.debug_output:
                    print(f"Caption cleared due to {idle_time:.1f}s idle timeout")
        
        # Update display - combine finalized text with current partial
        display_lines = []
        if self.caption_text:
            display_lines.extend(self.caption_text.split('\n'))
        if self.current_partial:
            display_lines.append(self.current_partial)
        
        if display_lines:
            display_text = "\n".join(display_lines)
            
            # Update main label to measure actual height
            self.caption_label.config(text=display_text)
            self.caption_label.update_idletasks()
            
            # Get actual text height vs available space
            text_height = self.caption_label.winfo_reqheight()
            window_height = self.config.getint("UI", "window_height", fallback=150)
            available_height = window_height - 40  # Account for padding and status bar
            
            # If overflowing, aggressively trim words from the top
            if text_height > available_height:
                # Trim by words, not just lines
                words = display_text.split()
                trim_words = len(words) // 4  # Start by removing 25%
                display_text = " ".join(words[trim_words:])
                
                # Keep trimming until it fits
                while trim_words < len(words):
                    self.caption_label.config(text=display_text)
                    self.caption_label.update_idletasks()
                    text_height = self.caption_label.winfo_reqheight()
                    
                    if text_height <= available_height:
                        break
                    
                    trim_words += max(1, len(words) // 10)  # Remove 10% more each iteration
                    if trim_words >= len(words):
                        display_text = " ".join(words[-20:])  # Keep last 20 words minimum
                        break
                    display_text = " ".join(words[trim_words:])
                
                # Update stored caption_text to trimmed version (preserve partial separately)
                if self.current_partial and display_text.endswith(self.current_partial):
                    self.caption_text = display_text[:-len(self.current_partial)].rstrip()
                else:
                    self.caption_text = display_text
            
            # Update all labels
            for label in self.caption_labels:
                label.config(text=display_text)
        else:
            for label in self.caption_labels:
                label.config(text="Waiting for speech...")
        
        self.root.after(100, self.update_caption)
    
    def start_drag(self, event):
        """Start window drag"""
        self.drag_data["x"] = event.x_root - self.root.winfo_x()
        self.drag_data["y"] = event.y_root - self.root.winfo_y()
    
    def do_drag(self, event):
        """Perform window drag"""
        x = event.x_root - self.drag_data["x"]
        y = event.y_root - self.drag_data["y"]
        self.root.geometry(f"+{x}+{y}")
    
    def on_closing(self):
        """Handle window close"""
        self.running = False
        self.root.destroy()

def main():
    root = tk.Tk()
    app = GameCaptionOverlay(root)
    root.mainloop()

if __name__ == "__main__":
    main()
