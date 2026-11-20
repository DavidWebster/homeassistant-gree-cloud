"""Base entity for Gree Cloud devices."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo as HADeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROP_FIRMWARE_VERSION
from .coordinator import CloudDeviceDataUpdateCoordinator


class GreeCloudEntity(CoordinatorEntity[CloudDeviceDataUpdateCoordinator]):
    """Base class for Gree Cloud entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CloudDeviceDataUpdateCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        version = coordinator.device.raw_properties.get(PROP_FIRMWARE_VERSION)
        self._attr_device_info = HADeviceInfo(
            identifiers={(DOMAIN, coordinator.device.device_info.mac)},
            name=coordinator.device.device_info.name,
            manufacturer="Gree",
            model=("Air-to-water heat pump" if coordinator.device_kind == "heatpump"
                   else coordinator.device.hid or "Unknown Model"),
            sw_version=None if version is None else str(version),
        )
