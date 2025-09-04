"""
Comprehensive test cases for VLAN island detection algorithm.

These tests verify the correctness of the island detection algorithm
using various network topologies and edge cases.
"""

import pytest
from typing import List, Dict, Any

from vlan_islands.models import NetworkTopology, Device, Link, VLAN, DeviceType, DeviceRole, LinkType
from vlan_islands.analyzer import VLANIslandAnalyzer, VLANIsland, VLANAnalysisResult


class TestVLANIslandAnalyzer:
    """Test cases for the VLANIslandAnalyzer class."""
    
    def create_simple_topology(self) -> NetworkTopology:
        """Create a simple test topology with known island structure."""
        devices = [
            Device(id="sw1", type=DeviceType.SWITCH, role=DeviceRole.CORE, location="datacenter"),
            Device(id="sw2", type=DeviceType.SWITCH, role=DeviceRole.DISTRIBUTION, location="building-a"),
            Device(id="sw3", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="building-a"),
            Device(id="sw4", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="building-b"),
            Device(id="sw5", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="building-b"),
        ]
        
        links = [
            Link(source="sw1", target="sw2", type=LinkType.ETHERNET, speed="10G"),
            Link(source="sw2", target="sw3", type=LinkType.ETHERNET, speed="1G"),
            # Note: sw4 and sw5 are connected to each other but not to the main network
            Link(source="sw4", target="sw5", type=LinkType.ETHERNET, speed="1G"),
        ]
        
        vlans = [
            VLAN(id=100, name="Test-VLAN", description="Test VLAN with islands", 
                 devices=["sw1", "sw2", "sw3", "sw4", "sw5"]),
            VLAN(id=200, name="Healthy-VLAN", description="Healthy VLAN", 
                 devices=["sw1", "sw2", "sw3"]),
            VLAN(id=300, name="Empty-VLAN", description="Empty VLAN", devices=[]),
        ]
        
        return NetworkTopology(devices=devices, links=links, vlans=vlans)
    
    def create_complex_topology(self) -> NetworkTopology:
        """Create a more complex topology with multiple island scenarios."""
        devices = [
            # Core layer
            Device(id="core1", type=DeviceType.SWITCH, role=DeviceRole.CORE, location="datacenter"),
            Device(id="core2", type=DeviceType.SWITCH, role=DeviceRole.CORE, location="datacenter"),
            
            # Distribution layer
            Device(id="dist1", type=DeviceType.SWITCH, role=DeviceRole.DISTRIBUTION, location="building-a"),
            Device(id="dist2", type=DeviceType.SWITCH, role=DeviceRole.DISTRIBUTION, location="building-a"),
            Device(id="dist3", type=DeviceType.SWITCH, role=DeviceRole.DISTRIBUTION, location="building-b"),
            
            # Access layer
            Device(id="acc1", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="building-a-floor1"),
            Device(id="acc2", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="building-a-floor2"),
            Device(id="acc3", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="building-b-floor1"),
            Device(id="acc4", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="building-b-floor2"),
            
            # Isolated devices
            Device(id="isolated1", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="remote"),
            Device(id="isolated2", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="remote"),
        ]
        
        links = [
            # Core interconnection
            Link(source="core1", target="core2", type=LinkType.ETHERNET, speed="40G"),
            
            # Core to distribution
            Link(source="core1", target="dist1", type=LinkType.ETHERNET, speed="10G"),
            Link(source="core2", target="dist2", type=LinkType.ETHERNET, speed="10G"),
            Link(source="core1", target="dist3", type=LinkType.ETHERNET, speed="10G"),
            
            # Distribution redundancy
            Link(source="dist1", target="dist2", type=LinkType.ETHERNET, speed="10G"),
            
            # Distribution to access
            Link(source="dist1", target="acc1", type=LinkType.ETHERNET, speed="1G"),
            Link(source="dist2", target="acc2", type=LinkType.ETHERNET, speed="1G"),
            Link(source="dist3", target="acc3", type=LinkType.ETHERNET, speed="1G"),
            Link(source="dist3", target="acc4", type=LinkType.ETHERNET, speed="1G"),
            
            # Isolated island
            Link(source="isolated1", target="isolated2", type=LinkType.ETHERNET, speed="1G"),
        ]
        
        vlans = [
            # VLAN with multiple islands
            VLAN(id=100, name="Multi-Island-VLAN", description="VLAN with 3 islands",
                 devices=["core1", "core2", "dist1", "dist2", "acc1", "acc2", "acc3", "isolated1", "isolated2"]),
            
            # VLAN with single island (healthy)
            VLAN(id=200, name="Healthy-VLAN", description="Connected VLAN",
                 devices=["core1", "core2", "dist1", "dist2", "acc1", "acc2"]),
            
            # VLAN with only isolated devices
            VLAN(id=300, name="Isolated-Only-VLAN", description="Only isolated devices",
                 devices=["isolated1", "isolated2"]),
            
            # Single device VLAN
            VLAN(id=400, name="Single-Device-VLAN", description="Single device",
                 devices=["core1"]),
        ]
        
        return NetworkTopology(devices=devices, links=links, vlans=vlans)
    
    def test_simple_island_detection(self):
        """Test basic island detection with simple topology."""
        topology = self.create_simple_topology()
        analyzer = VLANIslandAnalyzer(topology)
        
        # Test VLAN 100 (should have 2 islands)
        result = analyzer.analyze_vlan(100)
        assert result is not None
        assert result.vlan_id == 100
        assert result.vlan_name == "Test-VLAN"
        assert result.has_islands is True
        assert result.island_count == 2
        assert result.total_devices == 5
        assert result.main_island_size == 3  # sw1, sw2, sw3
        assert result.isolated_devices == 2  # sw4, sw5
        
        # Check islands
        assert len(result.islands) == 2
        main_island = next(island for island in result.islands if island.is_main_island)
        isolated_island = next(island for island in result.islands if not island.is_main_island)
        
        assert main_island.size == 3
        assert isolated_island.size == 2
        assert main_island.devices == {"sw1", "sw2", "sw3"}
        assert isolated_island.devices == {"sw4", "sw5"}
    
    def test_healthy_vlan(self):
        """Test detection of healthy VLAN with no islands."""
        topology = self.create_simple_topology()
        analyzer = VLANIslandAnalyzer(topology)
        
        # Test VLAN 200 (should be healthy)
        result = analyzer.analyze_vlan(200)
        assert result is not None
        assert result.has_islands is False
        assert result.island_count == 1
        assert result.main_island_size == 3
        assert result.isolated_devices == 0
        assert result.fragmentation_ratio == 0.0
    
    def test_empty_vlan(self):
        """Test handling of empty VLAN."""
        topology = self.create_simple_topology()
        analyzer = VLANIslandAnalyzer(topology)
        
        # Test VLAN 300 (empty)
        result = analyzer.analyze_vlan(300)
        assert result is not None
        assert result.has_islands is False
        assert result.island_count == 0
        assert result.total_devices == 0
        assert result.main_island_size == 0
        assert result.isolated_devices == 0
        assert result.fragmentation_ratio == 0.0
    
    def test_nonexistent_vlan(self):
        """Test handling of non-existent VLAN."""
        topology = self.create_simple_topology()
        analyzer = VLANIslandAnalyzer(topology)
        
        result = analyzer.analyze_vlan(999)
        assert result is None
    
    def test_complex_topology_analysis(self):
        """Test analysis of complex topology with multiple scenarios."""
        topology = self.create_complex_topology()
        analyzer = VLANIslandAnalyzer(topology)
        
        # Test VLAN 100 (multi-island)
        result = analyzer.analyze_vlan(100)
        assert result is not None
        assert result.has_islands is True
        assert result.island_count == 3  # Main network, acc3, isolated pair
        
        # Find the main island (should be largest)
        main_island = next(island for island in result.islands if island.is_main_island)
        assert main_island.size >= 6  # core1, core2, dist1, dist2, acc1, acc2
        
        # Test VLAN 300 (isolated only)
        result_isolated = analyzer.analyze_vlan(300)
        assert result_isolated is not None
        assert result_isolated.has_islands is False  # Only one island
        assert result_isolated.island_count == 1
        assert result_isolated.main_island_size == 2
        
        # Test VLAN 400 (single device)
        result_single = analyzer.analyze_vlan(400)
        assert result_single is not None
        assert result_single.has_islands is False
        assert result_single.island_count == 1
        assert result_single.main_island_size == 1
        assert result_single.total_devices == 1
    
    def test_full_network_analysis(self):
        """Test complete network analysis."""
        topology = self.create_complex_topology()
        analyzer = VLANIslandAnalyzer(topology)
        
        report = analyzer.analyze_all_vlans()
        
        assert report is not None
        assert len(report.vlan_results) == 4
        assert len(report.problematic_vlans) >= 1  # At least VLAN 100 has issues
        assert report.total_islands >= 4  # Sum of all islands
        
        # Check that problematic VLANs are correctly identified
        problematic_ids = {result.vlan_id for result in report.problematic_vlans}
        assert 100 in problematic_ids  # Multi-island VLAN should be problematic
        
        # Check recommendations are generated
        assert len(report.recommendations) > 0
    
    def test_fragmentation_ratio_calculation(self):
        """Test correct calculation of fragmentation ratios."""
        topology = self.create_simple_topology()
        analyzer = VLANIslandAnalyzer(topology)
        
        result = analyzer.analyze_vlan(100)
        assert result is not None
        
        # VLAN 100: 5 total devices, 3 in main island, 2 isolated
        # Fragmentation ratio = 2/5 = 0.4
        expected_ratio = 2.0 / 5.0
        assert abs(result.fragmentation_ratio - expected_ratio) < 0.001
    
    def test_island_device_membership(self):
        """Test that devices are correctly assigned to islands."""
        topology = self.create_simple_topology()
        analyzer = VLANIslandAnalyzer(topology)
        
        result = analyzer.analyze_vlan(100)
        assert result is not None
        
        # Check that all devices are assigned to exactly one island
        all_island_devices = set()
        for island in result.islands:
            assert len(island.devices & all_island_devices) == 0  # No overlap
            all_island_devices.update(island.devices)
        
        # All VLAN devices should be in some island
        vlan = next(v for v in topology.vlans if v.id == 100)
        assert all_island_devices == set(vlan.devices)
    
    def test_connection_path_finding(self):
        """Test finding connection paths between devices."""
        topology = self.create_simple_topology()
        analyzer = VLANIslandAnalyzer(topology)
        
        # Test path within connected component
        paths = analyzer.find_connection_paths("sw1", "sw3", 100)
        assert len(paths) > 0
        assert ["sw1", "sw2", "sw3"] in paths
        
        # Test path between disconnected components (should be empty)
        paths_disconnected = analyzer.find_connection_paths("sw1", "sw4", 100)
        assert len(paths_disconnected) == 0
        
        # Test path for devices not in VLAN
        paths_not_in_vlan = analyzer.find_connection_paths("sw1", "sw4", 200)
        assert len(paths_not_in_vlan) == 0
    
    def test_connectivity_suggestions(self):
        """Test generation of connectivity suggestions."""
        topology = self.create_simple_topology()
        analyzer = VLANIslandAnalyzer(topology)
        
        suggestions = analyzer.get_island_connectivity_suggestions(100)
        
        assert "vlan_id" in suggestions
        assert suggestions["vlan_id"] == 100
        assert "island_count" in suggestions
        assert suggestions["island_count"] == 2
        assert "connection_opportunities" in suggestions
        
        # Should have suggestions for connecting isolated island
        opportunities = suggestions["connection_opportunities"]
        assert len(opportunities) > 0
    
    def test_physical_graph_construction(self):
        """Test that physical graph is correctly constructed."""
        topology = self.create_simple_topology()
        analyzer = VLANIslandAnalyzer(topology)
        
        graph = analyzer.physical_graph
        
        # Check all devices are nodes
        assert len(graph.nodes()) == len(topology.devices)
        for device in topology.devices:
            assert device.id in graph.nodes()
        
        # Check all links are edges
        assert len(graph.edges()) == len(topology.links)
        for link in topology.links:
            assert graph.has_edge(link.source, link.target)
    
    def test_vlan_subgraph_creation(self):
        """Test creation of VLAN-specific subgraphs."""
        topology = self.create_simple_topology()
        analyzer = VLANIslandAnalyzer(topology)
        
        vlan = next(v for v in topology.vlans if v.id == 100)
        subgraph = analyzer._get_vlan_subgraph(vlan)
        
        # Subgraph should only contain VLAN devices
        assert set(subgraph.nodes()) == set(vlan.devices)
        
        # Should only have edges between VLAN devices
        for edge in subgraph.edges():
            assert edge[0] in vlan.devices
            assert edge[1] in vlan.devices
    
    def test_connected_components_algorithm(self):
        """Test the connected components detection algorithm."""
        topology = self.create_simple_topology()
        analyzer = VLANIslandAnalyzer(topology)
        
        vlan = next(v for v in topology.vlans if v.id == 100)
        subgraph = analyzer._get_vlan_subgraph(vlan)
        components = analyzer._find_connected_components(subgraph)
        
        assert len(components) == 2
        
        # Sort components by size for consistent testing
        components.sort(key=len, reverse=True)
        
        assert len(components[0]) == 3  # Main component
        assert len(components[1]) == 2  # Isolated component
        
        assert components[0] == {"sw1", "sw2", "sw3"}
        assert components[1] == {"sw4", "sw5"}


