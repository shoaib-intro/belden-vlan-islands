"""
Test cases for data models and validation.
"""

import pytest
from pydantic import ValidationError

from vlan_islands.models import (
    Device, Link, VLAN, NetworkTopology,
    DeviceType, DeviceRole, LinkType
)


class TestDevice:
    """Test cases for Device model."""
    
    def test_valid_device_creation(self):
        """Test creating a valid device."""
        device = Device(
            id="sw-001",
            type=DeviceType.SWITCH,
            role=DeviceRole.CORE,
            location="datacenter"
        )
        
        assert device.id == "sw-001"
        assert device.type == DeviceType.SWITCH
        assert device.role == DeviceRole.CORE
        assert device.location == "datacenter"
        assert device.metadata == {}
    
    def test_device_with_metadata(self):
        """Test device creation with metadata."""
        metadata = {"vendor": "Cisco", "model": "Catalyst 9300"}
        device = Device(
            id="sw-001",
            type=DeviceType.SWITCH,
            role=DeviceRole.ACCESS,
            location="building-a",
            metadata=metadata
        )
        
        assert device.metadata == metadata
    
    def test_device_id_validation(self):
        """Test device ID validation."""
        # Empty ID should fail
        with pytest.raises(ValidationError):
            Device(
                id="",
                type=DeviceType.SWITCH,
                role=DeviceRole.ACCESS,
                location="test"
            )
        
        # Whitespace-only ID should fail
        with pytest.raises(ValidationError):
            Device(
                id="   ",
                type=DeviceType.SWITCH,
                role=DeviceRole.ACCESS,
                location="test"
            )
    
    def test_device_id_trimming(self):
        """Test that device ID is trimmed."""
        device = Device(
            id="  sw-001  ",
            type=DeviceType.SWITCH,
            role=DeviceRole.ACCESS,
            location="test"
        )
        
        assert device.id == "sw-001"
    
    def test_device_equality(self):
        """Test device equality based on ID."""
        device1 = Device(id="sw-001", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="a")
        device2 = Device(id="sw-001", type=DeviceType.ROUTER, role=DeviceRole.CORE, location="b")
        device3 = Device(id="sw-002", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="a")
        
        assert device1 == device2  # Same ID
        assert device1 != device3  # Different ID
        assert device1 != "not-a-device"  # Different type
    
    def test_device_hashable(self):
        """Test that devices can be used in sets and as dict keys."""
        device1 = Device(id="sw-001", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="a")
        device2 = Device(id="sw-002", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="a")
        
        device_set = {device1, device2}
        assert len(device_set) == 2
        
        device_dict = {device1: "value1", device2: "value2"}
        assert len(device_dict) == 2


class TestLink:
    """Test cases for Link model."""
    
    def test_valid_link_creation(self):
        """Test creating a valid link."""
        link = Link(
            source="sw-001",
            target="sw-002",
            type=LinkType.ETHERNET,
            speed="10G"
        )
        
        assert link.source == "sw-001"
        assert link.target == "sw-002"
        assert link.type == LinkType.ETHERNET
        assert link.speed == "10G"
        assert link.metadata == {}
    
    def test_link_endpoint_validation(self):
        """Test link endpoint validation."""
        # Empty source should fail
        with pytest.raises(ValidationError):
            Link(source="", target="sw-002", type=LinkType.ETHERNET, speed="1G")
        
        # Empty target should fail
        with pytest.raises(ValidationError):
            Link(source="sw-001", target="", type=LinkType.ETHERNET, speed="1G")
        
        # Empty speed should fail
        with pytest.raises(ValidationError):
            Link(source="sw-001", target="sw-002", type=LinkType.ETHERNET, speed="")
    
    def test_link_endpoint_trimming(self):
        """Test that link endpoints are trimmed."""
        link = Link(
            source="  sw-001  ",
            target="  sw-002  ",
            type=LinkType.ETHERNET,
            speed="  10G  "
        )
        
        assert link.source == "sw-001"
        assert link.target == "sw-002"
        assert link.speed == "10G"
    
    def test_link_methods(self):
        """Test link utility methods."""
        link = Link(
            source="sw-001",
            target="sw-002",
            type=LinkType.ETHERNET,
            speed="10G"
        )
        
        # Test get_endpoints
        endpoints = link.get_endpoints()
        assert endpoints == ("sw-001", "sw-002")
        
        # Test connects_device
        assert link.connects_device("sw-001") is True
        assert link.connects_device("sw-002") is True
        assert link.connects_device("sw-003") is False
        
        # Test get_other_endpoint
        assert link.get_other_endpoint("sw-001") == "sw-002"
        assert link.get_other_endpoint("sw-002") == "sw-001"
        assert link.get_other_endpoint("sw-003") is None


