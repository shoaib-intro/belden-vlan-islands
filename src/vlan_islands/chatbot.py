"""
AI-powered chatbot for network troubleshooting and VLAN island remediation.

This module provides an intelligent conversational interface that helps network
administrators understand and fix VLAN connectivity issues.
"""

import os
import json
import yaml
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import openai
from dotenv import load_dotenv

from .models import NetworkTopology
from .analyzer import VLANIslandAnalyzer, NetworkAnalysisReport, VLANAnalysisResult
from .reports import ReportGenerator

# Load environment variables
load_dotenv()


@dataclass
class ChatMessage:
    """Represents a single chat message."""
    role: str  # 'user', 'assistant', or 'system'
    content: str
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ChatSession:
    """Represents a chat session with context."""
    session_id: str
    messages: List[ChatMessage]
    network_context: Optional[NetworkAnalysisReport]
    created_at: datetime
    last_activity: datetime
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the session."""
        message = ChatMessage(role=role, content=content, timestamp=datetime.now())
        self.messages.append(message)
        self.last_activity = datetime.now()
    
    def get_conversation_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation history for API calls."""
        recent_messages = self.messages[-limit:] if limit > 0 else self.messages
        return [{'role': msg.role, 'content': msg.content} for msg in recent_messages]


class NetworkChatbot:
    """
    AI-powered chatbot for network troubleshooting and VLAN island remediation.
    
    Provides conversational interface for:
    - Understanding VLAN island issues
    - Getting step-by-step remediation guidance
    - Analyzing network topology
    - Generating configuration recommendations
    """
    
    def __init__(self, topology: NetworkTopology, analysis_report: Optional[NetworkAnalysisReport] = None, config: Optional[Dict] = None):
        """
        Initialize the chatbot with network context.
        
        Args:
            topology: NetworkTopology object
            analysis_report: Optional pre-computed analysis report
            config: Optional configuration dictionary from YAML file
        """
        self.topology = topology
        self.analyzer = VLANIslandAnalyzer(topology)
        self.analysis_report = analysis_report or self.analyzer.analyze_all_vlans()
        self.config = config or {}
        
        # Initialize OpenAI client
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Chat sessions storage
        self.sessions: Dict[str, ChatSession] = {}
        
        # System prompt for the AI assistant
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with network context."""
        # Use YAML config system prompt if available
        if self.config.get('system_prompt'):
            base_prompt = self.config['system_prompt']
        else:
            base_prompt = "You are an expert network engineer and AI assistant specializing in VLAN troubleshooting and network topology analysis."
        
        # Get network summary
        summary = self.analysis_report.topology_summary
        problematic_vlans = len(self.analysis_report.problematic_vlans)
        
        # Build context about the current network
        network_context = f"""

CURRENT NETWORK ANALYSIS:
- Total Devices: {summary['total_devices']}
- Total VLANs: {summary['total_vlans']}
- VLANs with Issues: {problematic_vlans}
- Total Islands: {self.analysis_report.total_islands}

