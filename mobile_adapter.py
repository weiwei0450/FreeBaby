"""
FreeBaby Mobile Adapter
=======================
Bridges FreeBaby agent to phone capabilities:
- AutoX.js: UI automation via Accessibility Service (tap/swipe/type/read screen)
- Termux:API: Voice input (speech-to-text), TTS output, device sensors

Requires on phone:
  - Termux + python + termux-api pkg
  - AutoX.js app (from GitHub) with HTTP server enabled
  - Termux:API app (from F-Droid)

Usage:
    from mobile_adapter import MobileAdapter
    phone = MobileAdapter()
    phone.speak("hello")          # TTS output
    text = phone.listen()          # STT input
    phone.tap(500, 1000)           # tap screen
    ui = phone.get_ui_tree()       # read current screen
"""

import requests
import subprocess
import json
import os
import tempfile
from pathlib import Path


class MobileAdapter:
    def __init__(self, autox_host="127.0.0.1", autox_port=8765):
        self.autox_url = f"http://{autox_host}:{autox_port}"
        self.tts_voice = "zh-CN-XiaoxiaoNeural"  # edge-tts Chinese voice
        self.tts_rate = "+0%"
        
    # ==================== Voice Input (Termux:API STT) ====================
    
    def listen(self, lang="zh-CN", timeout=10):
        """Record speech and return transcribed text.
        Uses Android native speech recognition via termux-speech-to-text.
        Returns empty string if nothing recognized.
        """
        try:
            result = subprocess.run(
                ["termux-speech-to-text", "-l", lang],
                capture_output=True, text=True, timeout=timeout
            )
            text = result.stdout.strip()
            if text:
                print(f"[voice] Heard: {text}")
            return text
        except subprocess.TimeoutExpired:
            print("[voice] No speech detected")
            return ""
        except FileNotFoundError:
            print("[voice] termux-speech-to-text not found, install termux-api")
            return ""
    
    # ==================== Voice Output (edge-tts) ====================
    
    def speak(self, text, block=True):
        """Convert text to speech and play via Android media player.
        Uses edge-tts (Microsoft free TTS) for high quality Chinese voice.
        """
        if not text:
            return
        try:
            # Strip non-ASCII for safety
            clean = text.encode('ascii', 'replace').decode() if os.name == 'nt' else text
            outfile = os.path.join(tempfile.gettempdir(), "freebaby_tts.mp3")
            
            # Generate audio with edge-tts
            subprocess.run(
                ["edge-tts", "--voice", self.tts_voice, "--rate", self.tts_rate,
                 "--text", text, "--write-media", outfile],
                capture_output=True, timeout=30
            )
            
            # Play with termux-media-player
            if block:
                subprocess.run(
                    ["termux-media-player", "play", outfile],
                    capture_output=True, timeout=60
                )
            else:
                subprocess.Popen(
                    ["termux-media-player", "play", outfile],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
        except Exception as e:
            print(f"[tts] Error: {e}")
    
    # ==================== UI Automation (AutoX.js HTTP API) ====================
    
    def _autox_request(self, endpoint, data=None, timeout=10):
        """Send request to AutoX.js HTTP server."""
        try:
            url = f"{self.autox_url}/{endpoint}"
            if data:
                resp = requests.post(url, json=data, timeout=timeout)
            else:
                resp = requests.get(url, timeout=timeout)
            return resp.json()
        except requests.ConnectionError:
            print(f"[autox] Cannot connect to AutoX.js at {self.autox_url}")
            print("[autox] Make sure AutoX.js is running with HTTP server enabled")
            return None
        except Exception as e:
            print(f"[autox] Error: {e}")
            return None
    
    def tap(self, x, y):
        """Tap screen at coordinates (x, y)."""
        return self._autox_request("click", {"x": x, "y": y})
    
    def long_press(self, x, y, duration=1000):
        """Long press at coordinates."""
        return self._autox_request("longClick", {"x": x, "y": y, "duration": duration})
    
    def swipe(self, x1, y1, x2, y2, duration=500):
        """Swipe from (x1,y1) to (x2,y2)."""
        return self._autox_request("swipe", {
            "x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration": duration
        })
    
    def input_text(self, text):
        """Type text into the currently focused input field."""
        return self._autox_request("input", {"text": text})
    
    def press_key(self, key_name):
        """Press a key (back, home, recent, volume_up, etc.)."""
        return self._autox_request("pressKey", {"key": key_name})
    
    def back(self):
        """Press back button."""
        return self.press_key("back")
    
    def home(self):
        """Press home button."""
        return self.press_key("home")
    
    def get_ui_tree(self, depth=8):
        """Get current screen UI element tree.
        Returns structured UI info without needing screenshots.
        Much more reliable than OCR for Android automation.
        """
        return self._autox_request("uiTree", {"depth": depth})
    
    def get_current_app(self):
        """Get current foreground app package name and activity."""
        return self._autox_request("currentApp")
    
    def launch_app(self, package_name):
        """Launch an app by package name."""
        return self._autox_request("launch", {"packageName": package_name})
    
    def screenshot(self, save_path=None):
        """Take screenshot and save locally.
        Returns path to saved image.
        """
        if not save_path:
            save_path = os.path.join(tempfile.gettempdir(), "freebaby_screen.png")
        result = self._autox_request("screenshot", {"path": save_path})
        if result and result.get("success"):
            return save_path
        return None
    
    def find_and_tap(self, text=None, desc=None, id_=None):
        """Find a UI element by text/description/id and tap it.
        Convenience method combining find + tap.
        """
        data = {}
        if text: data["text"] = text
        if desc: data["desc"] = desc
        if id_: data["id"] = id_
        return self._autox_request("findAndClick", data)
    
    # ==================== Device Info ====================
    
    def get_clipboard(self):
        """Get clipboard content."""
        try:
            r = subprocess.run(["termux-clipboard-get"], capture_output=True, text=True)
            return r.stdout.strip()
        except Exception:
            return ""
    
    def set_clipboard(self, text):
        """Set clipboard content."""
        try:
            subprocess.run(["termux-clipboard-set", text], capture_output=True)
        except Exception:
            pass
    
    def get_battery(self):
        """Get battery info."""
        result = self._autox_request("battery")
        return result
    
    def notify(self, title, content):
        """Show Android notification."""
        try:
            subprocess.run(
                ["termux-notification", "--title", title, "--content", content],
                capture_output=True
            )
        except Exception:
            pass
    
    # ==================== Status Check ====================
    
    def check_status(self):
        """Check which components are available."""
        status = {
            "termux_api": False,
            "autox_connected": False,
            "edge_tts": False,
        }
        
        # Check termux-api
        try:
            subprocess.run(["termux-speech-to-text", "--help"],
                         capture_output=True, timeout=5)
            status["termux_api"] = True
        except Exception:
            pass
        
        # Check AutoX.js
        result = self._autox_request("ping")
        if result:
            status["autox_connected"] = True
        
        # Check edge-tts
        try:
            subprocess.run(["edge-tts", "--version"],
                         capture_output=True, timeout=5)
            status["edge_tts"] = True
        except Exception:
            pass
        
        return status


if __name__ == "__main__":
    phone = MobileAdapter()
    status = phone.check_status()
    print("FreeBaby Mobile Adapter Status:")
    for k, v in status.items():
        icon = "OK" if v else "MISSING"
        print(f"  [{icon}] {k}")