class TestVLAN:
    """Test cases for VLAN model."""
    
    def test_valid_vlan_creation(self):
        """Test creating a valid VLAN."""
        vlan = VLAN(
            id=100,
            name="Corporate",
            description="Corporate network VLAN",
            devices=["sw-001", "sw-002", "sw-003"]
        )
        
        assert vlan.id == 100
        assert vlan.name == "Corporate"
        assert vlan.description == "Corporate network VLAN"
        assert vlan.devices == ["sw-001", "sw-002", "sw-003"]
    
    def test_vlan_id_validation(self):
        """Test VLAN ID validation."""
        # ID too low should fail
        with pytest.raises(ValidationError):
            VLAN(id=0, name="Test", devices=[])
        
        # ID too high should fail
        with pytest.raises(ValidationError):
            VLAN(id=4095, name="Test", devices=[])
        
        # Valid range should work
        vlan = VLAN(id=1, name="Test", devices=[])
        assert vlan.id == 1
        
        vlan = VLAN(id=4094, name="Test", devices=[])
        assert vlan.id == 4094
    
    def test_vlan_name_validation(self):
        """Test VLAN name validation."""
        # Empty name should fail
        with pytest.raises(ValidationError):
            VLAN(id=100, name="", devices=[])
        
        # Whitespace-only name should fail
        with pytest.raises(ValidationError):
            VLAN(id=100, name="   ", devices=[])
    
    def test_vlan_name_trimming(self):
        """Test that VLAN name is trimmed."""
        vlan = VLAN(id=100, name="  Corporate  ", devices=[])
        assert vlan.name == "Corporate"
    
    def test_vlan_device_deduplication(self):
        """Test that duplicate devices are removed."""
        vlan = VLAN(
            id=100,
            name="Test",
            devices=["sw-001", "sw-002", "sw-001", "sw-003", "sw-002"]
        )
        
        # Should have unique devices only
        assert len(vlan.devices) == 3
        assert set(vlan.devices) == {"sw-001", "sw-002", "sw-003"}
    
    def test_vlan_device_trimming(self):
        """Test that device IDs in VLAN are trimmed."""
        vlan = VLAN(
            id=100,
            name="Test",
            devices=["  sw-001  ", "sw-002", "  ", "sw-003"]
        )
        
        # Should trim and remove empty devices
        assert set(vlan.devices) == {"sw-001", "sw-002", "sw-003"}
    
    def test_vlan_methods(self):
        """Test VLAN utility methods."""
        vlan = VLAN(
            id=100,
            name="Test",
            devices=["sw-001", "sw-002", "sw-003"]
        )
        
        # Test get_device_set
        device_set = vlan.get_device_set()
        assert device_set == {"sw-001", "sw-002", "sw-003"}
        
        # Test has_device
        assert vlan.has_device("sw-001") is True
        assert vlan.has_device("sw-004") is False
        
        # Test add_device
        vlan.add_device("sw-004")
        assert "sw-004" in vlan.devices
        
        # Adding duplicate should not change anything
        original_count = len(vlan.devices)
        vlan.add_device("sw-001")
        assert len(vlan.devices) == original_count
        
        # Test remove_device
        assert vlan.remove_device("sw-004") is True
        assert "sw-004" not in vlan.devices
        assert vlan.remove_device("sw-999") is False


