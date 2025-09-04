"""
Network topology parser for loading and validating JSON network data.

This module provides functionality to parse network topology data from JSON files
and convert them into validated Pydantic models.
"""

import json
from pathlib import Path
from typing import Dict, Any, Union
from pydantic import ValidationError

from .models import NetworkTopology, Device, Link, VLAN


class NetworkParseError(Exception):
    """Exception raised when network data cannot be parsed."""
    pass


class NetworkTopologyParser:
    """
    Parser for network topology JSON data.
    
    Handles loading, validation, and conversion of network topology data
    from JSON format into structured Pydantic models.
    """
    
    @staticmethod
    def load_from_file(file_path: Union[str, Path]) -> NetworkTopology:
        """
        Load network topology from a JSON file.
        
        Args:
            file_path: Path to the JSON file containing network topology data
            
        Returns:
            NetworkTopology: Validated network topology object
            
        Raises:
            NetworkParseError: If file cannot be read or data is invalid
            FileNotFoundError: If the specified file doesn't exist
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Network topology file not found: {file_path}")
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return NetworkTopologyParser.parse_from_dict(data)
            
        except json.JSONDecodeError as e:
            raise NetworkParseError(f"Invalid JSON format in {file_path}: {e}")
        except Exception as e:
            if isinstance(e, (NetworkParseError, FileNotFoundError)):
                raise
            raise NetworkParseError(f"Failed to load network topology from {file_path}: {e}")
    
    @staticmethod
    def parse_from_dict(data: Dict[str, Any]) -> NetworkTopology:
        """
        Parse network topology from a dictionary.
        
        Args:
            data: Dictionary containing network topology data
            
        Returns:
            NetworkTopology: Validated network topology object
            
        Raises:
            NetworkParseError: If data structure is invalid
        """
        try:
            # Validate required top-level keys
            required_keys = {'devices', 'links', 'vlans'}
            missing_keys = required_keys - set(data.keys())
            if missing_keys:
                raise NetworkParseError(f"Missing required keys: {missing_keys}")
            
            # Parse devices
            devices = []
            for device_data in data.get('devices', []):
                try:
                    device = Device(**device_data)
                    devices.append(device)
                except ValidationError as e:
                    raise NetworkParseError(f"Invalid device data for {device_data.get('id', 'unknown')}: {e}")
            
            # Parse links
            links = []
            for link_data in data.get('links', []):
                try:
                    link = Link(**link_data)
                    links.append(link)
                except ValidationError as e:
                    raise NetworkParseError(f"Invalid link data {link_data.get('source', '?')} -> {link_data.get('target', '?')}: {e}")
            
            # Parse VLANs
            vlans = []
            for vlan_data in data.get('vlans', []):
                try:
                    vlan = VLAN(**vlan_data)
                    vlans.append(vlan)
                except ValidationError as e:
                    raise NetworkParseError(f"Invalid VLAN data for VLAN {vlan_data.get('id', 'unknown')}: {e}")
            
            # Create and validate the complete topology
            topology = NetworkTopology(
                devices=devices,
                links=links,
                vlans=vlans
            )
            
            # Perform additional validation
            validation_errors = topology.validate_topology()
            if validation_errors:
                error_msg = "Topology validation failed:\n" + "\n".join(f"  - {error}" for error in validation_errors)
                raise NetworkParseError(error_msg)
            
            return topology
            
        except ValidationError as e:
            raise NetworkParseError(f"Network topology validation failed: {e}")
        except Exception as e:
            if isinstance(e, NetworkParseError):
                raise
            raise NetworkParseError(f"Failed to parse network topology: {e}")
    
    @staticmethod
    def save_to_file(topology: NetworkTopology, file_path: Union[str, Path]) -> None:
        """
        Save network topology to a JSON file.
        
        Args:
            topology: NetworkTopology object to save
            file_path: Path where to save the JSON file
            
        Raises:
            NetworkParseError: If data cannot be serialized or file cannot be written
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dictionary format
            data = {
                'devices': [device.dict() for device in topology.devices],
                'links': [link.dict() for link in topology.links],
                'vlans': [vlan.dict() for vlan in topology.vlans]
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise NetworkParseError(f"Failed to save network topology to {file_path}: {e}")
    
    @staticmethod
    def validate_file(file_path: Union[str, Path]) -> tuple[bool, list[str]]:
        """
        Validate a network topology file without fully loading it.
        
        Args:
            file_path: Path to the JSON file to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            topology = NetworkTopologyParser.load_from_file(file_path)
            additional_errors = topology.validate_topology()
            errors.extend(additional_errors)
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(str(e))
            return False, errors
    
    @staticmethod
    def get_topology_summary(topology: NetworkTopology) -> Dict[str, Any]:
        """
        Get a summary of the network topology.
        
        Args:
            topology: NetworkTopology object to summarize
            
        Returns:
            Dictionary containing topology summary statistics
        """
        stats = topology.get_statistics()
        
        # Add additional summary information
        stats.update({
            'vlan_summary': {
                vlan.id: {
                    'name': vlan.name,
                    'device_count': len(vlan.devices),
                    'description': vlan.description
                }
                for vlan in topology.vlans
            },
            'largest_vlan': max(
                (len(vlan.devices) for vlan in topology.vlans),
                default=0
            ),
            'smallest_vlan': min(
                (len(vlan.devices) for vlan in topology.vlans if vlan.devices),
                default=0
            ),
            'devices_per_location': {},
        })
        
        # Count devices per location
        location_counts: Dict[str, int] = {}
        for device in topology.devices:
            location_counts[device.location] = location_counts.get(device.location, 0) + 1
        stats['devices_per_location'] = location_counts
        
        return stats


def load_network_topology(file_path: Union[str, Path]) -> NetworkTopology:
    """
    Convenience function to load a network topology from a file.
    
    Args:
        file_path: Path to the network topology JSON file
        
    Returns:
        NetworkTopology: Validated network topology object
        
    Raises:
        NetworkParseError: If the file cannot be loaded or is invalid
        FileNotFoundError: If the file doesn't exist
    """
    return NetworkTopologyParser.load_from_file(file_path)
