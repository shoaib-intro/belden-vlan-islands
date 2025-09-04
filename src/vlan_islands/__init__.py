"""
VLAN Islands Detection and Troubleshooting Tool

An AI-powered solution for analyzing network topologies, identifying VLAN islands,
and providing interactive guidance for network administrators.
"""

__version__ = "1.0.0"
__author__ = "Network Analysis Tool"
__email__ = "admin@example.com"

from .models import Device, Link, VLAN, NetworkTopology
from .analyzer import VLANIslandAnalyzer
from .chatbot import NetworkChatbot

__all__ = [
    "Device",
    "Link", 
    "VLAN",
    "NetworkTopology",
    "VLANIslandAnalyzer",
    "NetworkChatbot",
]