class TestVLANAnalysisResult:
    """Test cases for VLANAnalysisResult data class."""
    
    def test_analysis_result_properties(self):
        """Test computed properties of VLANAnalysisResult."""
        islands = [
            VLANIsland(vlan_id=100, devices={"sw1", "sw2", "sw3"}, island_id=1, is_main_island=True),
            VLANIsland(vlan_id=100, devices={"sw4", "sw5"}, island_id=2, is_main_island=False),
        ]
        
        result = VLANAnalysisResult(
            vlan_id=100,
            vlan_name="Test-VLAN",
            total_devices=5,
            islands=islands,
            has_islands=True,
            main_island_size=3,
            fragmentation_ratio=0.4
        )
        
        assert result.island_count == 2
        assert result.isolated_devices == 2
        
        # Test finding island by device
        island = result.get_island_by_device("sw2")
        assert island is not None
        assert island.is_main_island is True
        
        island_isolated = result.get_island_by_device("sw4")
        assert island_isolated is not None
        assert island_isolated.is_main_island is False
        
        # Test non-existent device
        assert result.get_island_by_device("nonexistent") is None


class TestVLANIsland:
    """Test cases for VLANIsland data class."""
    
    def test_island_properties(self):
        """Test VLANIsland properties and methods."""
        devices = {"sw1", "sw2", "sw3"}
        island = VLANIsland(vlan_id=100, devices=devices, island_id=1)
        
        assert island.size == 3
        assert island.contains_device("sw1") is True
        assert island.contains_device("sw4") is False
        
        # Test post-init conversion to set
        island_from_list = VLANIsland(vlan_id=100, devices=["sw1", "sw2"], island_id=1)
        assert isinstance(island_from_list.devices, set)
        assert island_from_list.devices == {"sw1", "sw2"}