PROBLEMATIC VLANS IN THIS NETWORK:
"""
        
        for result in self.analysis_report.problematic_vlans[:5]:  # Top 5 issues
            network_context += f"- VLAN {result.vlan_id} ({result.vlan_name}): {result.island_count} islands, {result.fragmentation_ratio:.1%} fragmented\n"
        
        # Add specialties if available in config
        if self.config.get('specialties'):
            specialties_text = "\n\nYour specific areas of expertise include:\n"
            for specialty in self.config['specialties']:
                specialties_text += f"- **{specialty['name']}**: {specialty['description']}\n"
            network_context += specialties_text
        
        return base_prompt + network_context
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """
        Create a new chat session.
        
        Args:
            session_id: Optional session ID, will generate if not provided
            
        Returns:
            Session ID
        """
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = ChatSession(
            session_id=session_id,
            messages=[],
            network_context=self.analysis_report,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        # Add system message
        session.add_message("system", self.system_prompt)
        
        self.sessions[session_id] = session
        return session_id
    
    def chat(self, session_id: str, user_message: str) -> str:
        """
        Process a user message and return AI response.
        
        Args:
            session_id: Chat session ID
            user_message: User's message
            
        Returns:
            AI assistant's response
            
        Raises:
            ValueError: If session doesn't exist
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        
        # Add user message
        session.add_message("user", user_message)
        
        # Check if user is asking for specific analysis
        enhanced_context = self._enhance_message_with_context(user_message)
        if enhanced_context != user_message:
            session.add_message("system", f"Additional context: {enhanced_context}")
        
        # Get conversation history
        conversation = session.get_conversation_history(limit=20)
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=conversation,
                temperature=0.7,
                max_tokens=1000
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Add AI response to session
            session.add_message("assistant", ai_response)
            
            return ai_response
            
        except Exception as e:
            error_response = f"I apologize, but I encountered an error: {str(e)}. Please try rephrasing your question."
            session.add_message("assistant", error_response)
            return error_response
    
    def _enhance_message_with_context(self, user_message: str) -> str:
        """
        Enhance user message with relevant network context if applicable.
        
        Args:
            user_message: Original user message
            
        Returns:
            Enhanced message with context or original message
        """
        message_lower = user_message.lower()
        
        # Check if user is asking about specific VLAN
        if "vlan" in message_lower:
            # Try to extract VLAN ID
            words = user_message.split()
            for word in words:
                if word.isdigit():
                    vlan_id = int(word)
                    result = next((r for r in self.analysis_report.vlan_results if r.vlan_id == vlan_id), None)
                    if result:
                        context = f"VLAN {vlan_id} ({result.vlan_name}) has {result.island_count} islands with {result.isolated_devices} isolated devices."
                        return f"{user_message}\n\nContext: {context}"
        
        # Check if asking about connectivity or islands
        if any(term in message_lower for term in ["connect", "island", "isolated", "fix", "bridge"]):
            if self.analysis_report.problematic_vlans:
                worst = self.analysis_report.worst_fragmented_vlan
                context = f"Most problematic VLAN is {worst.vlan_id} ({worst.vlan_name}) with {worst.fragmentation_ratio:.1%} fragmentation."
                return f"{user_message}\n\nContext: {context}"
        
        return user_message
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary of a chat session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dictionary with session information
        """
        if session_id not in self.sessions:
            return {}
        
        session = self.sessions[session_id]
        
        return {
            "session_id": session_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "message_count": len([m for m in session.messages if m.role != "system"]),
            "has_network_context": session.network_context is not None
        }
    
    def export_session(self, session_id: str, file_path: Optional[str] = None) -> str:
        """
        Export chat session to JSON file.
        
        Args:
            session_id: Session ID to export
            file_path: Optional file path, will generate if not provided
            
        Returns:
            File path where session was saved
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        
        if not file_path:
            file_path = f"chat_session_{session_id}.json"
        
        export_data = {
            "session_id": session_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "messages": [msg.to_dict() for msg in session.messages if msg.role != "system"],
            "network_summary": {
                "total_devices": self.analysis_report.topology_summary["total_devices"],
                "total_vlans": self.analysis_report.topology_summary["total_vlans"],
                "problematic_vlans": len(self.analysis_report.problematic_vlans)
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return file_path
    
    def get_quick_help(self) -> str:
        """Get quick help message for users."""
        return """
🤖 Network Troubleshooting Assistant

I can help you with:
• Understanding VLAN island issues in your network
• Step-by-step remediation guidance
• Analyzing specific VLANs (e.g., "Tell me about VLAN 100")
• Configuration recommendations
• Network topology questions

Example questions:
• "How do I fix the connectivity issues in VLAN 50?"
• "What's causing the islands in my network?"
• "Show me how to configure trunk ports"
• "What's the best way to connect isolated devices?"

Just ask me anything about your network!
        """.strip()
    
    def analyze_vlan_interactive(self, vlan_id: int) -> str:
        """
        Provide interactive analysis of a specific VLAN.
        
        Args:
            vlan_id: VLAN ID to analyze
            
        Returns:
            Formatted analysis response
        """
        result = next((r for r in self.analysis_report.vlan_results if r.vlan_id == vlan_id), None)
        
        if not result:
            return f"[X] VLAN {vlan_id} not found in the network topology."
        
        if not result.has_islands:
            return f"[+] VLAN {vlan_id} ({result.vlan_name}) is healthy with no connectivity issues detected."
        
        # Build detailed analysis
        analysis = f"""
[!] VLAN {result.vlan_id} ({result.vlan_name}) Analysis

**Issue Summary:**
• {result.island_count} separate islands detected
• {result.isolated_devices} devices are isolated from the main network
• {result.fragmentation_ratio:.1%} of devices are disconnected

**Island Breakdown:**
"""
        
        for island in result.islands:
            status = "[*] MAIN ISLAND" if island.is_main_island else "[!] ISOLATED ISLAND"
            analysis += f"• Island {island.island_id} ({status}): {island.size} devices\n"
            
            if island.size <= 5:
                devices = ", ".join(sorted(island.devices))
                analysis += f"  Devices: {devices}\n"
            else:
                sample_devices = sorted(list(island.devices))[:3]
                analysis += f"  Devices: {', '.join(sample_devices)}... (+{island.size-3} more)\n"
        
        # Get connectivity suggestions
        suggestions = self.analyzer.get_island_connectivity_suggestions(vlan_id)
        
        if suggestions.get("connection_opportunities"):
            analysis += "\n**Recommended Actions:**\n"
            for opportunity in suggestions["connection_opportunities"][:3]:  # Top 3
                analysis += f"• Configure VLAN {vlan_id} on intermediate devices to bridge isolated island\n"
        
        analysis += f"\n💡 Ask me: \"How do I fix VLAN {vlan_id}?\" for detailed step-by-step guidance."
        
        return analysis.strip()
    
    def get_network_overview(self) -> str:
        """Get a comprehensive network overview."""
        report = self.analysis_report
        
        overview = f"""
🌐 **Network Overview**

**Topology Summary:**
• {report.topology_summary['total_devices']} devices across {report.topology_summary['total_vlans']} VLANs
• {len(report.healthy_vlans)} healthy VLANs, {len(report.problematic_vlans)} with issues
• {report.total_islands} total islands detected

**Health Status:**
"""
        
        if not report.problematic_vlans:
            overview += "[+] All VLANs are healthy - no connectivity issues detected!"
        else:
            overview += f"[!] {len(report.problematic_vlans)} VLANs need attention:\n"
            
            for result in sorted(report.problematic_vlans, key=lambda x: x.fragmentation_ratio, reverse=True)[:5]:
                overview += f"  • VLAN {result.vlan_id} ({result.vlan_name}): {result.island_count} islands\n"
        
        overview += f"\n[!] Ask me about specific VLANs or say \"help\" for guidance on fixing issues."
        
        return overview.strip()


def create_sample_conversation() -> List[Dict[str, str]]:
    """Create a sample conversation for demonstration purposes."""
    return [
        {
            "user": "What VLAN issues do you see in my network?",
            "assistant": "I've analyzed your network and found several VLANs with connectivity issues. VLAN 200 (Printers-A) has the most fragmentation with 3 separate islands, meaning some printer devices can't communicate with others. VLAN 300 (IoT-Bldg-A) also shows 2 islands. These issues typically indicate missing VLAN configurations on intermediate switches or physical connectivity problems. Would you like me to help you fix a specific VLAN?"
        },
        {
            "user": "How do I fix VLAN 200?",
            "assistant": "To fix VLAN 200 (Printers-A), here's a step-by-step approach:\n\n1. **Identify the islands**: Your VLAN has devices split across 3 islands\n2. **Check intermediate switches**: Verify that all switches between isolated devices have VLAN 200 configured\n3. **Configure trunk ports**: Ensure trunk ports between switches include VLAN 200\n4. **Verify physical connectivity**: Confirm all physical links are operational\n\nSpecific commands (Cisco example):\n```\nvlan 200\n name Printers-A\ninterface trunk_port\n switchport trunk allowed vlan add 200\n```\n\nWould you like me to provide more detailed configuration examples for your specific switch types?"
        }
    ]
