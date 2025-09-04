#!/usr/bin/env python3
"""
Streamlit Visualization Interface for VLAN Islands Analysis.

Interactive dashboards for network topology visualization and analytics.
"""

import streamlit as st
import sys
import os
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import networkx as nx
from typing import Dict, List, Optional, Tuple
import json

# Add src to path
sys.path.insert(0, str(Path("src").absolute()))

from vlan_islands.parser import load_network_topology, NetworkParseError
from vlan_islands.analyzer import VLANIslandAnalyzer
from vlan_islands.reports import ReportGenerator, create_island_summary_dataframe

# Page configuration
st.set_page_config(
    page_title="VLAN Islands Visualization",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if 'topology' not in st.session_state:
        st.session_state.topology = None
    if 'analysis_report' not in st.session_state:
        st.session_state.analysis_report = None
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = None

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
                st.session_state.analyzer = analyzer
            
            # Clean up temp file
            os.remove("temp_network.json")
            
            return True
    except NetworkParseError as e:
        st.error(f"Network parsing error: {e}")
    except Exception as e:
        st.error(f"Error loading network: {e}")
    
    return False

def create_network_topology_graph(analyzer: VLANIslandAnalyzer, highlight_vlan: Optional[int] = None):
    """Create interactive network topology visualization."""
    G = analyzer.physical_graph
    
    # Calculate layout
    pos = nx.spring_layout(G, k=3, iterations=50, seed=42)
    
    # Prepare node data
    node_x = []
    node_y = []
    node_text = []
    node_colors = []
    node_sizes = []
    
    # Color mapping for device roles
    role_colors = {
        'core': '#1B4332',
        'distribution': '#2D6A4F', 
        'access': '#52B788',
        'edge': '#74C69D',
        'wifi': '#FF6B6B',
        'storage': '#4ECDC4'
    }
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        node_data = G.nodes[node]
        role = node_data.get('role', 'unknown')
        device_type = node_data.get('device_type', 'unknown')
        location = node_data.get('location', 'unknown')
        
        # Node text for hover
        text = f"Device: {node}<br>Type: {device_type}<br>Role: {role}<br>Location: {location}"
        
        # Check if device is in highlighted VLAN
        if highlight_vlan:
            vlan = next((v for v in analyzer.topology.vlans if v.id == highlight_vlan), None)
            if vlan and node in vlan.devices:
                # Color by island if VLAN has issues
                vlan_result = analyzer.analyze_vlan(highlight_vlan)
                if vlan_result and vlan_result.has_islands:
                    island = vlan_result.get_island_by_device(node)
                    if island:
                        if island.is_main_island:
                            node_colors.append('#2ECC71')  # Green for main island
                            text += f"<br><b>Main Island {island.island_id}</b>"
                        else:
                            node_colors.append('#E74C3C')  # Red for isolated
                            text += f"<br><b>Isolated Island {island.island_id}</b>"
                        node_sizes.append(20)
                    else:
                        node_colors.append('#95A5A6')  # Gray for not in VLAN
                        node_sizes.append(10)
                else:
                    node_colors.append('#2ECC71')  # Green for healthy VLAN
                    node_sizes.append(15)
            else:
                node_colors.append('#95A5A6')  # Gray for not in VLAN
                node_sizes.append(10)
        else:
            # Color by role
            node_colors.append(role_colors.get(role, '#95A5A6'))
            node_sizes.append(15)
        
        node_text.append(text)
    
    # Prepare edge data
    edge_x = []
    edge_y = []
    
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    # Create traces
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#CCCCCC'),
        hoverinfo='none',
        mode='lines',
        showlegend=False
    )
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[node.split('-')[-1] for node in G.nodes()],  # Shortened labels
        textposition="middle center",
        textfont=dict(size=8, color="white"),
        hovertext=node_text,
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color='white')
        ),
        showlegend=False
    )
    
    # Create figure
    fig = go.Figure(data=[edge_trace, node_trace])
    
    title = "Network Topology"
    if highlight_vlan:
        vlan = next((v for v in analyzer.topology.vlans if v.id == highlight_vlan), None)
        if vlan:
            title += f" - VLAN {highlight_vlan} ({vlan.name})"
    
    fig.update_layout(
        title=title,
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        annotations=[
            dict(
                text="Hover over nodes for details",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002,
                font=dict(color="#888", size=12)
            )
        ],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        height=600
    )
    
    return fig

