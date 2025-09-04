#!/usr/bin/env python3
"""
Quick launcher for Streamlit GUI applications.
"""

import subprocess
import sys
import time
import webbrowser
import threading

def open_browser_delayed(url: str, delay: int = 3):
    """Open browser after a delay."""
    def delayed_open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    
    thread = threading.Thread(target=delayed_open)
    thread.daemon = True
    thread.start()

def main():
    print("🚀 Launching VLAN Islands GUI Applications")
    print("=" * 50)
    
    # Launch chatbot
    print("Starting AI Chatbot on port 8501...")
    chatbot_process = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "streamlit_chatbot.py",
        "--server.port", "8501",
        "--server.headless", "true"
    ])
    
    # Launch visualization
    print("Starting Visualization Dashboard on port 8502...")
    viz_process = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "streamlit_visualization.py", 
        "--server.port", "8502",
        "--server.headless", "true"
    ])
    
    print("\n🌐 Applications starting...")
    print("🤖 AI Chatbot:        http://localhost:8501")
    print("📊 Visualization:     http://localhost:8502")
    
    # Open browsers
    open_browser_delayed("http://localhost:8501", 3)
    open_browser_delayed("http://localhost:8502", 5)
    
    print("\n💡 Instructions:")
    print("   1. Upload data/vlan_islands_data.json in both apps")
    print("   2. For chatbot: Enter OpenAI API key in sidebar")
    print("   3. Chat: Just type and press Enter (no send button needed)")
    print("   4. Try commands: /clear or /restart")
    print("\n🔧 Chatbot Improvements:")
    print("   • Native Streamlit chat interface")
    print("   • Auto-submit on Enter key")
    print("   • Light theme with better visibility")
    print("   • Improved API key input")
    print("\n⌨️  Press Ctrl+C to stop")
    
    try:
        chatbot_process.wait()
        viz_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping applications...")
        chatbot_process.terminate()
        viz_process.terminate()
        chatbot_process.wait()
        viz_process.wait()
        print("✅ Applications stopped")

if __name__ == "__main__":
    main()
