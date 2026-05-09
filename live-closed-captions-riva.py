import tkinter as tk
from tkinter import ttk
import threading
import queue
import sounddevice as sd
import numpy as np
import configparser
import os
import sys

try:
    import riva.client
    from riva.client import AudioEncoding
except Exception:
    riva = None
    AudioEncoding = None


class RivaCaptionOverlay:
    def __init__(self, root):
        self.root = root
        self.root.title("Game Caption Overlay - Riva")
        self.root.geometry("750x300")
        self.root.configure(bg='black')
        self.root.attributes('-alpha', 0.95)
        self.root.attributes('-topmost', True)

        control_frame = tk.Frame(self.root, bg='#1a1a1a', height=80)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        device_frame = tk.Frame(control_frame, bg='#1a1a1a')
        device_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(device_frame, text="Audio Source:", fg="white", bg='#1a1a1a', font=("Arial", 9)).pack(side=tk.LEFT, padx=5)

        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(device_frame, textvariable=self.device_var, state='readonly', width=40)
        self.device_combo.pack(side=tk.LEFT, padx=5)
        self.device_combo.bind('<<ComboboxSelected>>', self.on_device_change)

        refresh_btn = tk.Button(device_frame, text="Refresh", command=self.refresh_devices, bg='#333333', fg='white', relief=tk.FLAT, padx=10)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        status_frame = tk.Frame(control_frame, bg='#1a1a1a')
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_label = tk.Label(
            status_frame,
            text="Status: Initializing...",
            font=("Arial", 10, "bold"),
            fg="orange",
            bg='#1a1a1a'
        )
        self.status_label.pack(side=tk.LEFT)

        self.riva_status_label = tk.Label(
            status_frame,
            text="Riva: Disconnected",
            font=("Arial", 10),
            fg="gray",
            bg='#1a1a1a',
            padx=15
        )
        self.riva_status_label.pack(side=tk.RIGHT)

        separator = tk.Frame(self.root, bg='#333333', height=2)
        separator.pack(fill=tk.X)

        caption_frame = tk.Frame(self.root, bg='black')
        caption_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)

        self.caption_label = tk.Label(
            caption_frame,
            text="Waiting for audio...",
            font=("Arial", 14, "bold"),
            fg="white",
            bg="black",
            wraplength=720,
            justify=tk.LEFT,
            anchor=tk.NW
        )
        self.caption_label.pack(fill=tk.BOTH, expand=True)

        self.root.bind('<Button-1>', self.start_drag)
        self.root.bind('<B1-Motion>', self.do_drag)
        self.drag_data = {"x": 0, "y": 0}

        self.audio_queue = queue.Queue()
        self.caption_queue = queue.Queue()
        self.running = True
        self.audio_device_id = None

        self.config = self.load_config()
        self.riva_client = None

        self.recognition_thread = threading.Thread(target=self.recognition_worker, daemon=True)
        self.recognition_thread.start()

        self.audio_thread = threading.Thread(target=self.audio_worker, daemon=True)
        self.audio_thread.start()

        self.refresh_devices()
        self.update_caption()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), "config.ini")
        config.read(config_path)
        return config

    def get_audio_devices(self):
        devices = sd.query_devices()
        input_devices = {}
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices[i] = device
        return input_devices

    def refresh_devices(self):
        input_devices = self.get_audio_devices()
        device_names = []
        for device_id, device_info in input_devices.items():
            name = device_info['name']
            display_name = f"{device_id}: {name}"
            device_names.append((display_name, device_id))

        device_names.sort(key=lambda x: x[0])
        display_list = [name for name, _ in device_names]
        self.device_combo['values'] = display_list

        if display_list and not self.device_var.get():
            self.device_combo.current(0)
            self.audio_device_id = device_names[0][1]

    def on_device_change(self, event=None):
        selected = self.device_var.get()
        if selected:
            device_id = int(selected.split(':')[0])
            self.audio_device_id = device_id
            self.caption_queue.put(f"Device changed to: {selected.split(': ')[1]}")

    def init_riva(self):
        if riva is None:
            self.caption_queue.put("Riva client not installed")
            self.riva_status_label.config(text="Riva: Client Missing", fg="red")
            return False

        endpoint = self.config.get("RIVA", "endpoint", fallback="localhost:50051")
        use_ssl = self.config.getboolean("RIVA", "use_ssl", fallback=False)
        language_code = self.config.get("RIVA", "language_code", fallback="en-US")

        try:
            auth = riva.client.Auth(uri=endpoint, use_ssl=use_ssl)
            self.riva_client = riva.client.ASRService(auth)
            self.language_code = language_code
            self.riva_status_label.config(text="Riva: Connected", fg="lime")
            return True
        except Exception as e:
            self.caption_queue.put(f"Riva init failed: {e}")
            self.riva_status_label.config(text="Riva: Connection Failed", fg="red")
            return False

    def audio_worker(self):
        try:
            while self.audio_device_id is None and self.running:
                continue

            sample_rate = self.config.getint("AUDIO", "sample_rate", fallback=16000)
            chunk_size = self.config.getint("AUDIO", "chunk_size", fallback=4000)

            with sd.InputStream(
                channels=1,
                samplerate=sample_rate,
                blocksize=chunk_size,
                device=self.audio_device_id
            ):
                while self.running:
                    data = sd.rec(chunk_size, samplerate=sample_rate, channels=1, blocking=True)
                    audio_data = (data * 32767).astype(np.int16).tobytes()
                    self.audio_queue.put(audio_data)
        except Exception as e:
            self.caption_queue.put(f"Audio Error: {e}")

    def recognition_worker(self):
        if not self.init_riva():
            self.caption_queue.put("Failed to initialize Riva")
            return

        self.caption_queue.put("Ready")

        sample_rate = self.config.getint("AUDIO", "sample_rate", fallback=16000)
        
        while self.running:
            try:
                audio_data = self.audio_queue.get(timeout=1)
                
                # Riva streaming ASR request
                response = self.riva_client.recognize(
                    audio=audio_data,
                    language_code=self.language_code,
                    encoding=AudioEncoding.LINEAR_PCM,
                    sample_rate_hz=sample_rate,
                    max_alternatives=1,
                    enable_automatic_punctuation=True
                )

                if response.results:
                    transcript = response.results[0].alternatives[0].transcript
                    if transcript.strip():
                        self.caption_queue.put(transcript)
            except queue.Empty:
                continue
            except Exception as e:
                self.caption_queue.put(f"Recognition error: {e}")

    def update_caption(self):
        try:
            while True:
                message = self.caption_queue.get_nowait()
                if message == "Ready":
                    self.status_label.config(text="Status: LISTENING (Ready)", fg="lime")
                    self.caption_label.config(text="Waiting for speech...")
                elif message.startswith("Error") or message.endswith("failed"):
                    self.status_label.config(text=f"Status: {message}", fg="red")
                else:
                    self.caption_label.config(text=message)
                    self.status_label.config(text="Status: Recording...", fg="yellow")
        except queue.Empty:
            pass

        self.root.after(100, self.update_caption)

    def start_drag(self, event):
        self.drag_data["x"] = event.x_root - self.root.winfo_x()
        self.drag_data["y"] = event.y_root - self.root.winfo_y()

    def do_drag(self, event):
        x = event.x_root - self.drag_data["x"]
        y = event.y_root - self.drag_data["y"]
        self.root.geometry(f"+{x}+{y}")

    def on_closing(self):
        self.running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = RivaCaptionOverlay(root)
    root.mainloop()


if __name__ == "__main__":
    main()