def create_vlan_summary_chart(report):
    """Create VLAN summary bar chart."""
    data = []
    
    for result in report.vlan_results:
        data.append({
            'VLAN ID': result.vlan_id,
            'VLAN Name': result.vlan_name,
            'Total Devices': result.total_devices,
            'Islands': result.island_count,
            'Fragmentation %': result.fragmentation_ratio * 100,
            'Status': 'Problematic' if result.has_islands else 'Healthy'
        })
    
    df = pd.DataFrame(data)
    
    # Create bar chart
    fig = px.bar(
        df,
        x='VLAN ID',
        y='Islands',
        color='Status',
        color_discrete_map={'Healthy': '#2ECC71', 'Problematic': '#E74C3C'},
        title='VLAN Islands Summary',
        hover_data=['VLAN Name', 'Total Devices', 'Fragmentation %']
    )
    
    fig.update_layout(
        xaxis_title="VLAN ID",
        yaxis_title="Number of Islands",
        height=400
    )
    
    return fig

def create_fragmentation_scatter(report):
    """Create fragmentation vs devices scatter plot."""
    data = []
    
    for result in report.vlan_results:
        data.append({
            'VLAN ID': result.vlan_id,
            'VLAN Name': result.vlan_name,
            'Total Devices': result.total_devices,
            'Fragmentation %': result.fragmentation_ratio * 100,
            'Islands': result.island_count,
            'Status': 'Problematic' if result.has_islands else 'Healthy'
        })
    
    df = pd.DataFrame(data)
    
    fig = px.scatter(
        df,
        x='Total Devices',
        y='Fragmentation %',
        color='Status',
        size='Islands',
        hover_data=['VLAN ID', 'VLAN Name'],
        color_discrete_map={'Healthy': '#2ECC71', 'Problematic': '#E74C3C'},
        title='VLAN Fragmentation Analysis'
    )
    
    fig.update_layout(
        xaxis_title="Total Devices in VLAN",
        yaxis_title="Fragmentation Percentage",
        height=400
    )
    
    return fig

def create_device_type_distribution(topology):
    """Create device type distribution pie chart."""
    device_counts = {}
    for device in topology.devices:
        device_type = device.type.value
        device_counts[device_type] = device_counts.get(device_type, 0) + 1
    
    fig = px.pie(
        values=list(device_counts.values()),
        names=list(device_counts.keys()),
        title='Device Type Distribution'
    )
    
    fig.update_layout(height=400)
    return fig

def create_location_heatmap(topology, report):
    """Create location-based problem heatmap."""
    location_problems = {}
    location_devices = {}
    
    # Count devices per location
    for device in topology.devices:
        location = device.location
        location_devices[location] = location_devices.get(location, 0) + 1
    
    # Count problems per location
    for result in report.problematic_vlans:
        for island in result.islands:
            if not island.is_main_island:  # Count isolated devices
                for device_id in island.devices:
                    device = next((d for d in topology.devices if d.id == device_id), None)
                    if device:
                        location = device.location
                        location_problems[location] = location_problems.get(location, 0) + 1
    
    # Create data for heatmap
    locations = list(location_devices.keys())
    problem_counts = [location_problems.get(loc, 0) for loc in locations]
    device_counts = [location_devices[loc] for loc in locations]
    
    # Calculate problem ratio
    problem_ratios = [p/d if d > 0 else 0 for p, d in zip(problem_counts, device_counts)]
    
    fig = px.bar(
        x=locations,
        y=problem_counts,
        color=problem_ratios,
        color_continuous_scale='Reds',
        title='Problem Devices by Location',
        labels={'x': 'Location', 'y': 'Isolated Devices', 'color': 'Problem Ratio'}
    )
    
    fig.update_layout(
        height=400,
        xaxis={'tickangle': 45}
    )
    
    return fig

