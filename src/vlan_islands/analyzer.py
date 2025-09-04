"""
VLAN Island Detection and Analysis Module.

This module implements the core algorithm for detecting VLAN islands in network topologies
using graph theory and connected component analysis.
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
import networkx as nx

from .models import NetworkTopology, Device, Link, VLAN


@dataclass
class VLANIsland:
    """
    Represents a single VLAN island (connected component).
    
    Attributes:
        vlan_id: The VLAN ID this island belongs to
        devices: Set of device IDs in this island
        island_id: Unique identifier for this island within the VLAN
        is_main_island: Whether this is the largest island in the VLAN
    """
    vlan_id: int
    devices: Set[str]
    island_id: int
    is_main_island: bool = False
    
    def __post_init__(self) -> None:
        """Ensure devices is a set."""
        if not isinstance(self.devices, set):
            self.devices = set(self.devices)
    
    @property
    def size(self) -> int:
        """Number of devices in this island."""
        return len(self.devices)
    
    def contains_device(self, device_id: str) -> bool:
        """Check if a device is in this island."""
        return device_id in self.devices


@dataclass
class VLANAnalysisResult:
    """
    Results of VLAN island analysis for a single VLAN.
    
    Attributes:
        vlan_id: The VLAN ID analyzed
        vlan_name: Human-readable VLAN name
        total_devices: Total number of devices configured for this VLAN
        islands: List of detected islands
        has_islands: Whether this VLAN has multiple islands (connectivity issues)
        main_island_size: Size of the largest island
        fragmentation_ratio: Ratio of devices not in the main island
    """
    vlan_id: int
    vlan_name: str
    total_devices: int
    islands: List[VLANIsland]
    has_islands: bool
    main_island_size: int
    fragmentation_ratio: float
    
    @property
    def island_count(self) -> int:
        """Number of islands detected."""
        return len(self.islands)
    
    @property
    def isolated_devices(self) -> int:
        """Number of devices not in the main island."""
        return self.total_devices - self.main_island_size
    
    def get_island_by_device(self, device_id: str) -> Optional[VLANIsland]:
        """Find which island contains a specific device."""
        for island in self.islands:
            if island.contains_device(device_id):
                return island
        return None


@dataclass
class NetworkAnalysisReport:
    """
    Complete network analysis report containing all VLAN island results.
    
    Attributes:
        timestamp: When the analysis was performed
        topology_summary: Basic topology statistics
        vlan_results: Analysis results for each VLAN
        problematic_vlans: VLANs with connectivity issues
        total_islands: Total number of islands across all VLANs
        recommendations: Suggested fixes for detected issues
    """
    timestamp: datetime
    topology_summary: Dict[str, Any]
    vlan_results: List[VLANAnalysisResult]
    problematic_vlans: List[VLANAnalysisResult]
    total_islands: int
    recommendations: List[str]
    
    @property
    def healthy_vlans(self) -> List[VLANAnalysisResult]:
        """VLANs without connectivity issues."""
        return [result for result in self.vlan_results if not result.has_islands]
    
    @property
    def worst_fragmented_vlan(self) -> Optional[VLANAnalysisResult]:
        """VLAN with the highest fragmentation ratio."""
        if not self.problematic_vlans:
            return None
        return max(self.problematic_vlans, key=lambda x: x.fragmentation_ratio)


class VLANIslandAnalyzer:
    """
    Main analyzer class for detecting VLAN islands in network topologies.
    
    Uses graph theory to model the network and identify disconnected components
    within each VLAN's subgraph.
    """
    
    def __init__(self, topology: NetworkTopology):
        """
        Initialize the analyzer with a network topology.
        
        Args:
            topology: NetworkTopology object containing devices, links, and VLANs
        """
        self.topology = topology
        self._physical_graph: Optional[nx.Graph] = None
        self._device_index: Dict[str, Device] = {device.id: device for device in topology.devices}
        self._vlan_index: Dict[int, VLAN] = {vlan.id: vlan for vlan in topology.vlans}
    
    @property
    def physical_graph(self) -> nx.Graph:
        """Get or build the physical network graph."""
        if self._physical_graph is None:
            self._build_physical_graph()
        return self._physical_graph
    
    def _build_physical_graph(self) -> None:
        """Build a NetworkX graph representing the physical network topology."""
        self._physical_graph = nx.Graph()
        
        # Add all devices as nodes
        for device in self.topology.devices:
            self._physical_graph.add_node(
                device.id,
                device_type=device.type.value,
                role=device.role.value,
                location=device.location
            )
        
        # Add all physical links as edges
        for link in self.topology.links:
            self._physical_graph.add_edge(
                link.source,
                link.target,
                link_type=link.type.value,
                speed=link.speed,
                **link.metadata
            )
    
    def _get_vlan_subgraph(self, vlan: VLAN) -> nx.Graph:
        """
        Create a subgraph containing only devices that participate in the given VLAN.
        
        Args:
            vlan: VLAN to create subgraph for
            
        Returns:
            NetworkX graph containing only VLAN participants and their connections
        """
        vlan_devices = set(vlan.devices)
        
        # Create subgraph with only VLAN devices
        subgraph = self.physical_graph.subgraph(vlan_devices).copy()
        
        return subgraph
    
    def _find_connected_components(self, graph: nx.Graph) -> List[Set[str]]:
        """
        Find all connected components in a graph using DFS.
        
        Args:
            graph: NetworkX graph to analyze
            
        Returns:
            List of sets, each containing device IDs in a connected component
        """
        if not graph.nodes():
            return []
        
        visited = set()
        components = []
        
        def dfs(node: str, component: Set[str]) -> None:
            """Depth-first search to find connected component."""
            visited.add(node)
            component.add(node)
            
            for neighbor in graph.neighbors(node):
                if neighbor not in visited:
                    dfs(neighbor, component)
        
        # Find all connected components
        for node in graph.nodes():
            if node not in visited:
                component: Set[str] = set()
                dfs(node, component)
                components.append(component)
        
        return components
    
    def analyze_vlan(self, vlan_id: int) -> Optional[VLANAnalysisResult]:
        """
        Analyze a specific VLAN for islands.
        
        Args:
            vlan_id: ID of the VLAN to analyze
            
        Returns:
            VLANAnalysisResult or None if VLAN doesn't exist
        """
        vlan = self._vlan_index.get(vlan_id)
        if not vlan:
            return None
        
        if not vlan.devices:
            # Empty VLAN - no islands possible
            return VLANAnalysisResult(
                vlan_id=vlan.id,
                vlan_name=vlan.name,
                total_devices=0,
                islands=[],
                has_islands=False,
                main_island_size=0,
                fragmentation_ratio=0.0
            )
        
        # Get VLAN subgraph and find connected components
        vlan_subgraph = self._get_vlan_subgraph(vlan)
        components = self._find_connected_components(vlan_subgraph)
        
        # Create VLANIsland objects
        islands = []
        for i, component in enumerate(components):
            island = VLANIsland(
                vlan_id=vlan.id,
                devices=component,
                island_id=i + 1
            )
            islands.append(island)
        
        # Sort islands by size (largest first) and mark main island
        islands.sort(key=lambda x: x.size, reverse=True)
        if islands:
            islands[0].is_main_island = True
            main_island_size = islands[0].size
        else:
            main_island_size = 0
        
        # Calculate fragmentation ratio
        total_devices = len(vlan.devices)
        fragmentation_ratio = (total_devices - main_island_size) / total_devices if total_devices > 0 else 0.0
        
        return VLANAnalysisResult(
            vlan_id=vlan.id,
            vlan_name=vlan.name,
            total_devices=total_devices,
            islands=islands,
            has_islands=len(islands) > 1,
            main_island_size=main_island_size,
            fragmentation_ratio=fragmentation_ratio
        )
    
    def analyze_all_vlans(self) -> NetworkAnalysisReport:
        """
        Analyze all VLANs in the topology for islands.
        
        Returns:
            Complete network analysis report
        """
        vlan_results = []
        problematic_vlans = []
        total_islands = 0
        
        # Analyze each VLAN
        for vlan in self.topology.vlans:
            result = self.analyze_vlan(vlan.id)
            if result:
                vlan_results.append(result)
                total_islands += result.island_count
                
                if result.has_islands:
                    problematic_vlans.append(result)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(problematic_vlans)
        
        return NetworkAnalysisReport(
            timestamp=datetime.now(),
            topology_summary=self.topology.get_statistics(),
            vlan_results=vlan_results,
            problematic_vlans=problematic_vlans,
            total_islands=total_islands,
            recommendations=recommendations
        )
    
    def _generate_recommendations(self, problematic_vlans: List[VLANAnalysisResult]) -> List[str]:
        """
        Generate recommendations for fixing VLAN islands.
        
        Args:
            problematic_vlans: List of VLANs with connectivity issues
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if not problematic_vlans:
            recommendations.append("[+] No VLAN islands detected. Network topology appears healthy.")
            return recommendations
        
        recommendations.append(f"[!] Detected {len(problematic_vlans)} VLANs with connectivity issues:")
        
        for result in sorted(problematic_vlans, key=lambda x: x.fragmentation_ratio, reverse=True):
            recommendations.append(
                f"  • VLAN {result.vlan_id} ({result.vlan_name}): "
                f"{result.island_count} islands, "
                f"{result.isolated_devices} devices isolated"
            )
        
        recommendations.extend([
            "",
            "💡 Recommended actions:",
            "1. Review physical connectivity between isolated devices",
            "2. Check VLAN configuration on intermediate switches",
            "3. Verify trunk port configurations",
            "4. Consider adding redundant links for critical paths",
            "5. Use network visualization to identify connection gaps"
        ])
        
        # Add specific recommendations for worst cases
        worst_vlan = max(problematic_vlans, key=lambda x: x.fragmentation_ratio)
        if worst_vlan.fragmentation_ratio > 0.5:
            recommendations.extend([
                "",
                f"🔥 Priority: VLAN {worst_vlan.vlan_id} has {worst_vlan.fragmentation_ratio:.1%} "
                f"of devices isolated - investigate immediately"
            ])
        
        return recommendations
    
    def find_connection_paths(self, source_device: str, target_device: str, vlan_id: int) -> List[List[str]]:
        """
        Find all possible connection paths between two devices within a VLAN.
        
        Args:
            source_device: Source device ID
            target_device: Target device ID
            vlan_id: VLAN ID to analyze within
            
        Returns:
            List of paths (each path is a list of device IDs)
        """
        vlan = self._vlan_index.get(vlan_id)
        if not vlan or source_device not in vlan.devices or target_device not in vlan.devices:
            return []
        
        vlan_subgraph = self._get_vlan_subgraph(vlan)
        
        try:
            # Find all simple paths (no repeated nodes)
            paths = list(nx.all_simple_paths(
                vlan_subgraph, 
                source_device, 
                target_device,
                cutoff=10  # Limit path length to avoid excessive computation
            ))
            return paths
        except nx.NetworkXNoPath:
            return []
    
    def get_island_connectivity_suggestions(self, vlan_id: int) -> Dict[str, Any]:
        """
        Get suggestions for connecting VLAN islands.
        
        Args:
            vlan_id: VLAN ID to analyze
            
        Returns:
            Dictionary containing connectivity suggestions
        """
        result = self.analyze_vlan(vlan_id)
        if not result or not result.has_islands:
            return {"message": "No islands detected for this VLAN"}
        
        suggestions = {
            "vlan_id": vlan_id,
            "vlan_name": result.vlan_name,
            "island_count": result.island_count,
            "connection_opportunities": []
        }
        
        # Find potential connection points between islands
        islands = result.islands
        main_island = next((island for island in islands if island.is_main_island), None)
        
        if main_island:
            for island in islands:
                if island == main_island:
                    continue
                
                # Find devices in the isolated island that have physical connections
                # to devices that could potentially bridge to the main island
                bridge_candidates = self._find_bridge_candidates(island.devices, main_island.devices)
                
                if bridge_candidates:
                    suggestions["connection_opportunities"].append({
                        "isolated_island": {
                            "id": island.island_id,
                            "devices": list(island.devices),
                            "size": island.size
                        },
                        "bridge_candidates": bridge_candidates
                    })
        
        return suggestions
    
    def _find_bridge_candidates(self, isolated_devices: Set[str], main_island_devices: Set[str]) -> List[Dict[str, Any]]:
        """
        Find potential bridge points to connect isolated devices to main island.
        
        Args:
            isolated_devices: Set of device IDs in isolated island
            main_island_devices: Set of device IDs in main island
            
        Returns:
            List of bridge candidate information
        """
        candidates = []
        
        # For each isolated device, find its physical neighbors
        for device_id in isolated_devices:
            neighbors = set(self.physical_graph.neighbors(device_id))
            
            # Find neighbors that could potentially bridge to main island
            potential_bridges = neighbors - isolated_devices
            
            for bridge_device in potential_bridges:
                # Check if this bridge device has a path to main island
                bridge_neighbors = set(self.physical_graph.neighbors(bridge_device))
                if bridge_neighbors & main_island_devices:
                    candidates.append({
                        "isolated_device": device_id,
                        "bridge_device": bridge_device,
                        "bridge_type": self._device_index.get(bridge_device, {}).type if bridge_device in self._device_index else "unknown",
                        "action": f"Configure VLAN on {bridge_device} to bridge {device_id} to main island"
                    })
        
        return candidates
