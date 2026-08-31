"""Support for Gree Cloud HWHP disinfect cycle number entities."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DISPATCH_DEVICE_DISCOVERED,
    HWHP_PROP_DISINFECT_CYCLE,
    HWHP_PROP_DISINFECT_HOUR,
)
from .coordinator import CloudDeviceDataUpdateCoordinator, GreeCloudConfigEntry, is_hwhp_device
from .entity import GreeCloudEntity


@dataclass(kw_only=True, frozen=True)
class GreeCloudNumberEntityDescription(NumberEntityDescription):
    """Describes a Gree Cloud HWHP number entity.

    Each entity is backed by a single raw integer property on the wire (unlike
    the schedule times in time.py, which are split across separate hour and
    minute properties).
    """

    raw_prop: str


GREE_CLOUD_HWHP_NUMBERS: tuple[GreeCloudNumberEntityDescription, ...] = (
    GreeCloudNumberEntityDescription(
        key="Disinfect Hour",
        translation_key="hwhp_disinfect_hour",
        raw_prop=HWHP_PROP_DISINFECT_HOUR,
        native_min_value=0,
        native_max_value=23,
        native_step=1,
    ),
    GreeCloudNumberEntityDescription(
        key="Disinfect Cycle",
        translation_key="hwhp_disinfect_cycle",
        raw_prop=HWHP_PROP_DISINFECT_CYCLE,
        # Days between anti-legionella disinfect cycles. Only one observed
        # value (7) is confirmed; the device's actual valid range is not
        # documented. 1-30 is a permissive guess wide enough to admit common
        # real-world schedules (daily through monthly) without guessing a
        # tight range that could reject a valid device configuration.
        native_min_value=1,
        native_max_value=30,
        native_step=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GreeCloudConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gree Cloud HWHP number entities from a config entry."""

    @callback
    def init_device(coordinator: CloudDeviceDataUpdateCoordinator) -> None:
        """Register the device if it is an HWHP (disinfect cycle is HWHP-only)."""
        if not is_hwhp_device(coordinator):
            return
        async_add_entities(
            GreeCloudNumber(coordinator=coordinator, description=description)
            for description in GREE_CLOUD_HWHP_NUMBERS
        )

    for coordinator in entry.runtime_data.coordinators:
        init_device(coordinator)

    entry.async_on_unload(
        async_dispatcher_connect(hass, DISPATCH_DEVICE_DISCOVERED, init_device)
    )


class GreeCloudNumber(GreeCloudEntity, NumberEntity):
    """Generic Gree Cloud HWHP number entity backed by a raw integer property."""

    entity_description: GreeCloudNumberEntityDescription

    def __init__(
        self,
        coordinator: CloudDeviceDataUpdateCoordinator,
        description: GreeCloudNumberEntityDescription,
    ) -> None:
        """Initialize the Gree Cloud HWHP number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_info.mac}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the current value of the raw property."""
        return self.coordinator.device.raw_properties.get(self.entity_description.raw_prop)

    async def async_set_native_value(self, value: float) -> None:
        """Set a new value for the raw property."""
        device = self.coordinator.device
        prop = self.entity_description.raw_prop
        device.raw_properties[prop] = int(value)
        if prop not in device._dirty:
            device._dirty.append(prop)
        await self.coordinator.push_state_update()
        self.async_write_ha_state()
