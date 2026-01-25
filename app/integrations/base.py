"""
Base Integration Adapter Interface
All external integrations (Home Assistant, SmartThings, etc.) must implement this
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DeviceState:
    """Current state of a device"""
    entity_id: str
    name: str
    state: str  # "on", "off", "unavailable", etc.
    attributes: Dict[str, Any]
    last_updated: datetime


@dataclass
class DeviceInfo:
    """Device information"""
    entity_id: str
    name: str
    domain: str  # "switch", "light", "climate", etc.
    platform: str  # "homeassistant", "smartthings", etc.
    capabilities: List[str]


class IntegrationAdapter(ABC):
    """Base class for all external integration adapters"""
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test connection to the integration platform
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    async def discover_devices(self, domain: Optional[str] = None) -> List[DeviceInfo]:
        """
        Discover available devices
        
        Args:
            domain: Optional filter by domain (e.g., "switch", "light")
            
        Returns:
            List of discovered devices
        """
        pass
    
    @abstractmethod
    async def get_device_state(self, entity_id: str) -> Optional[DeviceState]:
        """
        Get current state of a device
        
        Args:
            entity_id: Entity ID (e.g., "switch.miner_power")
            
        Returns:
            DeviceState or None if unavailable
        """
        pass
    
    @abstractmethod
    async def turn_on(self, entity_id: str) -> bool:
        """
        Turn device on
        
        Args:
            entity_id: Entity ID to control
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def turn_off(self, entity_id: str) -> bool:
        """
        Turn device off
        
        Args:
            entity_id: Entity ID to control
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def call_service(
        self, 
        domain: str, 
        service: str, 
        entity_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Call a service on a device
        
        Args:
            domain: Domain (e.g., "switch", "climate")
            service: Service name (e.g., "turn_on", "set_temperature")
            entity_id: Entity ID to control
            data: Optional service data
            
        Returns:
            True if successful
        """
        pass
