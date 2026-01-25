"""
External integrations module - portable to HEMA
Provides interfaces for controlling external smart home devices
"""
from .base import IntegrationAdapter, DeviceInfo, DeviceState
from .homeassistant import HomeAssistantIntegration

__all__ = [
    'IntegrationAdapter',
    'DeviceInfo',
    'DeviceState',
    'HomeAssistantIntegration',
]
