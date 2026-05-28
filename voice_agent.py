"""
FreeBaby Voice Agent
====================
Mobile voice-driven agent loop:
  1. User speaks -> STT -> text
  2. LLM thinks -> decides action
  3. Execute action (UI automation / code / reply)
  4. TTS speaks result
  5. Loop back to 1

Run on Termux:
    python voice_agent.py

Requires: mobile_adapter.py, mykey.py, termux-api, AutoX.js
"""

import os
import sys
import json
import time
import traceback

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mobile_adapter import MobileAdapter
from agentmain import GeneraticAgent


class VoiceAgent:
    def __init__(self):
        self.phone = MobileAdapter()
        self.agent = GeneraticAgent()
        self.running = False
        self.conversation = []
    
    def check_deps(self):
        """Verify all dependencies are available."""
        status = self.phone.check_status()
        issues = []
        if not status["termux_api"]:
            issues.append("Termux:API not installed (pkg install termux-api)")
        if not status["edge_tts"]:
            issues.append("edge-tts not installed (pip install edge-tts)")
        if not status["autox_connected"]:
            issues.append("AutoX.js not connected (start AutoX.js HTTP server)")
        
        if issues:
            print("Missing dependencies:")
            for i in issues:
                print(f"  - {i}")
            return False
        print("All dependencies OK")
        return True
    
    def think_and_act(self, user_text):
        """Send user input to LLM, execute any actions it returns."""
        self.conversation.append({"role": "user", "content": user_text})
        
        # Build context with phone state
        context = self._build_context()
        
        # Ask LLM
        try:
            response = self.agent.chat(
                user_text,
                system_prompt=self._system_prompt(),
                context=context
            )
            self.conversation.append({"role": "assistant", "content": response})
            return response
        except Exception as e:
            error_msg = f"LLM error: {e}"
            print(f"[agent] {error_msg}")
            return error_msg
    
    def _system_prompt(self):
        return """You are FreeBaby, a voice-controlled phone assistant.
You can:
- Control the phone UI (tap, swipe, type, read screen)
- Answer questions
- Execute tasks

When the user asks you to do something on the phone:
1. Read the current screen with get_ui_tree
2. Find the right element to interact with
3. Perform the action (tap, type, swipe)
4. Report what you did

Keep responses SHORT and spoken-friendly (no markdown, no code blocks).
Respond in the same language the user speaks."""

    def _build_context(self):
        """Get current phone state for LLM context."""
        app = self.phone.get_current_app()
        app_info = f"Current app: {app}" if app else "Unknown app"
        return f"{app_info}\nTime: {time.strftime('%H:%M')}"
    
    def run(self):
        """Main voice agent loop."""
        print("=== FreeBaby Voice Agent ===")
        
        if not self.check_deps():
            print("\nFix the issues above and try again.")
            return
        
        self.phone.speak("FreeBaby ready. Say something.")
        self.running = True
        
        while self.running:
            try:
                # Listen for voice input
                print("\nListening...")
                text = self.phone.listen(timeout=15)
                
                if not text:
                    continue  # Silence, keep listening
                
                # Check for exit commands
                if any(w in text.lower() for w in ["exit", "quit", "bye", "stop", "close"]):
                    self.phone.speak("Goodbye!")
                    self.running = False
                    break
                
                # Process with LLM
                print(f"[user] {text}")
                response = self.think_and_act(text)
                print(f"[agent] {response}")
                
                # Speak response
                self.phone.speak(response)
                
            except KeyboardInterrupt:
                print("\nStopped by user.")
                self.running = False
                break
            except Exception as e:
                print(f"[error] {e}")
                traceback.print_exc()
                self.phone.speak("Something went wrong. Try again.")


def main():
    agent = VoiceAgent()
    agent.run()


if __name__ == "__main__":
    main()
