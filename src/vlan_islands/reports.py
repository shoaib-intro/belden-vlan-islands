"""
Report generation module for VLAN island analysis results.

This module provides functionality to export analysis results in various formats
including JSON, CSV, and formatted text reports.
"""

import json
import csv
from pathlib import Path
from typing import Dict, Any, List, Union, Optional
from datetime import datetime
import pandas as pd
from tabulate import tabulate

from .analyzer import NetworkAnalysisReport, VLANAnalysisResult, VLANIsland


class ReportGenerator:
    """
    Generates various types of reports from VLAN island analysis results.
    """
    
    @staticmethod
    def generate_json_report(report: NetworkAnalysisReport, file_path: Optional[Union[str, Path]] = None) -> str:
        """
        Generate a JSON report from analysis results.
        
        Args:
            report: NetworkAnalysisReport to convert
            file_path: Optional path to save the report
            
        Returns:
            JSON string representation of the report
        """
        # Convert report to serializable dictionary
        report_data = {
            "analysis_metadata": {
                "timestamp": report.timestamp.isoformat(),
                "total_vlans_analyzed": len(report.vlan_results),
                "problematic_vlans_count": len(report.problematic_vlans),
                "total_islands": report.total_islands
            },
            "topology_summary": report.topology_summary,
            "vlan_analysis": [
                {
                    "vlan_id": result.vlan_id,
                    "vlan_name": result.vlan_name,
                    "total_devices": result.total_devices,
                    "island_count": result.island_count,
                    "has_connectivity_issues": result.has_islands,
                    "main_island_size": result.main_island_size,
                    "isolated_devices": result.isolated_devices,
                    "fragmentation_ratio": round(result.fragmentation_ratio, 4),
                    "islands": [
                        {
                            "island_id": island.island_id,
                            "devices": list(island.devices),
                            "device_count": island.size,
                            "is_main_island": island.is_main_island
                        }
                        for island in result.islands
                    ]
                }
                for result in report.vlan_results
            ],
            "recommendations": report.recommendations,
            "summary": {
                "healthy_vlans": len(report.healthy_vlans),
                "problematic_vlans": len(report.problematic_vlans),
                "worst_fragmented_vlan": {
                    "vlan_id": report.worst_fragmented_vlan.vlan_id,
                    "vlan_name": report.worst_fragmented_vlan.vlan_name,
                    "fragmentation_ratio": round(report.worst_fragmented_vlan.fragmentation_ratio, 4)
                } if report.worst_fragmented_vlan else None
            }
        }
        
        json_str = json.dumps(report_data, indent=2, ensure_ascii=False)
        
        if file_path:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json_str)
        
        return json_str
    
    @staticmethod
    def generate_csv_report(report: NetworkAnalysisReport, file_path: Optional[Union[str, Path]] = None) -> str:
        """
        Generate a CSV report from analysis results.
        
        Args:
            report: NetworkAnalysisReport to convert
            file_path: Optional path to save the report
            
        Returns:
            CSV string representation
        """
        # Prepare data for CSV
        csv_data = []
        
        for result in report.vlan_results:
            base_row = {
                'VLAN_ID': result.vlan_id,
                'VLAN_Name': result.vlan_name,
                'Total_Devices': result.total_devices,
                'Island_Count': result.island_count,
                'Has_Issues': 'Yes' if result.has_islands else 'No',
                'Main_Island_Size': result.main_island_size,
                'Isolated_Devices': result.isolated_devices,
                'Fragmentation_Ratio': round(result.fragmentation_ratio, 4)
            }
            
            if result.islands:
                for island in result.islands:
                    row = base_row.copy()
                    row.update({
                        'Island_ID': island.island_id,
                        'Island_Size': island.size,
                        'Is_Main_Island': 'Yes' if island.is_main_island else 'No',
                        'Island_Devices': ';'.join(sorted(island.devices))
                    })
                    csv_data.append(row)
            else:
                # VLAN with no devices
                row = base_row.copy()
                row.update({
                    'Island_ID': 'N/A',
                    'Island_Size': 0,
                    'Is_Main_Island': 'N/A',
                    'Island_Devices': ''
                })
                csv_data.append(row)
        
        if not csv_data:
            return ""
        
        # Convert to CSV string
        fieldnames = csv_data[0].keys()
        csv_content = []
        
        # Add header
        csv_content.append(','.join(fieldnames))
        
        # Add data rows
        for row in csv_data:
            csv_row = []
            for field in fieldnames:
                value = str(row.get(field, ''))
                # Escape quotes and commas
                if ',' in value or '"' in value:
                    value = f'"{value.replace('"', '""')}"'
                csv_row.append(value)
            csv_content.append(','.join(csv_row))
        
        csv_str = '\n'.join(csv_content)
        
        if file_path:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(csv_str)
        
        return csv_str
    
    @staticmethod
    def generate_text_report(report: NetworkAnalysisReport, file_path: Optional[Union[str, Path]] = None) -> str:
        """
        Generate a formatted text report from analysis results.
        
        Args:
            report: NetworkAnalysisReport to convert
            file_path: Optional path to save the report
            
        Returns:
            Formatted text report string
        """
        lines = []
        
        # Header
        lines.extend([
            "=" * 80,
            "VLAN ISLANDS ANALYSIS REPORT",
            "=" * 80,
            f"Analysis Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ])
        
        # Executive Summary
        lines.extend([
            "EXECUTIVE SUMMARY",
            "-" * 40,
            f"Total VLANs Analyzed: {len(report.vlan_results)}",
            f"VLANs with Issues: {len(report.problematic_vlans)}",
            f"Healthy VLANs: {len(report.healthy_vlans)}",
            f"Total Islands Detected: {report.total_islands}",
            "",
        ])
        
        if report.worst_fragmented_vlan:
            lines.extend([
                f"Most Fragmented VLAN: {report.worst_fragmented_vlan.vlan_id} "
                f"({report.worst_fragmented_vlan.vlan_name}) - "
                f"{report.worst_fragmented_vlan.fragmentation_ratio:.1%} fragmented",
                "",
            ])
        
        # Topology Summary
        lines.extend([
            "NETWORK TOPOLOGY SUMMARY",
            "-" * 40,
            f"Total Devices: {report.topology_summary['total_devices']}",
            f"Total Links: {report.topology_summary['total_links']}",
            f"Total VLANs: {report.topology_summary['total_vlans']}",
            "",
        ])
        
        # Device breakdown
        if 'device_types' in report.topology_summary:
            lines.append("Device Types:")
            for device_type, count in report.topology_summary['device_types'].items():
                if count > 0:
                    lines.append(f"  • {device_type.title()}: {count}")
            lines.append("")
        
        # Problematic VLANs Details
        if report.problematic_vlans:
            lines.extend([
                "PROBLEMATIC VLANS (DETAILED ANALYSIS)",
                "-" * 40,
            ])
            
            for result in sorted(report.problematic_vlans, key=lambda x: x.fragmentation_ratio, reverse=True):
                lines.extend([
                    f"VLAN {result.vlan_id}: {result.vlan_name}",
                    f"  Total Devices: {result.total_devices}",
                    f"  Islands Detected: {result.island_count}",
                    f"  Main Island Size: {result.main_island_size}",
                    f"  Isolated Devices: {result.isolated_devices}",
                    f"  Fragmentation Ratio: {result.fragmentation_ratio:.1%}",
                    "",
                    "  Island Details:",
                ])
                
                for island in result.islands:
                    status = "[*] MAIN" if island.is_main_island else "[!] ISOLATED"
                    lines.append(f"    Island {island.island_id} ({status}): {island.size} devices")
                    
                    # Show first few devices, truncate if too many
                    devices_list = sorted(list(island.devices))
                    if len(devices_list) <= 5:
                        lines.append(f"      Devices: {', '.join(devices_list)}")
                    else:
                        shown = devices_list[:3]
                        lines.append(f"      Devices: {', '.join(shown)} ... (+{len(devices_list)-3} more)")
                
                lines.append("")
        
        # Healthy VLANs Summary
        if report.healthy_vlans:
            lines.extend([
                "HEALTHY VLANS (NO ISSUES DETECTED)",
                "-" * 40,
            ])
            
            # Create table for healthy VLANs
            healthy_data = []
            for result in sorted(report.healthy_vlans, key=lambda x: x.vlan_id):
                healthy_data.append([
                    result.vlan_id,
                    result.vlan_name,
                    result.total_devices,
                    "[+] Connected" if result.total_devices > 0 else "Empty"
                ])
            
            if healthy_data:
                table = tabulate(
                    healthy_data,
                    headers=["VLAN ID", "Name", "Devices", "Status"],
                    tablefmt="grid"
                )
                lines.extend(table.split('\n'))
                lines.append("")
        
        # Recommendations
        lines.extend([
            "RECOMMENDATIONS",
            "-" * 40,
        ])
        lines.extend(report.recommendations)
        lines.extend(["", "=" * 80])
        
        text_report = '\n'.join(lines)
        
        if file_path:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text_report)
        
        return text_report
    
    @staticmethod
    def generate_summary_table(report: NetworkAnalysisReport) -> str:
        """
        Generate a concise summary table of all VLANs.
        
        Args:
            report: NetworkAnalysisReport to summarize
            
        Returns:
            Formatted table string
        """
        table_data = []
        
        for result in sorted(report.vlan_results, key=lambda x: x.vlan_id):
            status = "[!] ISSUES" if result.has_islands else "[+] HEALTHY"
            table_data.append([
                result.vlan_id,
                result.vlan_name,
                result.total_devices,
                result.island_count,
                f"{result.fragmentation_ratio:.1%}",
                status
            ])
        
        if not table_data:
            return "No VLANs analyzed."
        
        return tabulate(
            table_data,
            headers=["VLAN ID", "Name", "Devices", "Islands", "Fragmentation", "Status"],
            tablefmt="grid"
        )
    
    @staticmethod
    def export_all_formats(report: NetworkAnalysisReport, output_dir: Union[str, Path], base_filename: str = "vlan_analysis") -> Dict[str, str]:
        """
        Export the report in all supported formats.
        
        Args:
            report: NetworkAnalysisReport to export
            output_dir: Directory to save reports
            base_filename: Base filename (without extension)
            
        Returns:
            Dictionary mapping format to file path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        exported_files = {}
        
        # JSON report
        json_file = output_path / f"{base_filename}.json"
        ReportGenerator.generate_json_report(report, json_file)
        exported_files['json'] = str(json_file)
        
        # CSV report
        csv_file = output_path / f"{base_filename}.csv"
        ReportGenerator.generate_csv_report(report, csv_file)
        exported_files['csv'] = str(csv_file)
        
        # Text report
        txt_file = output_path / f"{base_filename}.txt"
        ReportGenerator.generate_text_report(report, txt_file)
        exported_files['txt'] = str(txt_file)
        
        return exported_files


def create_island_summary_dataframe(report: NetworkAnalysisReport) -> pd.DataFrame:
    """
    Create a pandas DataFrame summarizing all islands across VLANs.
    
    Args:
        report: NetworkAnalysisReport to convert
        
    Returns:
        DataFrame with island information
    """
    data = []
    
    for result in report.vlan_results:
        for island in result.islands:
            data.append({
                'VLAN_ID': result.vlan_id,
                'VLAN_Name': result.vlan_name,
                'Island_ID': island.island_id,
                'Island_Size': island.size,
                'Is_Main_Island': island.is_main_island,
                'Devices': list(island.devices),
                'Fragmentation_Ratio': result.fragmentation_ratio
            })
    
    return pd.DataFrame(data)


def create_device_vlan_matrix(report: NetworkAnalysisReport) -> pd.DataFrame:
    """
    Create a device-VLAN participation matrix.
    
    Args:
        report: NetworkAnalysisReport to analyze
        
    Returns:
        DataFrame showing which devices participate in which VLANs
    """
    # Collect all devices and VLANs
    all_devices = set()
    vlan_data = {}
    
    for result in report.vlan_results:
        vlan_data[result.vlan_id] = set()
        for island in result.islands:
            all_devices.update(island.devices)
            vlan_data[result.vlan_id].update(island.devices)
    
    # Create matrix
    matrix_data = []
    for device in sorted(all_devices):
        row = {'Device': device}
        for vlan_id in sorted(vlan_data.keys()):
            row[f'VLAN_{vlan_id}'] = device in vlan_data[vlan_id]
        matrix_data.append(row)
    
    return pd.DataFrame(matrix_data)