class TestNetworkTopology:
    """Test cases for NetworkTopology model."""
    
    def test_valid_topology_creation(self):
        """Test creating a valid network topology."""
        devices = [
            Device(id="sw-001", type=DeviceType.SWITCH, role=DeviceRole.CORE, location="dc"),
            Device(id="sw-002", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="floor1")
        ]
        
        links = [
            Link(source="sw-001", target="sw-002", type=LinkType.ETHERNET, speed="10G")
        ]
        
        vlans = [
            VLAN(id=100, name="Corporate", devices=["sw-001", "sw-002"])
        ]
        
        topology = NetworkTopology(devices=devices, links=links, vlans=vlans)
        
        assert len(topology.devices) == 2
        assert len(topology.links) == 1
        assert len(topology.vlans) == 1
    
    def test_duplicate_device_validation(self):
        """Test that duplicate device IDs are rejected."""
        devices = [
            Device(id="sw-001", type=DeviceType.SWITCH, role=DeviceRole.CORE, location="dc"),
            Device(id="sw-001", type=DeviceType.ROUTER, role=DeviceRole.ACCESS, location="floor1")
        ]
        
        with pytest.raises(ValidationError, match="Duplicate device IDs"):
            NetworkTopology(devices=devices, links=[], vlans=[])
    
    def test_duplicate_vlan_validation(self):
        """Test that duplicate VLAN IDs are rejected."""
        vlans = [
            VLAN(id=100, name="VLAN1", devices=[]),
            VLAN(id=100, name="VLAN2", devices=[])
        ]
        
        with pytest.raises(ValidationError, match="Duplicate VLAN IDs"):
            NetworkTopology(devices=[], links=[], vlans=vlans)
    
    def test_topology_methods(self):
        """Test NetworkTopology utility methods."""
        devices = [
            Device(id="sw-001", type=DeviceType.SWITCH, role=DeviceRole.CORE, location="dc"),
            Device(id="sw-002", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="floor1")
        ]
        
        links = [
            Link(source="sw-001", target="sw-002", type=LinkType.ETHERNET, speed="10G")
        ]
        
        vlans = [
            VLAN(id=100, name="Corporate", devices=["sw-001", "sw-002"])
        ]
        
        topology = NetworkTopology(devices=devices, links=links, vlans=vlans)
        
        # Test get_device_by_id
        device = topology.get_device_by_id("sw-001")
        assert device is not None
        assert device.id == "sw-001"
        assert topology.get_device_by_id("nonexistent") is None
        
        # Test get_vlan_by_id
        vlan = topology.get_vlan_by_id(100)
        assert vlan is not None
        assert vlan.id == 100
        assert topology.get_vlan_by_id(999) is None
        
        # Test get_device_links
        device_links = topology.get_device_links("sw-001")
        assert len(device_links) == 1
        assert device_links[0].source == "sw-001" or device_links[0].target == "sw-001"
        
        # Test get_device_neighbors
        neighbors = topology.get_device_neighbors("sw-001")
        assert neighbors == ["sw-002"]
        
        neighbors_empty = topology.get_device_neighbors("nonexistent")
        assert neighbors_empty == []
    
    def test_topology_validation(self):
        """Test topology validation method."""
        devices = [
            Device(id="sw-001", type=DeviceType.SWITCH, role=DeviceRole.CORE, location="dc"),
            Device(id="sw-002", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="floor1")
        ]
        
        # Valid topology
        links = [
            Link(source="sw-001", target="sw-002", type=LinkType.ETHERNET, speed="10G")
        ]
        
        vlans = [
            VLAN(id=100, name="Corporate", devices=["sw-001", "sw-002"])
        ]
        
        topology = NetworkTopology(devices=devices, links=links, vlans=vlans)
        errors = topology.validate_topology()
        assert len(errors) == 0
        
        # Invalid topology - link references non-existent device
        invalid_links = [
            Link(source="sw-001", target="nonexistent", type=LinkType.ETHERNET, speed="10G")
        ]
        
        invalid_topology = NetworkTopology(devices=devices, links=invalid_links, vlans=[])
        errors = invalid_topology.validate_topology()
        assert len(errors) > 0
        assert any("non-existent" in error.lower() for error in errors)
        
        # Invalid topology - VLAN references non-existent device
        invalid_vlans = [
            VLAN(id=100, name="Test", devices=["nonexistent"])
        ]
        
        invalid_topology2 = NetworkTopology(devices=devices, links=[], vlans=invalid_vlans)
        errors = invalid_topology2.validate_topology()
        assert len(errors) > 0
        assert any("non-existent" in error.lower() for error in errors)
    
    def test_topology_statistics(self):
        """Test topology statistics generation."""
        devices = [
            Device(id="sw-001", type=DeviceType.SWITCH, role=DeviceRole.CORE, location="dc"),
            Device(id="sw-002", type=DeviceType.SWITCH, role=DeviceRole.ACCESS, location="floor1"),
            Device(id="r-001", type=DeviceType.ROUTER, role=DeviceRole.EDGE, location="dc")
        ]
        
        links = [
            Link(source="sw-001", target="sw-002", type=LinkType.ETHERNET, speed="10G"),
            Link(source="sw-001", target="r-001", type=LinkType.ETHERNET, speed="10G")
        ]
        
        vlans = [
            VLAN(id=100, name="Corporate", devices=["sw-001", "sw-002"]),
            VLAN(id=200, name="Guest", devices=["sw-001"])
        ]
        
        topology = NetworkTopology(devices=devices, links=links, vlans=vlans)
        stats = topology.get_statistics()
        
        assert stats["total_devices"] == 3
        assert stats["total_links"] == 2
        assert stats["total_vlans"] == 2
        assert stats["device_types"][DeviceType.SWITCH.value] == 2
        assert stats["device_types"][DeviceType.ROUTER.value] == 1
        assert stats["device_roles"][DeviceRole.CORE.value] == 1
        assert stats["device_roles"][DeviceRole.ACCESS.value] == 1
        assert stats["device_roles"][DeviceRole.EDGE.value] == 1
        
        # Average links per device = (2 links * 2 endpoints) / 3 devices
        expected_avg = (2 * 2) / 3
        assert abs(stats["average_links_per_device"] - expected_avg) < 0.001


class TestEnums:
    """Test cases for enum values."""
    
    def test_device_type_enum(self):
        """Test DeviceType enum values."""
        assert DeviceType.SWITCH.value == "switch"
        assert DeviceType.ROUTER.value == "router"
        assert DeviceType.CONTROLLER.value == "controller"
        assert DeviceType.ACCESS_POINT.value == "access-point"
    
    def test_device_role_enum(self):
        """Test DeviceRole enum values."""
        assert DeviceRole.CORE.value == "core"
        assert DeviceRole.DISTRIBUTION.value == "distribution"
        assert DeviceRole.ACCESS.value == "access"
        assert DeviceRole.EDGE.value == "edge"
        assert DeviceRole.WIFI.value == "wifi"
        assert DeviceRole.STORAGE.value == "storage"
    
    def test_link_type_enum(self):
        """Test LinkType enum values."""
        assert LinkType.ETHERNET.value == "ethernet"
        assert LinkType.FIBER.value == "fiber"
        assert LinkType.WIRELESS.value == "wireless"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
