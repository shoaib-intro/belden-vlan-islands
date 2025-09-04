"""
Data models for network topology representation using Pydantic.

This module defines the core data structures for representing network devices,
links, VLANs, and the overall network topology.
"""

from typing import List, Dict, Optional, Set, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class DeviceType(str, Enum):
    """Enumeration of supported network device types."""
    SWITCH = "switch"
    ROUTER = "router"
    CONTROLLER = "controller"
    ACCESS_POINT = "access-point"


class DeviceRole(str, Enum):
    """Enumeration of network device roles in the hierarchy."""
    CORE = "core"
    DISTRIBUTION = "distribution"
    ACCESS = "access"
    EDGE = "edge"
    WIFI = "wifi"
    STORAGE = "storage"


class LinkType(str, Enum):
    """Enumeration of supported link types."""
    ETHERNET = "ethernet"
    FIBER = "fiber"
    WIRELESS = "wireless"


class Device(BaseModel):
    """
    Represents a network device (switch, router, access point, etc.).
    
    Attributes:
        id: Unique identifier for the device
        type: Type of network device
        role: Role in network hierarchy
        location: Physical location of the device
        metadata: Additional device-specific information
    """
    id: str = Field(..., description="Unique device identifier")
    type: DeviceType = Field(..., description="Device type")
    role: DeviceRole = Field(..., description="Device role in network hierarchy")
    location: str = Field(..., description="Physical location")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator('id')
    def validate_id(cls, v: str) -> str:
        """Ensure device ID is non-empty and valid."""
        if not v or not v.strip():
            raise ValueError("Device ID cannot be empty")
        return v.strip()

    def __hash__(self) -> int:
        """Make Device hashable for use in sets and as dict keys."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Device equality based on ID."""
        if not isinstance(other, Device):
            return NotImplemented
        return self.id == other.id


