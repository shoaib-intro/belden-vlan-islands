#!/usr/bin/env python3
"""
Test script to analyze the provided network topology and generate reports.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path("src").absolute()))

from vlan_islands.parser import load_network_topology
from vlan_islands.analyzer import VLANIslandAnalyzer
from vlan_islands.reports import ReportGenerator

def main():
    print("🌐 VLAN Islands Detection - Test Analysis")
    print("=" * 50)
    
    # Load network topology
    print("📁 Loading network topology...")
    topology = load_network_topology("data/vlan_islands_data.json")
    print(f"✅ Loaded {len(topology.devices)} devices, {len(topology.links)} links, {len(topology.vlans)} VLANs")
    
    # Analyze for VLAN islands
    print("\n🔍 Analyzing VLAN islands...")
    analyzer = VLANIslandAnalyzer(topology)
    report = analyzer.analyze_all_vlans()
    
    # Print summary
    print(f"\n📊 Analysis Results:")
    print(f"   • Total VLANs: {len(report.vlan_results)}")
    print(f"   • Healthy VLANs: {len(report.healthy_vlans)}")
    print(f"   • Problematic VLANs: {len(report.problematic_vlans)}")
    print(f"   • Total Islands: {report.total_islands}")
    
    # Show problematic VLANs
    if report.problematic_vlans:
        print(f"\n🚨 Problematic VLANs (Top 10):")
        for i, result in enumerate(sorted(report.problematic_vlans, key=lambda x: x.fragmentation_ratio, reverse=True)[:10], 1):
            print(f"   {i:2d}. VLAN {result.vlan_id:3d} ({result.vlan_name:<20}): "
                  f"{result.island_count:2d} islands, {result.fragmentation_ratio:5.1%} fragmented")
    
    # Generate detailed text report
    print(f"\n📄 Generating detailed report...")
    text_report = ReportGenerator.generate_text_report(report, "analysis_report.txt")
    print(f"   • Text report saved: analysis_report.txt")
    
    # Generate JSON report  
    json_report = ReportGenerator.generate_json_report(report, "analysis_report.json")
    print(f"   • JSON report saved: analysis_report.json")
    
    # Generate CSV report
    csv_report = ReportGenerator.generate_csv_report(report, "analysis_report.csv") 
    print(f"   • CSV report saved: analysis_report.csv")
    
    # Show worst VLAN details
    if report.worst_fragmented_vlan:
        worst = report.worst_fragmented_vlan
        print(f"\n🔥 Most Problematic VLAN: {worst.vlan_id} ({worst.vlan_name})")
        print(f"   • Fragmentation: {worst.fragmentation_ratio:.1%}")
        print(f"   • Islands: {worst.island_count}")
        print(f"   • Isolated devices: {worst.isolated_devices}")
        
        # Show island details
        print(f"   • Island breakdown:")
        for island in worst.islands:
            status = "MAIN" if island.is_main_island else "ISOLATED"
            print(f"     - Island {island.island_id} ({status}): {island.size} devices")
    
    # Show recommendations
    print(f"\n💡 Key Recommendations:")
    for i, rec in enumerate(report.recommendations[:5], 1):
        print(f"   {i}. {rec}")
    
    print(f"\n✅ Analysis complete! Check the generated report files for detailed information.")

if __name__ == "__main__":
    main()
