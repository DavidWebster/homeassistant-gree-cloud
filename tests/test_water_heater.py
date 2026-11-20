"""Hot water heat pump: what a service call sends to the unit.

The recorded unit is off, tank at 53 °C, target 55 °C.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from .common import call
from .fake_cloud import FakeUnit

HEATER = "water_heater.water_heater"


@pytest.fixture
async def unit(cloud, setup_integration) -> FakeUnit:
    unit = cloud.add("hwhp")
    await setup_integration()
    unit.forget()
    return unit


async def test_it_is_a_water_heater_not_an_air_conditioner(
    hass: HomeAssistant, cloud, unit: FakeUnit
) -> None:
    """A unit that reports a tank temperature gets no climate entity or AC switches.

    Fork: the only switches are the hot water schedule, eco, holiday and
    disinfect switches.
    """
    assert hass.states.async_entity_ids("climate") == []
    assert sorted(hass.states.async_entity_ids("switch")) == [
        "switch.water_heater_disinfect_cycle",
        "switch.water_heater_eco_1",
        "switch.water_heater_eco_2",
        "switch.water_heater_holiday_mode",
        "switch.water_heater_schedule_1",
        "switch.water_heater_schedule_2",
    ]
    assert hass.states.async_entity_ids("water_heater") == [HEATER]


async def test_firmware_version_is_a_string(
    hass: HomeAssistant, cloud, setup_integration, caplog: pytest.LogCaptureFixture
) -> None:
    """Fork: ``ver`` arrives as a number; Home Assistant 2026.12 rejects a non-string sw_version."""
    cloud.add("hwhp")
    await setup_integration()
    assert "as sw_version" not in caplog.text


async def test_target_temperature(hass: HomeAssistant, cloud, unit: FakeUnit, poll) -> None:
    """Beyond the 30 °C an air conditioner stops at."""
    await call(hass, "water_heater", "set_temperature", HEATER, temperature=60)
    assert unit.commands == [{"SetTemInt": 60}, {"SetTemDec": 0}]
    assert hass.states.get(HEATER).attributes["temperature"] == 60
    await poll()
    assert hass.states.get(HEATER).attributes["temperature"] == 60


@pytest.mark.parametrize(
    ("mode", "commands"),
    [
        ("heat_pump", [{"Wmod": 0}, {"Pow": 1}]),
        ("performance", [{"Wmod": 2}, {"Pow": 1}]),
    ],
)
async def test_operation_mode(
    hass: HomeAssistant, cloud, unit: FakeUnit, poll, mode: str, commands: list[dict[str, Any]]
) -> None:
    await call(hass, "water_heater", "set_operation_mode", HEATER, operation_mode=mode)
    assert unit.commands == commands
    assert hass.states.get(HEATER).state == mode
    await poll()
    assert hass.states.get(HEATER).state == mode


async def test_switching_off(hass: HomeAssistant, cloud, setup_integration) -> None:
    unit = cloud.add("hwhp", state={"Pow": 1})
    await setup_integration()
    assert hass.states.get(HEATER).state == "heat_pump"

    unit.forget()
    await call(hass, "water_heater", "set_operation_mode", HEATER, operation_mode="off")
    assert unit.commands == [{"Pow": 0}]
    assert hass.states.get(HEATER).state == "off"


async def test_readings_follow_the_unit(hass: HomeAssistant, cloud, unit: FakeUnit, poll) -> None:
    """Temperatures arrive with an offset of 100."""
    unit.state.update(WatTmp=161, Wstate=1)
    await poll()
    shown = hass.states.get(HEATER)
    assert shown.attributes["current_temperature"] == 61
    assert shown.attributes["heating_status"] == "heating"
