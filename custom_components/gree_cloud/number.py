"""Number entities: Versati heat pump setpoints and HWHP disinfect cycle settings.

Heat pump setpoints are exposed only with approved device-specific limits.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DISPATCH_DEVICE_DISCOVERED,
    HWHP_PROP_DISINFECT_CYCLE,
    HWHP_PROP_DISINFECT_HOUR,
)
from .coordinator import (
    CloudDeviceDataUpdateCoordinator,
    GreeCloudConfigEntry,
    is_heatpump_device,
    is_hwhp_device,
)
from .entity import GreeCloudEntity
from .heatpump import COOLING_SETPOINTS, SETPOINTS, setpoint


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
    """Set up Gree Cloud number entities from a config entry."""

    @callback
    def init_device(coordinator: CloudDeviceDataUpdateCoordinator) -> None:
        if is_heatpump_device(coordinator):
            # Do not advertise controls whose write ranges are unverified.
            if coordinator.device_kind != "heatpump":
                return
            entities = []
            policy = coordinator.device.write_policy
            for key in (*SETPOINTS, *COOLING_SETPOINTS):
                if (
                    key in policy.approved
                    and key in policy.limits
                    and setpoint(coordinator.data or {}, key) is not None
                ):
                    entities.append(HeatPumpNumber(coordinator, key))
            async_add_entities(entities)
            return
        if is_hwhp_device(coordinator):
            async_add_entities(
                GreeCloudNumber(coordinator=coordinator, description=description)
                for description in GREE_CLOUD_HWHP_NUMBERS
            )

    for coordinator in entry.runtime_data.coordinators:
        init_device(coordinator)

    entry.async_on_unload(
        async_dispatcher_connect(hass, DISPATCH_DEVICE_DISCOVERED, init_device)
    )


class HeatPumpNumber(GreeCloudEntity, NumberEntity):
    """One atomic setpoint; actual state changes only after confirmed readback."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, key):
        super().__init__(coordinator)
        self.key = key
        self._attr_translation_key = (SETPOINTS | COOLING_SETPOINTS)[key]
        self._attr_unique_id = (
            f"{coordinator.device.device_info.mac}_versati_number_{key}"
        )
        self._attr_native_min_value, self._attr_native_max_value = (
            coordinator.device.write_policy.limits[key]
        )

    @property
    def native_value(self):
        return setpoint(self.coordinator.data or {}, self.key)

    async def async_set_native_value(self, value):
        await self.coordinator.async_heatpump_command(self.key, value)


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
