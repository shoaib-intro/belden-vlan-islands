"""
Network topology visualization module for VLAN islands.

This module provides functionality to create visual representations of network
topologies with highlighted VLAN islands and connectivity issues.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import json

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd

from .models import NetworkTopology, Device, DeviceRole, DeviceType
from .analyzer import NetworkAnalysisReport, VLANAnalysisResult, VLANIsland


class NetworkVisualizer:
    """
    Creates visualizations of network topologies with VLAN island highlighting.
    """
    
    def __init__(self, topology: NetworkTopology, analysis_report: Optional[NetworkAnalysisReport] = None):
        """
        Initialize the visualizer.
        
        Args:
            topology: NetworkTopology object
            analysis_report: Optional analysis report for highlighting issues
        """
        self.topology = topology
        self.analysis_report = analysis_report
        self.device_colors = self._get_device_colors()
        self.role_positions = self._calculate_role_positions()
    
    def _get_device_colors(self) -> Dict[str, str]:
        """Get color mapping for different device types and roles."""
        return {
            # Device types
            DeviceType.SWITCH.value: "#2E86AB",      # Blue
            DeviceType.ROUTER.value: "#A23B72",      # Purple
            DeviceType.CONTROLLER.value: "#F18F01",  # Orange
            DeviceType.ACCESS_POINT.value: "#C73E1D", # Red
            
            # Device roles
            DeviceRole.CORE.value: "#1B4332",        # Dark green
            DeviceRole.DISTRIBUTION.value: "#2D6A4F", # Medium green
            DeviceRole.ACCESS.value: "#52B788",      # Light green
            DeviceRole.EDGE.value: "#74C69D",        # Very light green
            DeviceRole.WIFI.value: "#FF6B6B",        # Light red
            DeviceRole.STORAGE.value: "#4ECDC4",     # Teal
            
            # Island status
            "main_island": "#2ECC71",     # Green
            "isolated_island": "#E74C3C", # Red
            "healthy_vlan": "#95A5A6",    # Gray
        }
    
    def _calculate_role_positions(self) -> Dict[str, Tuple[float, float]]:
        """Calculate hierarchical positions for devices based on their roles."""
        positions = {}
        
        # Define hierarchy levels (Y coordinates)
        role_levels = {
            DeviceRole.CORE.value: 4.0,
            DeviceRole.DISTRIBUTION.value: 3.0,
            DeviceRole.ACCESS.value: 2.0,
            DeviceRole.EDGE.value: 1.0,
            DeviceRole.WIFI.value: 1.5,
            DeviceRole.STORAGE.value: 3.5,
        }
        
        # Group devices by role
        role_groups = {}
        for device in self.topology.devices:
            role = device.role.value
            if role not in role_groups:
                role_groups[role] = []
            role_groups[role].append(device)
        
        # Calculate positions for each role group
        for role, devices in role_groups.items():
            y_level = role_levels.get(role, 2.0)
            device_count = len(devices)
            
            # Distribute devices horizontally
            if device_count == 1:
                x_positions = [0.0]
            else:
                x_positions = [
                    -2.0 + (4.0 * i / (device_count - 1))
                    for i in range(device_count)
                ]
            
            # Assign positions
            for i, device in enumerate(devices):
                positions[device.id] = (x_positions[i], y_level)
        
        return positions
    
    def create_topology_visualization(
        self,
        output_path: Optional[Union[str, Path]] = None,
        format: str = "html",
        highlight_islands: bool = True
    ) -> str:
        """
        Create a complete network topology visualization.
        
        Args:
            output_path: Optional output file path
            format: Output format ('html', 'png', 'svg')
            highlight_islands: Whether to highlight VLAN islands
            
        Returns:
            Path to the generated visualization file
        """
        if format == "html":
            return self._create_interactive_topology(output_path, highlight_islands)
        else:
            return self._create_static_topology(output_path, format, highlight_islands)
    
    def _create_interactive_topology(
        self,
        output_path: Optional[Union[str, Path]] = None,
        highlight_islands: bool = True
    ) -> str:
        """Create an interactive HTML visualization using Plotly."""
        # Build NetworkX graph
        G = nx.Graph()
        
        # Add nodes with attributes
        for device in self.topology.devices:
            G.add_node(
                device.id,
                device_type=device.type.value,
                role=device.role.value,
                location=device.location,
                color=self.device_colors.get(device.type.value, "#95A5A6")
            )
        
        # Add edges
        for link in self.topology.links:
            G.add_edge(
                link.source,
                link.target,
                link_type=link.type.value,
                speed=link.speed
            )
        
        # Calculate layout
        pos = self._get_hierarchical_layout(G)
        
        # Prepare node traces
        node_traces = self._create_node_traces(G, pos, highlight_islands)
        
        # Prepare edge traces
        edge_traces = self._create_edge_traces(G, pos)
        
        # Create figure
        fig = go.Figure(data=edge_traces + node_traces)
        
        fig.update_layout(
            title={
                'text': f"Network Topology - {len(self.topology.devices)} Devices, {len(self.topology.vlans)} VLANs",
                'x': 0.5,
                'font': {'size': 20}
            },
            showlegend=True,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    text="Hover over nodes for details. Legend shows device roles.",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.005, y=-0.002,
                    font=dict(color="#888", size=12)
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white'
        )
        
        # Add analysis summary if available
        if self.analysis_report and highlight_islands:
            self._add_analysis_annotations(fig)
        
        # Save file
        if not output_path:
            output_path = "network_topology.html"
        
        fig.write_html(str(output_path))
        return str(output_path)
    
    def _create_static_topology(
        self,
        output_path: Optional[Union[str, Path]] = None,
        format: str = "png",
        highlight_islands: bool = True
    ) -> str:
        """Create a static visualization using matplotlib."""
        # Build NetworkX graph
        G = nx.Graph()
        
        for device in self.topology.devices:
            G.add_node(device.id, **device.dict())
        
        for link in self.topology.links:
            G.add_edge(link.source, link.target, **link.dict())
        
        # Create figure
        plt.figure(figsize=(16, 12))
        
        # Calculate layout
        pos = self._get_hierarchical_layout(G)
        
        # Draw edges
        nx.draw_networkx_edges(
            G, pos,
            edge_color='#CCCCCC',
            width=1.5,
            alpha=0.7
        )
        
        # Draw nodes by role
        role_colors = {}
        for role in DeviceRole:
            nodes_of_role = [
                node for node in G.nodes()
                if G.nodes[node].get('role') == role.value
            ]
            if nodes_of_role:
                color = self.device_colors.get(role.value, "#95A5A6")
                nx.draw_networkx_nodes(
                    G, pos,
                    nodelist=nodes_of_role,
                    node_color=color,
                    node_size=800,
                    alpha=0.8,
                    label=role.value.title()
                )
        
        # Add labels
        labels = {node: node.split('-')[-1] for node in G.nodes()}  # Shortened labels
        nx.draw_networkx_labels(G, pos, labels, font_size=8)
        
        plt.title(f"Network Topology - {len(self.topology.devices)} Devices", fontsize=16)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.axis('off')
        plt.tight_layout()
        
        # Save file
        if not output_path:
            output_path = f"network_topology.{format}"
        
        plt.savefig(str(output_path), format=format, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def create_vlan_visualization(
        self,
        vlan_id: int,
        output_path: Optional[Union[str, Path]] = None,
        format: str = "html"
    ) -> str:
        """
        Create a visualization focused on a specific VLAN and its islands.
        
        Args:
            vlan_id: VLAN ID to visualize
            output_path: Optional output file path
            format: Output format ('html', 'png', 'svg')
            
        Returns:
            Path to the generated visualization file
        """
        # Find the VLAN
        vlan = next((v for v in self.topology.vlans if v.id == vlan_id), None)
        if not vlan:
            raise ValueError(f"VLAN {vlan_id} not found")
        
        # Get analysis result if available
        vlan_result = None
        if self.analysis_report:
            vlan_result = next(
                (r for r in self.analysis_report.vlan_results if r.vlan_id == vlan_id),
                None
            )
        
        if format == "html":
            return self._create_interactive_vlan_view(vlan, vlan_result, output_path)
        else:
            return self._create_static_vlan_view(vlan, vlan_result, output_path, format)
    
    def _create_interactive_vlan_view(
        self,
        vlan,
        vlan_result: Optional[VLANAnalysisResult],
        output_path: Optional[Union[str, Path]] = None
    ) -> str:
        """Create interactive VLAN-specific visualization."""
        # Build subgraph with only VLAN devices
        G = nx.Graph()
        vlan_devices = set(vlan.devices)
        
        # Add VLAN devices
        for device in self.topology.devices:
            if device.id in vlan_devices:
                G.add_node(device.id, **device.dict())
        
        # Add links between VLAN devices
        for link in self.topology.links:
            if link.source in vlan_devices and link.target in vlan_devices:
                G.add_edge(link.source, link.target, **link.dict())
        
        # Calculate layout
        pos = nx.spring_layout(G, k=2, iterations=50)
        
        # Create traces
        edge_traces = self._create_edge_traces(G, pos)
        
        # Color nodes by island if analysis is available
        if vlan_result and vlan_result.has_islands:
            node_traces = self._create_island_node_traces(G, pos, vlan_result)
            title_suffix = f" - {vlan_result.island_count} Islands Detected"
        else:
            node_traces = self._create_node_traces(G, pos, False)
            title_suffix = " - Healthy"
        
        # Create figure
        fig = go.Figure(data=edge_traces + node_traces)
        
        fig.update_layout(
            title={
                'text': f"VLAN {vlan.id} ({vlan.name}){title_suffix}",
                'x': 0.5,
                'font': {'size': 18}
            },
            showlegend=True,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white'
        )
        
        # Save file
        if not output_path:
            output_path = f"vlan_{vlan.id}_topology.html"
        
        fig.write_html(str(output_path))
        return str(output_path)
    
    def _create_static_vlan_view(
        self,
        vlan,
        vlan_result: Optional[VLANAnalysisResult],
        output_path: Optional[Union[str, Path]] = None,
        format: str = "png"
    ) -> str:
        """Create static VLAN-specific visualization."""
        # Similar to interactive but using matplotlib
        # Implementation would follow the same pattern as _create_static_topology
        # but focused on VLAN devices only
        
        if not output_path:
            output_path = f"vlan_{vlan.id}_topology.{format}"
        
        # Placeholder implementation
        plt.figure(figsize=(12, 8))
        plt.text(0.5, 0.5, f"VLAN {vlan.id} Visualization\n(Static view)", 
                ha='center', va='center', fontsize=16)
        plt.axis('off')
        plt.savefig(str(output_path), format=format, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def _get_hierarchical_layout(self, G: nx.Graph) -> Dict[str, Tuple[float, float]]:
        """Calculate hierarchical layout based on device roles."""
        pos = {}
        
        # Use pre-calculated role positions if available
        for node in G.nodes():
            if node in self.role_positions:
                pos[node] = self.role_positions[node]
            else:
                # Fallback to spring layout for missing nodes
                temp_pos = nx.spring_layout(G.subgraph([node]), k=1)
                pos[node] = temp_pos[node]
        
        return pos
    
    def _create_node_traces(
        self,
        G: nx.Graph,
        pos: Dict[str, Tuple[float, float]],
        highlight_islands: bool
    ) -> List[go.Scatter]:
        """Create Plotly traces for network nodes."""
        traces = []
        
        # Group nodes by role for better visualization
        role_groups = {}
        for node in G.nodes():
            role = G.nodes[node].get('role', 'unknown')
            if role not in role_groups:
                role_groups[role] = []
            role_groups[role].append(node)
        
        # Create trace for each role
        for role, nodes in role_groups.items():
            x_coords = [pos[node][0] for node in nodes]
            y_coords = [pos[node][1] for node in nodes]
            
            hover_text = []
            for node in nodes:
                node_data = G.nodes[node]
                text = f"Device: {node}<br>"
                text += f"Type: {node_data.get('type', 'Unknown')}<br>"
                text += f"Role: {node_data.get('role', 'Unknown')}<br>"
                text += f"Location: {node_data.get('location', 'Unknown')}"
                hover_text.append(text)
            
            color = self.device_colors.get(role, "#95A5A6")
            
            trace = go.Scatter(
                x=x_coords,
                y=y_coords,
                mode='markers',
                marker=dict(
                    size=15,
                    color=color,
                    line=dict(width=2, color='white')
                ),
                text=nodes,
                hovertext=hover_text,
                hoverinfo='text',
                name=role.title(),
                showlegend=True
            )
            traces.append(trace)
        
        return traces
    
    def _create_edge_traces(
        self,
        G: nx.Graph,
        pos: Dict[str, Tuple[float, float]]
    ) -> List[go.Scatter]:
        """Create Plotly traces for network edges."""
        edge_x = []
        edge_y = []
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            line=dict(width=2, color='#CCCCCC'),
            hoverinfo='none',
            mode='lines',
            showlegend=False
        )
        
        return [edge_trace]
    
    def _create_island_node_traces(
        self,
        G: nx.Graph,
        pos: Dict[str, Tuple[float, float]],
        vlan_result: VLANAnalysisResult
    ) -> List[go.Scatter]:
        """Create node traces colored by island membership."""
        traces = []
        
        # Create trace for each island
        for island in vlan_result.islands:
            island_nodes = [node for node in island.devices if node in G.nodes()]
            
            if not island_nodes:
                continue
            
            x_coords = [pos[node][0] for node in island_nodes]
            y_coords = [pos[node][1] for node in island_nodes]
            
            hover_text = []
            for node in island_nodes:
                node_data = G.nodes[node]
                text = f"Device: {node}<br>"
                text += f"Island: {island.island_id}<br>"
                text += f"Status: {'Main Island' if island.is_main_island else 'Isolated'}<br>"
                text += f"Type: {node_data.get('type', 'Unknown')}<br>"
                text += f"Location: {node_data.get('location', 'Unknown')}"
                hover_text.append(text)
            
            color = self.device_colors["main_island"] if island.is_main_island else self.device_colors["isolated_island"]
            name = f"Island {island.island_id}" + (" (Main)" if island.is_main_island else " (Isolated)")
            
            trace = go.Scatter(
                x=x_coords,
                y=y_coords,
                mode='markers',
                marker=dict(
                    size=20 if island.is_main_island else 15,
                    color=color,
                    line=dict(width=2, color='white')
                ),
                text=island_nodes,
                hovertext=hover_text,
                hoverinfo='text',
                name=name,
                showlegend=True
            )
            traces.append(trace)
        
        return traces
    
    def _add_analysis_annotations(self, fig: go.Figure) -> None:
        """Add analysis summary annotations to the figure."""
        if not self.analysis_report:
            return
        
        summary_text = f"Analysis Summary:<br>"
        summary_text += f"• Problematic VLANs: {len(self.analysis_report.problematic_vlans)}<br>"
        summary_text += f"• Total Islands: {self.analysis_report.total_islands}<br>"
        
        if self.analysis_report.worst_fragmented_vlan:
            worst = self.analysis_report.worst_fragmented_vlan
            summary_text += f"• Worst VLAN: {worst.vlan_id} ({worst.fragmentation_ratio:.1%} fragmented)"
        
        fig.add_annotation(
            text=summary_text,
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            font=dict(size=12, color="#333"),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#CCC",
            borderwidth=1
        )
    
    def create_vlan_matrix_heatmap(
        self,
        output_path: Optional[Union[str, Path]] = None
    ) -> str:
        """
        Create a heatmap showing device participation in VLANs.
        
        Args:
            output_path: Optional output file path
            
        Returns:
            Path to the generated heatmap file
        """
        # Create device-VLAN matrix
        devices = [device.id for device in self.topology.devices]
        vlans = [vlan.id for vlan in self.topology.vlans]
        
        matrix = []
        for device_id in devices:
            row = []
            for vlan in self.topology.vlans:
                row.append(1 if device_id in vlan.devices else 0)
            matrix.append(row)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=[f"VLAN {vlan_id}" for vlan_id in vlans],
            y=devices,
            colorscale='RdYlBu_r',
            showscale=True
        ))
        
        fig.update_layout(
            title="Device-VLAN Participation Matrix",
            xaxis_title="VLANs",
            yaxis_title="Devices",
            height=max(600, len(devices) * 20),
            width=max(800, len(vlans) * 50)
        )
        
        if not output_path:
            output_path = "vlan_matrix_heatmap.html"
        
        fig.write_html(str(output_path))
        return str(output_path)