def create_vlan_islands_weather(report):
    """Create VLAN islands weather visualization - showing network health like weather."""
    # Create weather-like categories based on fragmentation
    weather_data = []
    
    for result in report.vlan_results:
        if result.fragmentation_ratio == 0:
            weather = "Sunny"
            color = "#FFD700"  # Gold
            icon = "☀️"
        elif result.fragmentation_ratio < 0.2:
            weather = "Partly Cloudy" 
            color = "#87CEEB"  # Sky Blue
            icon = "⛅"
        elif result.fragmentation_ratio < 0.5:
            weather = "Cloudy"
            color = "#708090"  # Slate Gray
            icon = "☁️"
        elif result.fragmentation_ratio < 0.8:
            weather = "Stormy"
            color = "#FF4500"  # Orange Red
            icon = "⛈️"
        else:
            weather = "Hurricane"
            color = "#DC143C"  # Crimson
            icon = "🌪️"
        
        weather_data.append({
            'VLAN ID': result.vlan_id,
            'VLAN Name': result.vlan_name,
            'Weather': weather,
            'Fragmentation': result.fragmentation_ratio * 100,
            'Islands': result.island_count,
            'Devices': result.total_devices,
            'Color': color,
            'Icon': icon
        })
    
    df = pd.DataFrame(weather_data)
    
    # Create sunburst chart showing weather distribution
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Weather Distribution', 'Fragmentation Storm Map', 
                       'Island Count by Weather', 'VLAN Weather Timeline'),
        specs=[[{"type": "pie"}, {"type": "scatter"}],
               [{"type": "bar"}, {"type": "scatter"}]]
    )
    
    # Weather distribution pie chart
    weather_counts = df['Weather'].value_counts()
    fig.add_trace(
        go.Pie(
            labels=weather_counts.index,
            values=weather_counts.values,
            hole=0.4,
            marker_colors=['#FFD700', '#87CEEB', '#708090', '#FF4500', '#DC143C']
        ),
        row=1, col=1
    )
    
    # Fragmentation storm map (scatter)
    fig.add_trace(
        go.Scatter(
            x=df['Devices'],
            y=df['Fragmentation'],
            mode='markers+text',
            marker=dict(
                size=df['Islands'] * 5,
                color=df['Fragmentation'],
                colorscale='Reds',
                showscale=True,
                colorbar=dict(title="Fragmentation %")
            ),
            text=df['VLAN ID'],
            textposition="middle center",
            hovertemplate="<b>VLAN %{text}</b><br>" +
                         "Devices: %{x}<br>" +
                         "Fragmentation: %{y:.1f}%<br>" +
                         "Weather: " + df['Weather'] + "<br>" +
                         "<extra></extra>"
        ),
        row=1, col=2
    )
    
    # Island count by weather
    weather_island_avg = df.groupby('Weather')['Islands'].mean().reset_index()
    fig.add_trace(
        go.Bar(
            x=weather_island_avg['Weather'],
            y=weather_island_avg['Islands'],
            marker_color=['#FFD700', '#87CEEB', '#708090', '#FF4500', '#DC143C']
        ),
        row=2, col=1
    )
    
    # VLAN weather timeline (sorted by VLAN ID)
    df_sorted = df.sort_values('VLAN ID')
    fig.add_trace(
        go.Scatter(
            x=df_sorted['VLAN ID'],
            y=df_sorted['Fragmentation'],
            mode='markers+lines',
            marker=dict(
                size=12,
                color=df_sorted['Fragmentation'],
                colorscale='RdYlBu_r',
                line=dict(width=2, color='white')
            ),
            line=dict(width=2),
            hovertemplate="<b>VLAN %{x}</b><br>" +
                         "Weather: " + df_sorted['Weather'] + "<br>" +
                         "Fragmentation: %{y:.1f}%<br>" +
                         "<extra></extra>"
        ),
        row=2, col=2
    )
    
    fig.update_layout(
        title_text="VLAN Islands Weather Map - Network Health Forecast",
        height=800,
        showlegend=False
    )
    
    # Update subplot titles
    fig.update_xaxes(title_text="Total Devices", row=1, col=2)
    fig.update_yaxes(title_text="Fragmentation %", row=1, col=2)
    fig.update_xaxes(title_text="Weather Condition", row=2, col=1)
    fig.update_yaxes(title_text="Avg Islands", row=2, col=1)
    fig.update_xaxes(title_text="VLAN ID", row=2, col=2)
    fig.update_yaxes(title_text="Fragmentation %", row=2, col=2)
    
    return fig

