"""Support for Gree Cloud HWHP schedule start/end time entities."""

from __future__ import annotations

from dataclasses import dataclass
import datetime

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DISPATCH_DEVICE_DISCOVERED,
    HWHP_PROP_WTMR1_END_HR,
    HWHP_PROP_WTMR1_END_MIN,
    HWHP_PROP_WTMR1_START_HR,
    HWHP_PROP_WTMR1_START_MIN,
    HWHP_PROP_WTMR2_END_HR,
    HWHP_PROP_WTMR2_END_MIN,
    HWHP_PROP_WTMR2_START_HR,
    HWHP_PROP_WTMR2_START_MIN,
)
from .coordinator import CloudDeviceDataUpdateCoordinator, GreeCloudConfigEntry, is_hwhp_device
from .entity import GreeCloudEntity


@dataclass(kw_only=True, frozen=True)
class GreeCloudTimeEntityDescription(TimeEntityDescription):
    """Describes a Gree Cloud HWHP schedule time entity.

    Each schedule window is stored as separate hour/minute integer
    properties (there is no single combined "time" property on the wire),
    so this description names both halves.
    """

    hour_prop: str
    minute_prop: str


GREE_CLOUD_HWHP_TIMES: tuple[GreeCloudTimeEntityDescription, ...] = (
    GreeCloudTimeEntityDescription(
        key="Schedule 1 Start",
        translation_key="hwhp_schedule_1_start",
        hour_prop=HWHP_PROP_WTMR1_START_HR,
        minute_prop=HWHP_PROP_WTMR1_START_MIN,
    ),
    GreeCloudTimeEntityDescription(
        key="Schedule 1 End",
        translation_key="hwhp_schedule_1_end",
        hour_prop=HWHP_PROP_WTMR1_END_HR,
        minute_prop=HWHP_PROP_WTMR1_END_MIN,
    ),
    GreeCloudTimeEntityDescription(
        key="Schedule 2 Start",
        translation_key="hwhp_schedule_2_start",
        hour_prop=HWHP_PROP_WTMR2_START_HR,
        minute_prop=HWHP_PROP_WTMR2_START_MIN,
    ),
    GreeCloudTimeEntityDescription(
        key="Schedule 2 End",
        translation_key="hwhp_schedule_2_end",
        hour_prop=HWHP_PROP_WTMR2_END_HR,
        minute_prop=HWHP_PROP_WTMR2_END_MIN,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GreeCloudConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gree Cloud HWHP schedule time entities from a config entry."""

    @callback
    def init_device(coordinator: CloudDeviceDataUpdateCoordinator) -> None:
        """Register the device if it is an HWHP (schedules are HWHP-only)."""
        if not is_hwhp_device(coordinator):
            return
        async_add_entities(
            GreeCloudTime(coordinator=coordinator, description=description)
            for description in GREE_CLOUD_HWHP_TIMES
        )

    for coordinator in entry.runtime_data.coordinators:
        init_device(coordinator)

    entry.async_on_unload(
        async_dispatcher_connect(hass, DISPATCH_DEVICE_DISCOVERED, init_device)
    )


class GreeCloudTime(GreeCloudEntity, TimeEntity):
    """Start/end time for one Gree Cloud HWHP schedule window."""

    entity_description: GreeCloudTimeEntityDescription

    def __init__(
        self,
        coordinator: CloudDeviceDataUpdateCoordinator,
        description: GreeCloudTimeEntityDescription,
    ) -> None:
        """Initialize the Gree Cloud HWHP time entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_info.mac}_{description.key}"

    @property
    def native_value(self) -> datetime.time | None:
        """Return the current start/end time for this schedule window."""
        props = self.coordinator.device.raw_properties
        hour = props.get(self.entity_description.hour_prop)
        minute = props.get(self.entity_description.minute_prop)
        if hour is None or minute is None:
            return None
        return datetime.time(hour=hour, minute=minute)

    async def async_set_value(self, value: datetime.time) -> None:
        """Set a new start/end time for this schedule window."""
        device = self.coordinator.device
        hour_prop = self.entity_description.hour_prop
        minute_prop = self.entity_description.minute_prop
        device.raw_properties[hour_prop] = value.hour
        device.raw_properties[minute_prop] = value.minute
        for prop in (hour_prop, minute_prop):
            if prop not in device._dirty:
                device._dirty.append(prop)
        await self.coordinator.push_state_update()
        self.async_write_ha_state()