class Link(BaseModel):
    """
    Represents a physical connection between two network devices.
    
    Attributes:
        source: Source device ID
        target: Target device ID
        type: Type of physical connection
        speed: Connection speed (e.g., "1G", "10G", "40G")
        metadata: Additional link-specific information
    """
    source: str = Field(..., description="Source device ID")
    target: str = Field(..., description="Target device ID")
    type: LinkType = Field(..., description="Physical connection type")
    speed: str = Field(..., description="Connection speed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator('source', 'target')
    def validate_endpoints(cls, v: str) -> str:
        """Ensure link endpoints are non-empty."""
        if not v or not v.strip():
            raise ValueError("Link endpoints cannot be empty")
        return v.strip()

    @validator('speed')
    def validate_speed(cls, v: str) -> str:
        """Validate speed format."""
        if not v or not v.strip():
            raise ValueError("Speed cannot be empty")
        # Basic validation - could be enhanced with regex for specific formats
        return v.strip()

    def get_endpoints(self) -> tuple[str, str]:
        """Get both endpoints of the link."""
        return (self.source, self.target)

    def connects_device(self, device_id: str) -> bool:
        """Check if this link connects to a specific device."""
        return device_id in (self.source, self.target)

    def get_other_endpoint(self, device_id: str) -> Optional[str]:
        """Get the other endpoint of a link given one endpoint."""
        if device_id == self.source:
            return self.target
        elif device_id == self.target:
            return self.source
        return None


class VLAN(BaseModel):
    """
    Represents a VLAN configuration.
    
    Attributes:
        id: VLAN ID (typically 1-4094)
        name: Human-readable VLAN name
        description: VLAN description
        devices: List of device IDs that participate in this VLAN
        metadata: Additional VLAN-specific information
    """
    id: int = Field(..., ge=1, le=4094, description="VLAN ID (1-4094)")
    name: str = Field(..., description="VLAN name")
    description: str = Field(default="", description="VLAN description")
    devices: List[str] = Field(default_factory=list, description="Participating device IDs")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator('name')
    def validate_name(cls, v: str) -> str:
        """Ensure VLAN name is non-empty."""
        if not v or not v.strip():
            raise ValueError("VLAN name cannot be empty")
        return v.strip()

    @validator('devices')
    def validate_devices(cls, v: List[str]) -> List[str]:
        """Remove duplicates and empty device IDs."""
        return list(set(device.strip() for device in v if device and device.strip()))

    def get_device_set(self) -> Set[str]:
        """Get devices as a set for efficient operations."""
        return set(self.devices)

    def has_device(self, device_id: str) -> bool:
        """Check if a device participates in this VLAN."""
        return device_id in self.devices

    def add_device(self, device_id: str) -> None:
        """Add a device to this VLAN."""
        if device_id and device_id.strip() and device_id not in self.devices:
            self.devices.append(device_id.strip())

    def remove_device(self, device_id: str) -> bool:
        """Remove a device from this VLAN. Returns True if device was removed."""
        try:
            self.devices.remove(device_id)
            return True
        except ValueError:
            return False


class NetworkTopology(BaseModel):
    """
    Represents the complete network topology including devices, links, and VLANs.
    
    Attributes:
        devices: List of all network devices
        links: List of all physical connections
        vlans: List of all VLAN configurations
    """
    devices: List[Device] = Field(default_factory=list, description="Network devices")
    links: List[Link] = Field(default_factory=list, description="Physical connections")
    vlans: List[VLAN] = Field(default_factory=list, description="VLAN configurations")

    @validator('devices')
    def validate_unique_devices(cls, v: List[Device]) -> List[Device]:
        """Ensure all device IDs are unique."""
        device_ids = [device.id for device in v]
        if len(device_ids) != len(set(device_ids)):
            raise ValueError("Duplicate device IDs found")
        return v

    @validator('vlans')
    def validate_unique_vlans(cls, v: List[VLAN]) -> List[VLAN]:
        """Ensure all VLAN IDs are unique."""
        vlan_ids = [vlan.id for vlan in v]
        if len(vlan_ids) != len(set(vlan_ids)):
            raise ValueError("Duplicate VLAN IDs found")
        return v

    def get_device_by_id(self, device_id: str) -> Optional[Device]:
        """Get a device by its ID."""
        for device in self.devices:
            if device.id == device_id:
                return device
        return None

    def get_vlan_by_id(self, vlan_id: int) -> Optional[VLAN]:
        """Get a VLAN by its ID."""
        for vlan in self.vlans:
            if vlan.id == vlan_id:
                return vlan
        return None

    def get_device_links(self, device_id: str) -> List[Link]:
        """Get all links connected to a specific device."""
        return [link for link in self.links if link.connects_device(device_id)]

    def get_device_neighbors(self, device_id: str) -> List[str]:
        """Get all neighboring device IDs for a given device."""
        neighbors = []
        for link in self.links:
            other = link.get_other_endpoint(device_id)
            if other:
                neighbors.append(other)
        return neighbors

    def validate_topology(self) -> List[str]:
        """
        Validate the network topology and return a list of validation errors.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check that all devices referenced in links exist
        device_ids = {device.id for device in self.devices}
        for link in self.links:
            if link.source not in device_ids:
                errors.append(f"Link references non-existent source device: {link.source}")
            if link.target not in device_ids:
                errors.append(f"Link references non-existent target device: {link.target}")
        
        # Check that all devices referenced in VLANs exist
        for vlan in self.vlans:
            for device_id in vlan.devices:
                if device_id not in device_ids:
                    errors.append(f"VLAN {vlan.id} references non-existent device: {device_id}")
        
        return errors

    def get_statistics(self) -> Dict[str, Any]:
        """Get basic topology statistics."""
        return {
            "total_devices": len(self.devices),
            "total_links": len(self.links),
            "total_vlans": len(self.vlans),
            "device_types": {
                device_type.value: sum(1 for d in self.devices if d.type == device_type)
                for device_type in DeviceType
            },
            "device_roles": {
                role.value: sum(1 for d in self.devices if d.role == role)
                for role in DeviceRole
            },
            "average_links_per_device": len(self.links) * 2 / len(self.devices) if self.devices else 0,
        }
