"""Support for Gree Cloud switch entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from greeclimate.device import Device

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DISPATCH_DEVICE_DISCOVERED,
    HWHP_PROP_HOLIDAY_SWITCH,
    HWHP_PROP_SCH1_ENABLE,
    HWHP_PROP_SCH2_ENABLE,
)
from .coordinator import CloudDeviceDataUpdateCoordinator, GreeCloudConfigEntry, is_hwhp_device
from .entity import GreeCloudEntity


@dataclass(kw_only=True, frozen=True)
class GreeCloudSwitchEntityDescription(SwitchEntityDescription):
    """Describes a Gree Cloud switch entity."""

    get_value_fn: Callable[[Device], bool]
    set_value_fn: Callable[[Device, bool], None]


def _set_light(device: Device, value: bool) -> None:
    """Typed helper to set device light property."""
    device.light = value


def _set_quiet(device: Device, value: bool) -> None:
    """Typed helper to set device quiet property."""
    device.quiet = value


def _set_fresh_air(device: Device, value: bool) -> None:
    """Typed helper to set device fresh_air property."""
    device.fresh_air = value


def _set_xfan(device: Device, value: bool) -> None:
    """Typed helper to set device xfan property."""
    device.xfan = value


def _set_anion(device: Device, value: bool) -> None:
    """Typed helper to set device anion property."""
    device.anion = value


def _raw_property_setter(prop: str) -> Callable[[Device, bool], None]:
    """Build a set_value_fn for a raw property with no typed Device setter.

    Mirrors the pattern water_heater.py uses for HWHP temperature: write
    directly into raw_properties and mark it dirty so push_state_update
    picks it up, since these properties (Sch1/Sch2) have no typed setter on
    the base Device class the way light/quiet/xfan etc. do.
    """

    def _set(device: Device, value: bool) -> None:
        device.raw_properties[prop] = int(value)
        if prop not in device._dirty:
            device._dirty.append(prop)

    return _set


def _raw_property_getter(prop: str) -> Callable[[Device], bool]:
    """Build a get_value_fn reading a raw property as a bool."""

    def _get(device: Device) -> bool:
        return bool(device.raw_properties.get(prop))

    return _get


GREE_CLOUD_HWHP_SWITCHES: tuple[GreeCloudSwitchEntityDescription, ...] = (
    GreeCloudSwitchEntityDescription(
        key="Schedule 1",
        translation_key="hwhp_schedule_1",
        get_value_fn=_raw_property_getter(HWHP_PROP_SCH1_ENABLE),
        set_value_fn=_raw_property_setter(HWHP_PROP_SCH1_ENABLE),
    ),
    GreeCloudSwitchEntityDescription(
        key="Schedule 2",
        translation_key="hwhp_schedule_2",
        get_value_fn=_raw_property_getter(HWHP_PROP_SCH2_ENABLE),
        set_value_fn=_raw_property_setter(HWHP_PROP_SCH2_ENABLE),
    ),
    GreeCloudSwitchEntityDescription(
        key="Holiday Mode",
        translation_key="hwhp_holiday_mode",
        get_value_fn=_raw_property_getter(HWHP_PROP_HOLIDAY_SWITCH),
        set_value_fn=_raw_property_setter(HWHP_PROP_HOLIDAY_SWITCH),
    ),
)


GREE_CLOUD_SWITCHES: tuple[GreeCloudSwitchEntityDescription, ...] = (
    GreeCloudSwitchEntityDescription(
        key="Panel Light",
        translation_key="light",
        get_value_fn=lambda d: d.light,
        set_value_fn=_set_light,
    ),
    GreeCloudSwitchEntityDescription(
        key="Quiet",
        translation_key="quiet",
        get_value_fn=lambda d: d.quiet,
        set_value_fn=_set_quiet,
    ),
    GreeCloudSwitchEntityDescription(
        key="Fresh Air",
        translation_key="fresh_air",
        get_value_fn=lambda d: d.fresh_air,
        set_value_fn=_set_fresh_air,
    ),
    GreeCloudSwitchEntityDescription(
        key="XFan",
        translation_key="xfan",
        get_value_fn=lambda d: d.xfan,
        set_value_fn=_set_xfan,
    ),
    GreeCloudSwitchEntityDescription(
        key="Health mode",
        translation_key="health_mode",
        get_value_fn=lambda d: d.anion,
        set_value_fn=_set_anion,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GreeCloudConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Gree Cloud HVAC device from a config entry."""

    @callback
    def init_device(coordinator: CloudDeviceDataUpdateCoordinator) -> None:
        """Register the device."""
        descriptions = (
            GREE_CLOUD_HWHP_SWITCHES if is_hwhp_device(coordinator) else GREE_CLOUD_SWITCHES
        )
        async_add_entities(
            GreeCloudSwitch(coordinator=coordinator, description=description)
            for description in descriptions
        )

    for coordinator in entry.runtime_data.coordinators:
        init_device(coordinator)

    entry.async_on_unload(
        async_dispatcher_connect(hass, DISPATCH_DEVICE_DISCOVERED, init_device)
    )


class GreeCloudSwitch(GreeCloudEntity, SwitchEntity):
    """Generic Gree Cloud switch entity."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    entity_description: GreeCloudSwitchEntityDescription

    def __init__(
        self,
        coordinator: CloudDeviceDataUpdateCoordinator,
        description: GreeCloudSwitchEntityDescription,
    ) -> None:
        """Initialize the Gree Cloud device."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_info.mac}_{description.key}"

    @property
    def is_on(self) -> bool:
        """Return if the state is turned on."""
        return self.entity_description.get_value_fn(self.coordinator.device)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self.entity_description.set_value_fn(self.coordinator.device, True)
        await self.coordinator.push_state_update()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self.entity_description.set_value_fn(self.coordinator.device, False)
        await self.coordinator.push_state_update()
        self.async_write_ha_state()