@pytest.fixture
def sample_topology():
    """Fixture providing a sample topology for tests."""
    return TestVLANIslandAnalyzer().create_simple_topology()


@pytest.fixture
def complex_topology():
    """Fixture providing a complex topology for tests."""
    return TestVLANIslandAnalyzer().create_complex_topology()


def test_analyzer_initialization(sample_topology):
    """Test analyzer initialization with topology."""
    analyzer = VLANIslandAnalyzer(sample_topology)
    
    assert analyzer.topology == sample_topology
    assert len(analyzer._device_index) == len(sample_topology.devices)
    assert len(analyzer._vlan_index) == len(sample_topology.vlans)


def test_edge_cases():
    """Test various edge cases and error conditions."""
    # Empty topology
    empty_topology = NetworkTopology(devices=[], links=[], vlans=[])
    analyzer = VLANIslandAnalyzer(empty_topology)
    report = analyzer.analyze_all_vlans()
    
    assert len(report.vlan_results) == 0
    assert len(report.problematic_vlans) == 0
    assert report.total_islands == 0
    
    # Topology with devices but no links
    devices_only = NetworkTopology(
        devices=[
            Device(id="sw1", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="test"),
            Device(id="sw2", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="test"),
        ],
        links=[],
        vlans=[
            VLAN(id=100, name="Test", devices=["sw1", "sw2"])
        ]
    )
    
    analyzer_no_links = VLANIslandAnalyzer(devices_only)
    result = analyzer_no_links.analyze_vlan(100)
    
    # Should detect 2 islands (each device is isolated)
    assert result.has_islands is True
    assert result.island_count == 2
    assert result.main_island_size == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
