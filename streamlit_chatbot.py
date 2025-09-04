#!/usr/bin/env python3
"""
Streamlit Chatbot Interface for VLAN Islands Troubleshooting.

Interactive chatbot with memory context, chat history, and OpenAI integration.
"""

import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import json
import yaml

# Add src to path
sys.path.insert(0, str(Path("src").absolute()))

from vlan_islands.parser import load_network_topology, NetworkParseError
from vlan_islands.analyzer import VLANIslandAnalyzer
from vlan_islands.chatbot import NetworkChatbot, ChatMessage, ChatSession

# Page configuration
st.set_page_config(
    page_title="VLAN Islands AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better visibility and light theme
st.markdown("""
<style>
    /* Force light theme */
    .stApp {
        background-color: white !important;
        color: black !important;
    }
    
    /* Improve sidebar visibility */
    .stSidebar {
        background-color: #f8f9fa !important;
    }
    
    .stSidebar .stTextInput input {
        background-color: white !important;
        color: black !important;
        border: 1px solid #ddd !important;
    }
    
    /* Improve main content visibility */
    .stTextInput input {
        background-color: white !important;
        color: black !important;
        border: 1px solid #ddd !important;
    }
    
    /* Chat input styling */
    .stChatInput input {
        background-color: white !important;
        color: black !important;
        border: 1px solid #ddd !important;
    }
    
    /* Chat message styling */
    .stChatMessage {
        background-color: white !important;
        color: black !important;
        border: 1px solid #e6e6e6 !important;
        border-radius: 8px !important;
        margin: 10px 0 !important;
        padding: 10px !important;
    }
    
    /* Ensure text is visible */
    .stMarkdown, .stText, p, div {
        color: black !important;
    }
    
    /* Button styling */
    .stButton button {
        background-color: #007bff !important;
        color: white !important;
        border: none !important;
    }
    
    /* Metric styling */
    .stMetric {
        background-color: #f8f9fa !important;
        border: 1px solid #ddd !important;
        border-radius: 4px !important;
        padding: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if 'topology' not in st.session_state:
        st.session_state.topology = None
    if 'analysis_report' not in st.session_state:
        st.session_state.analysis_report = None
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = None
    if 'chat_session_id' not in st.session_state:
        st.session_state.chat_session_id = None
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = ""

def display_chat_message(message: Dict[str, str], is_user: bool = True):
    """Display a single chat message using Streamlit's native chat interface."""
    avatar = "👤" if is_user else "🤖"
    name = "You" if is_user else "AI Assistant"
    
    with st.chat_message(name, avatar=avatar):
        st.write(message['content'])
        if message.get('timestamp'):
            st.caption(f"⏰ {message['timestamp']}")

def load_network_data(uploaded_file) -> bool:
    """Load network topology from uploaded file."""
    try:
        if uploaded_file is not None:
            # Save uploaded file temporarily
            with open("temp_network.json", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Load topology
            topology = load_network_topology("temp_network.json")
            st.session_state.topology = topology
            
            # Analyze network
            with st.spinner("Analyzing network topology..."):
                analyzer = VLANIslandAnalyzer(topology)
                report = analyzer.analyze_all_vlans()
                st.session_state.analysis_report = report
            
            # Clean up temp file
            os.remove("temp_network.json")
            
            return True
    except NetworkParseError as e:
        st.error(f"Network parsing error: {e}")
    except Exception as e:
        st.error(f"Error loading network: {e}")
    
    return False

def load_chatbot_config() -> Dict:
    """Load chatbot configuration from YAML file."""
    try:
        with open("chatbot_config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        st.error(f"Error loading chatbot config: {e}")
        # Return default config
        return {
            "chatbot": {"name": "VLAN Islands AI Assistant", "model": "gpt-4"},
            "system_prompt": "You are a network troubleshooting assistant.",
            "specialties": []
        }

def initialize_chatbot(api_key: str) -> bool:
    """Initialize the AI chatbot with the provided API key."""
    try:
        if not api_key:
            st.warning("Please enter your OpenAI API key in the sidebar.")
            return False
        
        if st.session_state.topology is None or st.session_state.analysis_report is None:
            st.warning("Please upload a network topology file first.")
            return False
        
        # Set API key in environment
        os.environ["OPENAI_API_KEY"] = api_key
        
        # Load chatbot configuration
        config = load_chatbot_config()
        
        # Initialize chatbot with custom config
        chatbot = NetworkChatbot(
            st.session_state.topology, 
            st.session_state.analysis_report,
            config=config
        )
        st.session_state.chatbot = chatbot
        st.session_state.chatbot_config = config
        
        # Create chat session
        session_id = chatbot.create_session()
        st.session_state.chat_session_id = session_id
        
        return True
        
    except Exception as e:
        st.error(f"Error initializing chatbot: {e}")
        return False

def process_chat_command(user_input: str) -> Optional[str]:
    """Process special chat commands like /clear and /restart."""
    user_input = user_input.strip()
    
    if user_input.lower() in ["/clear", "/restart"]:
        # Clear chat history
        st.session_state.chat_messages = []
        
        # Create new chat session
        if st.session_state.chatbot:
            session_id = st.session_state.chatbot.create_session()
            st.session_state.chat_session_id = session_id
        
        return "Chat history cleared. Starting fresh conversation."
    
    return None

def main():
    """Main Streamlit application."""
    initialize_session_state()
    
    # Header
    st.title("🤖 VLAN Islands AI Assistant")
    st.markdown("Interactive troubleshooting assistant for network VLAN connectivity issues")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # OpenAI API Key
        st.subheader("🔑 OpenAI API Key")
        api_key = st.text_input(
            "Enter your OpenAI API Key:",
            type="password",
            value=st.session_state.openai_api_key,
            help="Required for AI chatbot functionality. Get your key from https://platform.openai.com/api-keys",
            placeholder="sk-..."
        )
        
        if api_key and api_key != st.session_state.openai_api_key:
            st.success("✅ API key updated!")
        elif not api_key:
            st.warning("⚠️ Please enter your OpenAI API key to enable the chatbot.")
        
        if api_key != st.session_state.openai_api_key:
            st.session_state.openai_api_key = api_key
            st.session_state.chatbot = None  # Reset chatbot when API key changes
        
        st.markdown("---")
        
        # Network topology upload
        st.subheader("📁 Network Topology")
        uploaded_file = st.file_uploader(
            "Upload network topology JSON file",
            type=['json'],
            help="Upload your network topology file to start analysis"
        )
        
        if uploaded_file is not None and st.session_state.topology is None:
            if load_network_data(uploaded_file):
                st.success("✅ Network topology loaded successfully!")
                st.rerun()
        
        # Network summary
        if st.session_state.analysis_report:
            st.markdown("---")
            st.subheader("📊 Network Summary")
            report = st.session_state.analysis_report
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total VLANs", len(report.vlan_results))
                st.metric("Problematic VLANs", len(report.problematic_vlans))
            with col2:
                st.metric("Total Islands", report.total_islands)
                st.metric("Healthy VLANs", len(report.healthy_vlans))
            
            if report.worst_fragmented_vlan:
                worst = report.worst_fragmented_vlan
                st.error(f"🚨 Worst: VLAN {worst.vlan_id} ({worst.fragmentation_ratio:.1%} fragmented)")
        
        st.markdown("---")
        
        # Chat controls
        st.subheader("💬 Chat Controls")
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_messages = []
            if st.session_state.chatbot:
                session_id = st.session_state.chatbot.create_session()
                st.session_state.chat_session_id = session_id
            st.success("Chat history cleared!")
            st.rerun()
        
        # Export chat
        if st.session_state.chat_messages:
            chat_data = {
                "timestamp": datetime.now().isoformat(),
                "messages": st.session_state.chat_messages
            }
            
            st.download_button(
                "💾 Export Chat History",
                data=json.dumps(chat_data, indent=2),
                file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        # AI Specialties
        if 'chatbot_config' in st.session_state and st.session_state.chatbot_config.get('specialties'):
            st.markdown("---")
            st.subheader("🧠 AI Specialties")
            for specialty in st.session_state.chatbot_config['specialties'][:4]:  # Show first 4
                st.markdown(f"**{specialty['name']}**")
                st.caption(specialty['description'])
        
        # Help section
        st.markdown("---")
        st.subheader("❓ Help")
        st.markdown("""
        **Commands:**
        - `/clear` or `/restart` - Clear chat history
        
        **Example questions:**
        - "What VLAN issues do you see?"
        - "How do I fix VLAN 30?"
        - "Show me the worst fragmented VLAN"
        - "Explain the connectivity problems"
        """)
    
    # Main chat interface
    if st.session_state.topology is None:
        st.info("👈 Please upload a network topology file in the sidebar to get started.")
        return
    
    if not st.session_state.openai_api_key:
        st.warning("👈 Please enter your OpenAI API key in the sidebar to enable the chatbot.")
        return
    
    # Initialize chatbot if needed
    if st.session_state.chatbot is None:
        with st.spinner("Initializing AI assistant..."):
            if not initialize_chatbot(st.session_state.openai_api_key):
                return
        st.success("🤖 AI Assistant ready!")
        st.rerun()
    
    # Display chat messages
    st.subheader("💬 Chat with AI Assistant")
    
    # Chat container with messages
    chat_container = st.container()
    
    with chat_container:
        if not st.session_state.chat_messages:
            # Welcome message
            with st.chat_message("assistant", avatar="🤖"):
                st.write(f"""
                Welcome! I'm your network troubleshooting assistant. I've analyzed your network and found **{len(st.session_state.analysis_report.problematic_vlans)} problematic VLANs with {st.session_state.analysis_report.total_islands} total islands**. 
                
                Ask me anything about your VLAN connectivity issues, and I'll provide detailed guidance!
                """)
        
        # Display chat history
        for message in st.session_state.chat_messages:
            display_chat_message(message, message['role'] == 'user')
    
    # Chat input using Streamlit's native chat input (auto-submits on Enter)
    user_input = st.chat_input(
        placeholder="Ask me about your network... (type /clear to reset chat)",
        key="chat_input"
    )
    
    # Process input when user presses Enter
    if user_input and user_input.strip():
        # Check for commands first
        command_response = process_chat_command(user_input.strip())
        
        if command_response:
            # Add command response
            st.session_state.chat_messages.append({
                'role': 'assistant',
                'content': command_response,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            st.rerun()
        else:
            # Add user message to history
            st.session_state.chat_messages.append({
                'role': 'user',
                'content': user_input.strip(),
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            
            # Get AI response
            with st.spinner("🤖 Thinking..."):
                try:
                    response = st.session_state.chatbot.chat(
                        st.session_state.chat_session_id, 
                        user_input.strip()
                    )
                    
                    # Add assistant response to history
                    st.session_state.chat_messages.append({
                        'role': 'assistant',
                        'content': response,
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    })
                    
                except Exception as e:
                    st.error(f"Error getting AI response: {e}")
                    st.session_state.chat_messages.append({
                        'role': 'assistant',
                        'content': f"Sorry, I encountered an error: {e}",
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    })
            
            st.rerun()
    
    # Quick action buttons
    if st.session_state.analysis_report and st.session_state.analysis_report.problematic_vlans:
        st.markdown("---")
        st.subheader("🚀 Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Show Network Overview"):
                overview = st.session_state.chatbot.get_network_overview()
                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': overview,
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
                st.rerun()
        
        with col2:
            worst_vlan = st.session_state.analysis_report.worst_fragmented_vlan
            if st.button(f"🔍 Analyze VLAN {worst_vlan.vlan_id}"):
                analysis = st.session_state.chatbot.analyze_vlan_interactive(worst_vlan.vlan_id)
                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': analysis,
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
                st.rerun()
        
        with col3:
            if st.button("💡 Get Recommendations"):
                recommendations = "\n".join([
                    "🔧 **Key Recommendations:**",
                    ""
                ] + [f"• {rec}" for rec in st.session_state.analysis_report.recommendations[:5]])
                
                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': recommendations,
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
                st.rerun()

if __name__ == "__main__":
    main()
