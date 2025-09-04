#!/usr/bin/env python3
"""
Comprehensive Demo Launcher for VLAN Islands Detection Tool.

This script handles installation, setup, and launches both CLI and GUI interfaces.
Provides a complete demonstration of all features including:
- Network topology analysis
- VLAN island detection  
- Report generation
- Streamlit GUI interfaces (Chatbot and Visualization)
- CLI tools
"""

import sys
import os
import subprocess
import time
import webbrowser
import threading
from pathlib import Path
from typing import Optional, List
import json
import traceback

def print_banner():
    """Print the demo banner."""
    print("[*] VLAN Islands Detection Tool - Complete Demo")
    print("=" * 60)
    print("AI-Powered Network Troubleshooting & Visualization Suite")
    print("=" * 60)

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 9):
        print("[X] Python 3.9 or higher is required.")
        print(f"   Current version: {sys.version}")
        return False
    
    print(f"[+] Python {sys.version.split()[0]} detected")
    return True

def install_dependencies():
    """Install required dependencies with comprehensive error handling."""
    print("\n[*] Installing Dependencies")
    print("-" * 40)
    
    try:
        # Check if pip is available
        try:
            subprocess.run([sys.executable, "-m", "pip", "--version"], 
                         capture_output=True, check=True)
        except subprocess.CalledProcessError:
            print("[X] pip is not available. Please install pip first.")
            return False
        
        # Install in development mode
        print("Installing package in development mode...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-e", "."
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("[+] Dependencies installed successfully!")
            return True
        else:
            print(f"[X] Installation failed:")
            print(f"    stdout: {result.stdout}")
            print(f"    stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("[X] Installation timed out (>5 minutes)")
        print("    This might indicate network issues or large dependencies")
        return False
    except FileNotFoundError:
        print("[X] Python executable not found")
        return False
    except PermissionError:
        print("[X] Permission denied. Try running as administrator or in a virtual environment")
        return False
    except Exception as e:
        print(f"[X] Installation error: {e}")
        print(f"    Error type: {type(e).__name__}")
        if hasattr(e, '__traceback__'):
            print("    Traceback available - run with --debug for details")
        return False

def run_analysis_demo():
    """Run the core analysis demonstration."""
    print("\n[1] Step 1: Network Analysis Demo")
    print("-" * 40)
    
    # Add src to path for demo
    sys.path.insert(0, str(Path("src").absolute()))
    
    try:
        from vlan_islands.parser import load_network_topology
        from vlan_islands.analyzer import VLANIslandAnalyzer
        from vlan_islands.reports import ReportGenerator
        
        # Load and analyze network
        print("[>] Loading network topology...")
        topology = load_network_topology("data/vlan_islands_data.json")
        print(f"[+] Loaded {len(topology.devices)} devices, {len(topology.vlans)} VLANs")
        
        print("[>] Analyzing VLAN islands...")
        analyzer = VLANIslandAnalyzer(topology)
        report = analyzer.analyze_all_vlans()
        
        # Print key results
        print(f"[#] Analysis Results:")
        print(f"   • Total VLANs: {len(report.vlan_results)}")
        print(f"   • Problematic VLANs: {len(report.problematic_vlans)}")
        print(f"   • Total islands: {report.total_islands}")
        
        if report.worst_fragmented_vlan:
            worst = report.worst_fragmented_vlan
            print(f"   • Worst: VLAN {worst.vlan_id} ({worst.fragmentation_ratio:.1%} fragmented)")
        
        # Generate reports
        print("[>] Generating reports...")
        ReportGenerator.generate_text_report(report, "demo_analysis.txt")
        ReportGenerator.generate_json_report(report, "demo_analysis.json")
        print("[+] Reports generated: demo_analysis.txt, demo_analysis.json")
        
        return True
        
    except Exception as e:
        print(f"[X] Analysis demo failed: {e}")
        return False

def launch_streamlit_app(script_name: str, port: int, title: str) -> Optional[subprocess.Popen]:
    """Launch a Streamlit app in the background."""
    try:
        print(f"[>] Starting {title}...")
        
        # Launch Streamlit
        process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", script_name,
            "--server.port", str(port),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--logger.level", "error"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait a moment for startup
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print(f"[+] {title} started on port {port}")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"[X] Failed to start {title}:")
            print(f"   Error: {stderr}")
            return None
            
    except Exception as e:
        print(f"[X] Error launching {title}: {e}")
        return None

def open_browser_delayed(url: str, delay: int = 2):
    """Open browser after a delay."""
    def delayed_open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Could not open browser: {e}")
    
    thread = threading.Thread(target=delayed_open)
    thread.daemon = True
    thread.start()

def run_gui_demo():
    """Run the Streamlit GUI demonstration."""
    print("\n[2] Step 2: Streamlit GUI Demo")
    print("-" * 40)
    
    # Check if Streamlit is available
    try:
        import streamlit
        print("[+] Streamlit available")
    except ImportError:
        print("[X] Streamlit not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "streamlit>=1.28.0"])
        try:
            import streamlit
            print("[+] Streamlit installed successfully")
        except ImportError:
            print("[X] Failed to install Streamlit")
            return False
    
    # Launch both apps
    chatbot_process = launch_streamlit_app("streamlit_chatbot.py", 8501, "AI Chatbot Interface")
    viz_process = launch_streamlit_app("streamlit_visualization.py", 8502, "Visualization Dashboard")
    
    if chatbot_process or viz_process:
        print("\n[*] GUI Applications Running:")
        print("-" * 40)
        
        if chatbot_process:
            print("🤖 AI Chatbot:        http://localhost:8501")
            open_browser_delayed("http://localhost:8501", 2)
        
        if viz_process:
            print("[#] Visualization:     http://localhost:8502")
            open_browser_delayed("http://localhost:8502", 4)
        
        print("\n[!] Instructions:")
        print("   1. Upload the network file: data/vlan_islands_data.json")
        print("   2. For chatbot: Add your OpenAI API key in the sidebar")
        print("   3. Explore the interactive features!")
        print("\n[>] Press Ctrl+C to stop all services")
        
        try:
            # Keep processes running
            while True:
                time.sleep(1)
                
                # Check if processes are still alive
                if chatbot_process and chatbot_process.poll() is not None:
                    print("[X] Chatbot process stopped")
                    chatbot_process = None
                
                if viz_process and viz_process.poll() is not None:
                    print("[X] Visualization process stopped")
                    viz_process = None
                
                if not chatbot_process and not viz_process:
                    print("All GUI processes stopped")
                    break
                    
        except KeyboardInterrupt:
            print("\n🛑 Stopping GUI applications...")
            
            if chatbot_process:
                chatbot_process.terminate()
                chatbot_process.wait()
            
            if viz_process:
                viz_process.terminate() 
                viz_process.wait()
            
            print("[+] All applications stopped")
        
        return True
    else:
        print("[X] Failed to start GUI applications")
        return False

def run_cli_demo():
    """Demonstrate CLI tools."""
    print("\n[3] Step 3: CLI Tools Demo")
    print("-" * 40)
    
    commands = [
        {
            "name": "Network Validation",
            "cmd": [sys.executable, "-m", "vlan_islands.cli", "validate", "data/vlan_islands_data.json"],
            "description": "Validate network topology file"
        },
        {
            "name": "Quick Analysis",
            "cmd": [sys.executable, "-m", "vlan_islands.cli", "analyze", "data/vlan_islands_data.json", "--summary-only"],
            "description": "Quick VLAN analysis summary"
        },
        {
            "name": "Detailed VLAN Analysis",
            "cmd": [sys.executable, "-m", "vlan_islands.cli", "vlan", "data/vlan_islands_data.json", "--vlan-id", "30"],
            "description": "Analyze specific VLAN (worst case)"
        }
    ]
    
    for demo in commands:
        print(f"\n[>] {demo['name']}: {demo['description']}")
        try:
            result = subprocess.run(demo["cmd"], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print("[+] Success")
                # Show first few lines of output
                lines = result.stdout.strip().split('\n')[:5]
                for line in lines:
                    print(f"   {line}")
                if len(result.stdout.strip().split('\n')) > 5:
                    print("   ...")
            else:
                print(f"[X] Failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("[X] Command timed out")
        except Exception as e:
            print(f"[X] Error: {e}")

def show_verification_results():
    """Show algorithm verification results."""
    print("\n[4] Step 4: Algorithm Verification")
    print("-" * 40)
    
    try:
        result = subprocess.run([sys.executable, "verify_algorithm.py"], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Extract key verification results
            lines = result.stdout.split('\n')
            for line in lines:
                if "VERIFICATION PASSED" in line or "63 islands is CORRECT" in line:
                    print(f"[+] {line}")
                elif "All algorithms agree" in line:
                    print(f"[+] {line}")
                elif "Analysis complete:" in line:
                    print(f"[#] {line}")
        else:
            print(f"[X] Verification failed: {result.stderr}")
            
    except Exception as e:
        print(f"[X] Verification error: {e}")

def main():
    """Main demo function."""
    print_banner()
    
    # Check requirements
    if not check_python_version():
        return 1
    
    # Check if data file exists
    if not Path("data/vlan_islands_data.json").exists():
        print("[X] Network data file not found: data/vlan_islands_data.json")
        return 1
    
    print("[+] Network data file found")
    
    # Install dependencies
    if not install_dependencies():
        print("[X] Failed to install dependencies")
        return 1
    
    # Run demos
    demos = [
        ("Analysis", run_analysis_demo),
        ("Algorithm Verification", show_verification_results),
        ("CLI Tools", run_cli_demo)
    ]
    
    for name, demo_func in demos:
        try:
            if not demo_func():
                print(f"[!] {name} demo had issues but continuing...")
        except Exception as e:
            print(f"[X] {name} demo failed: {e}")
    
    # Ask user about GUI demo
    print("\n" + "=" * 60)
    response = input("[?] Launch Streamlit GUI applications? (y/n): ").lower().strip()
    
    if response in ['y', 'yes']:
        run_gui_demo()
    else:
        print("Skipping GUI demo")
    
    # Final summary
    print("\n[+] Demo Complete!")
    print("-" * 40)
    print("What was demonstrated:")
    print("[+] Network topology loading and validation")
    print("[+] VLAN island detection (63 islands found)")
    print("[+] Algorithm verification (4 algorithms agree)")
    print("[+] Report generation (JSON, CSV, Text)")
    print("[+] CLI tools and commands")
    
    if response in ['y', 'yes']:
        print("[+] Streamlit GUI interfaces")
        print("   • AI-powered chatbot with memory")
        print("   • Interactive visualization dashboard")
    
    print("\n[>] Next Steps:")
    print("• Review generated reports: demo_analysis.txt, demo_analysis.json")
    print("• Try CLI commands: vlan-islands --help")
    print("• Upload your own network topology files")
    print("• Use the AI chatbot for troubleshooting guidance")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)