"""Support for Gree Cloud sensor entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from greeclimate.device import Device

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DISPATCH_DEVICE_DISCOVERED,
    ENERGY_SCALE,
    HWHP_PROP_CAPACITY,
    HWHP_PROP_HOLIDAY_CYCLE,
    HWHP_PROP_HOLIDAY_REMAIN,
    HWHP_TEMP_ENCODING_OFFSET,
    PROP_COMPRESSOR_FREQ,
    PROP_ENERGY_TOTAL,
    PROP_HUMIDITY,
)
from .coordinator import (
    CloudDeviceDataUpdateCoordinator,
    GreeCloudConfigEntry,
    is_hwhp_device,
)
from .entity import GreeCloudEntity


@dataclass(kw_only=True, frozen=True)
class GreeCloudSensorEntityDescription(SensorEntityDescription):
    """Describes a Gree Cloud sensor entity."""

    value_fn: Callable[[Device], float | None]
    exists_fn: Callable[[Device], bool]


def _energy_total(device: Device) -> float | None:
    """Return cumulative energy in kWh, or None if the device did not report it."""
    raw = device.raw_properties.get(PROP_ENERGY_TOTAL)
    if raw is None:
        return None
    return round(raw * ENERGY_SCALE, 1)


def _has_energy_total(device: Device) -> bool:
    """Return True if the device reports the energy counter.

    Devices silently omit properties they do not support, so a missing key -
    rather than a zero value - is what marks the counter as unavailable. A
    freshly installed unit legitimately reports 0.
    """
    return device.raw_properties.get(PROP_ENERGY_TOTAL) is not None


def _compressor_frequency(device: Device) -> float | None:
    """Return compressor frequency in Hz."""
    return device.raw_properties.get(PROP_COMPRESSOR_FREQ)


def _has_compressor_frequency(device: Device) -> bool:
    """Return True if the device reports compressor frequency.

    Zero is a valid reading - it means the compressor is idle - so presence of
    the key is the only reliable test.
    """
    return device.raw_properties.get(PROP_COMPRESSOR_FREQ) is not None


def _humidity(device: Device) -> float | None:
    """Return relative humidity in percent."""
    return device.raw_properties.get(PROP_HUMIDITY)


def _has_humidity(device: Device) -> bool:
    """Return True if the device has a usable humidity reading.

    Unlike the other properties, units without a humidity sensor report a flat
    0 rather than omitting the key, and 0 %RH is not a plausible indoor value.
    Readings outside 1-100 are therefore treated as "no sensor fitted".
    """
    raw = device.raw_properties.get(PROP_HUMIDITY)
    return isinstance(raw, (int, float)) and 0 < raw <= 100


def _hwhp_capacity(device: Device) -> float | None:
    """Return the hot water capacity/availability gauge, as a percentage.

    Uses the same +100 raw encoding as temperature. Not clamped to 0-100 by
    the device - a satisfied tank has been observed reporting 120 (20% in
    the EWPE app), so this is passed through as-is rather than clamped.
    """
    raw = device.raw_properties.get(HWHP_PROP_CAPACITY)
    if raw is None:
        return None
    return raw - HWHP_TEMP_ENCODING_OFFSET


def _has_hwhp_capacity(device: Device) -> bool:
    """Return True if the device reports the hot water capacity gauge."""
    return device.raw_properties.get(HWHP_PROP_CAPACITY) is not None


def _hwhp_holiday_cycle(device: Device) -> float | None:
    """Return the configured holiday mode duration.

    Interpretation inferred from a single live capture (HolidayCycle=7) and
    not confirmed by Gree documentation; assumed to be whole days, matching
    the observed value and the "holiday" framing.
    """
    return device.raw_properties.get(HWHP_PROP_HOLIDAY_CYCLE)


def _has_hwhp_holiday_cycle(device: Device) -> bool:
    """Return True if the device reports the holiday cycle property."""
    return device.raw_properties.get(HWHP_PROP_HOLIDAY_CYCLE) is not None


def _hwhp_holiday_remain(device: Device) -> float | None:
    """Return the days remaining in an active holiday period.

    Interpretation inferred (not confirmed by Gree documentation); observed
    as 0 while HolidaySwitch was off, consistent with but not proof of this
    reading.
    """
    return device.raw_properties.get(HWHP_PROP_HOLIDAY_REMAIN)


def _has_hwhp_holiday_remain(device: Device) -> bool:
    """Return True if the device reports the holiday remaining property."""
    return device.raw_properties.get(HWHP_PROP_HOLIDAY_REMAIN) is not None


GREE_CLOUD_HWHP_SENSORS: tuple[GreeCloudSensorEntityDescription, ...] = (
    GreeCloudSensorEntityDescription(
        key="Hot Water Capacity",
        translation_key="hwhp_capacity",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_hwhp_capacity,
        exists_fn=_has_hwhp_capacity,
    ),
    GreeCloudSensorEntityDescription(
        key="Holiday Cycle",
        translation_key="hwhp_holiday_cycle",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=_hwhp_holiday_cycle,
        exists_fn=_has_hwhp_holiday_cycle,
    ),
    GreeCloudSensorEntityDescription(
        key="Holiday Remaining",
        translation_key="hwhp_holiday_remain",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=_hwhp_holiday_remain,
        exists_fn=_has_hwhp_holiday_remain,
    ),
)


GREE_CLOUD_SENSORS: tuple[GreeCloudSensorEntityDescription, ...] = (
    GreeCloudSensorEntityDescription(
        key="Energy",
        translation_key="energy_total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=_energy_total,
        exists_fn=_has_energy_total,
    ),
    GreeCloudSensorEntityDescription(
        key="Humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_humidity,
        exists_fn=_has_humidity,
    ),
    GreeCloudSensorEntityDescription(
        key="Compressor Frequency",
        translation_key="compressor_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_compressor_frequency,
        exists_fn=_has_compressor_frequency,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GreeCloudConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Gree Cloud sensors from a config entry."""

    @callback
    def init_device(coordinator: CloudDeviceDataUpdateCoordinator) -> None:
        """Register the device."""
        # Hot water heat pumps report consumption under a different key and
        # get their own sensor set (they have no compressor frequency or
        # humidity sensor, but do have a hot water capacity gauge the AC
        # sensor set has no equivalent for).
        descriptions = (
            GREE_CLOUD_HWHP_SENSORS if is_hwhp_device(coordinator) else GREE_CLOUD_SENSORS
        )
        async_add_entities(
            GreeCloudSensor(coordinator=coordinator, description=description)
            for description in descriptions
            if description.exists_fn(coordinator.device)
        )

    for coordinator in entry.runtime_data.coordinators:
        init_device(coordinator)

    entry.async_on_unload(
        async_dispatcher_connect(hass, DISPATCH_DEVICE_DISCOVERED, init_device)
    )


class GreeCloudSensor(GreeCloudEntity, SensorEntity):
    """Generic Gree Cloud sensor entity."""

    entity_description: GreeCloudSensorEntityDescription

    def __init__(
        self,
        coordinator: CloudDeviceDataUpdateCoordinator,
        description: GreeCloudSensorEntityDescription,
    ) -> None:
        """Initialize the Gree Cloud sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_info.mac}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator.device)