def main():
    """Main Streamlit application."""
    initialize_session_state()
    
    # Header
    st.title("📊 VLAN Islands Visualization Dashboard")
    st.markdown("Interactive analytics and visualizations for network VLAN connectivity analysis")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("📁 Data Input")
        
        # Network topology upload
        uploaded_file = st.file_uploader(
            "Upload network topology JSON file",
            type=['json'],
            help="Upload your network topology file to start visualization"
        )
        
        if uploaded_file is not None and st.session_state.topology is None:
            if load_network_data(uploaded_file):
                st.success("✅ Network topology loaded successfully!")
                st.rerun()
        
        # Analysis summary
        if st.session_state.analysis_report:
            st.markdown("---")
            st.header("📊 Analysis Summary")
            report = st.session_state.analysis_report
            
            st.metric("Total VLANs", len(report.vlan_results))
            st.metric("Total Islands", report.total_islands)
            st.metric("Problematic VLANs", len(report.problematic_vlans))
            st.metric("Healthy VLANs", len(report.healthy_vlans))
            
            if report.worst_fragmented_vlan:
                worst = report.worst_fragmented_vlan
                st.error(f"🚨 Worst: VLAN {worst.vlan_id} ({worst.fragmentation_ratio:.1%})")
        
        # Visualization controls
        if st.session_state.analysis_report:
            st.markdown("---")
            st.header("🎛️ Visualization Controls")
            
            # VLAN selection for topology highlighting
            vlan_options = [("None", None)] + [
                (f"VLAN {v.id} ({v.name})", v.id) 
                for v in st.session_state.topology.vlans
            ]
            
            selected_vlan = st.selectbox(
                "Highlight VLAN in topology:",
                options=vlan_options,
                format_func=lambda x: x[0],
                help="Select a VLAN to highlight its islands in the network topology"
            )
            
            highlight_vlan_id = selected_vlan[1] if selected_vlan[1] is not None else None
        
        # Export options
        if st.session_state.analysis_report:
            st.markdown("---")
            st.header("💾 Export Data")
            
            # Generate reports
            report = st.session_state.analysis_report
            
            # JSON report
            json_report = ReportGenerator.generate_json_report(report)
            st.download_button(
                "📄 Download JSON Report",
                data=json_report,
                file_name="vlan_analysis_report.json",
                mime="application/json"
            )
            
            # CSV report
            csv_report = ReportGenerator.generate_csv_report(report)
            st.download_button(
                "📊 Download CSV Report",
                data=csv_report,
                file_name="vlan_analysis_report.csv",
                mime="text/csv"
            )
            
            # Text report
            text_report = ReportGenerator.generate_text_report(report)
            st.download_button(
                "📝 Download Text Report",
                data=text_report,
                file_name="vlan_analysis_report.txt",
                mime="text/plain"
            )
    
    # Main content
    if st.session_state.topology is None:
        st.info("👈 Please upload a network topology file in the sidebar to get started.")
        
        # Show sample data format
        st.subheader("📋 Expected Data Format")
        st.code('''
{
  "devices": [
    {
      "id": "core-sw-01",
      "type": "switch",
      "role": "core",
      "location": "datacenter"
    }
  ],
  "links": [
    {
      "source": "core-sw-01",
      "target": "core-sw-02",
      "type": "ethernet",
      "speed": "40G"
    }
  ],
  "vlans": [
    {
      "id": 100,
      "name": "Corporate",
      "description": "Corporate network",
      "devices": ["core-sw-01", "core-sw-02"]
    }
  ]
}
        ''', language='json')
        
        return
    
    # Main dashboard
    report = st.session_state.analysis_report
    analyzer = st.session_state.analyzer
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total VLANs",
            len(report.vlan_results),
            help="Total number of VLANs in the network"
        )
    
    with col2:
        st.metric(
            "Total Islands",
            report.total_islands,
            help="Total disconnected segments across all VLANs"
        )
    
    with col3:
        st.metric(
            "Problematic VLANs",
            len(report.problematic_vlans),
            delta=f"-{len(report.healthy_vlans)} healthy",
            delta_color="inverse",
            help="VLANs with connectivity issues"
        )
    
    with col4:
        if report.worst_fragmented_vlan:
            worst = report.worst_fragmented_vlan
            st.metric(
                "Worst Fragmentation",
                f"{worst.fragmentation_ratio:.1%}",
                delta=f"VLAN {worst.vlan_id}",
                delta_color="off",
                help="Highest fragmentation ratio in the network"
            )
    
    # Network topology visualization
    st.subheader("🌐 Network Topology")
    
    if 'highlight_vlan_id' in locals():
        topology_fig = create_network_topology_graph(analyzer, highlight_vlan_id)
    else:
        topology_fig = create_network_topology_graph(analyzer)
    
    st.plotly_chart(topology_fig, use_container_width=True)
    
    # VLAN analysis charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 VLAN Islands Summary")
        vlan_summary_fig = create_vlan_summary_chart(report)
        st.plotly_chart(vlan_summary_fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Fragmentation Analysis")
        fragmentation_fig = create_fragmentation_scatter(report)
        st.plotly_chart(fragmentation_fig, use_container_width=True)
    
    # VLAN Islands Weather Map
    st.subheader("🌤️ VLAN Islands Weather Map")
    weather_fig = create_vlan_islands_weather(report)
    st.plotly_chart(weather_fig, use_container_width=True)
    
    # Additional analytics
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏗️ Device Distribution")
        device_dist_fig = create_device_type_distribution(st.session_state.topology)
        st.plotly_chart(device_dist_fig, use_container_width=True)
    
    with col2:
        st.subheader("📍 Problems by Location")
        location_fig = create_location_heatmap(st.session_state.topology, report)
        st.plotly_chart(location_fig, use_container_width=True)
    
    # Detailed tables
    st.subheader("📋 Detailed Analysis")
    
    tab1, tab2, tab3 = st.tabs(["🚨 Problematic VLANs", "✅ Healthy VLANs", "🏝️ Island Details"])
    
    with tab1:
        if report.problematic_vlans:
            problematic_data = []
            for result in sorted(report.problematic_vlans, key=lambda x: x.fragmentation_ratio, reverse=True):
                problematic_data.append({
                    'VLAN ID': result.vlan_id,
                    'Name': result.vlan_name,
                    'Devices': result.total_devices,
                    'Islands': result.island_count,
                    'Main Island': result.main_island_size,
                    'Isolated': result.isolated_devices,
                    'Fragmentation': f"{result.fragmentation_ratio:.1%}"
                })
            
            st.dataframe(problematic_data, use_container_width=True)
        else:
            st.success("🎉 No problematic VLANs found!")
    
    with tab2:
        if report.healthy_vlans:
            healthy_data = []
            for result in sorted(report.healthy_vlans, key=lambda x: x.vlan_id):
                healthy_data.append({
                    'VLAN ID': result.vlan_id,
                    'Name': result.vlan_name,
                    'Devices': result.total_devices,
                    'Status': '✅ Connected' if result.total_devices > 0 else '⚪ Empty'
                })
            
            st.dataframe(healthy_data, use_container_width=True)
        else:
            st.warning("No healthy VLANs found.")
    
    with tab3:
        if report.problematic_vlans:
            island_data = []
            for result in report.problematic_vlans:
                for island in result.islands:
                    island_data.append({
                        'VLAN ID': result.vlan_id,
                        'VLAN Name': result.vlan_name,
                        'Island ID': island.island_id,
                        'Type': 'Main' if island.is_main_island else 'Isolated',
                        'Size': island.size,
                        'Devices': ', '.join(sorted(list(island.devices))[:3]) + 
                                  (f' ... (+{island.size-3} more)' if island.size > 3 else '')
                    })
            
            island_df = pd.DataFrame(island_data)
            st.dataframe(island_df, use_container_width=True)
        else:
            st.info("No islands to display.")
    
    # Recommendations
    st.subheader("💡 Recommendations")
    
    if report.recommendations:
        for i, rec in enumerate(report.recommendations, 1):
            if rec.startswith('🚨') or rec.startswith('❌'):
                st.error(f"{i}. {rec}")
            elif rec.startswith('✅') or rec.startswith('💡'):
                st.info(f"{i}. {rec}")
            else:
                st.write(f"{i}. {rec}")
    else:
        st.success("🎉 No specific recommendations - your network looks healthy!")

if __name__ == "__main__":
    main()
