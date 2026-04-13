"""Services for Goodwe integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import (
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    ATTR_PARAMETER,
    ATTR_VALUE,
    DOMAIN,
    SERVICE_GET_PARAMETER,
    SERVICE_SET_PARAMETER,
)

_LOGGER = logging.getLogger(__name__)

# Allowlist of inverter parameters that may be written via the set_parameter service.
# Only operational / scheduling settings are included. Hardware-level settings
# (communication address, baud rate, battery voltage limits, grid safety parameters,
# remote shutdown, etc.) are intentionally excluded to prevent misconfiguration or damage.
SAFE_WRITABLE_PARAMETERS: frozenset[str] = frozenset(
    {
        # Grid export control
        "grid_export",               # Enable/disable the grid export power limit
        "grid_export_limit",         # Export limit value (W or %)
        "meter_target_power_offset", # Offset applied to the meter target power
        # Operation / work mode
        "work_mode",
        # EMS (energy management system) mode and target power
        "ems_mode",
        "ems_power_limit",
        # Eco Mode / Time-of-Use schedule groups (all four, V1 and V2 layouts)
        "eco_mode_1",
        "eco_mode_1_switch",
        "eco_mode_2",
        "eco_mode_2_switch",
        "eco_mode_3",
        "eco_mode_3_switch",
        "eco_mode_4",
        "eco_mode_4_switch",
        "eco_mode_enable",           # Global eco mode on/off switch
        # Peak shaving
        "peak_shaving_mode",
        "peak_shaving_power_limit",
        "peak_shaving_soc",
        # Battery SoC / depth-of-discharge operational limits
        "battery_discharge_depth",          # On-grid DoD limit (%)
        "battery_discharge_depth_offline",  # Off-grid / backup DoD limit (%)
        "battery_soc_protection",           # Minimum SoC protection threshold
        "soc_upper_limit",                  # Maximum charge SoC (%)
        # Fast charging
        "fast_charging",
        "fast_charging_soc",
        "fast_charging_power",
        # Backup / UPS supply
        "backup_supply",       # Enable backup output
        "backup_mode_enable",  # Backup mode switch (fw22+)
        # Load control relay
        "load_control_switch",
        "load_control_soc",
        "load_control_mode",
        # Misc operational
        "shadow_scan",           # Enable PV shadow-scan optimisation
        "dod_holding",           # DoD holding during peak shaving
        "smart_charging_enable", # Smart charging mode switch
        "max_charge_power",      # Maximum charge power (W)
        # ES/BP-series operational parameters
        "off-grid_charge",    # ES: enable off-grid charging
        "bp_off_grid_charge", # ES BP variant
        "bp_pv_discharge",    # ES BP variant: PV-priority discharge
    }
)

SERVICE_GET_PARAMETER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): str,
        vol.Required(ATTR_PARAMETER): str,
        vol.Required(ATTR_ENTITY_ID): str,
    }
)

SERVICE_SET_PARAMETER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): str,
        vol.Required(ATTR_PARAMETER): vol.In(SAFE_WRITABLE_PARAMETERS),
        vol.Required(ATTR_VALUE): vol.Any(str, int, bool),
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Goodwe integration."""

    if hass.services.has_service(DOMAIN, SERVICE_GET_PARAMETER):
        return

    async def _get_inverter_by_device_id(hass: HomeAssistant, device_id: str):
        """Return a inverter instance given a device_id."""
        device = dr.async_get(hass).async_get(device_id)
        if device is None:
            raise ValueError(f"Device {device_id} not found in device registry")
        for runtime_data in hass.data[DOMAIN].values():
            if device.identifiers == runtime_data.device_info.get("identifiers"):
                return runtime_data.inverter
        raise ValueError(f"Inverter for device id {device_id} not found")

    async def async_get_parameter(call):
        """Service for setting inverter parameter."""
        device_id = call.data[ATTR_DEVICE_ID]
        parameter = call.data[ATTR_PARAMETER]
        entity_id = call.data[ATTR_ENTITY_ID]

        _LOGGER.debug("Reading inverter parameter '%s'", parameter)
        inverter = await _get_inverter_by_device_id(hass, device_id)
        value = await inverter.read_setting(parameter)

        entity = er.async_get(hass).async_get(entity_id)
        await hass.services.async_call(
            entity.domain,
            "set_value",
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
            blocking=True,
        )

    async def async_set_parameter(call):
        """Service for setting inverter parameter."""
        device_id = call.data[ATTR_DEVICE_ID]
        parameter = call.data[ATTR_PARAMETER]
        value = call.data[ATTR_VALUE]

        _LOGGER.debug("Setting inverter parameter '%s' to '%s'", parameter, value)
        inverter = await _get_inverter_by_device_id(hass, device_id)
        await inverter.write_setting(parameter, value)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PARAMETER,
        async_get_parameter,
        schema=SERVICE_GET_PARAMETER_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PARAMETER,
        async_set_parameter,
        schema=SERVICE_SET_PARAMETER_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services for Goodwe integration."""

    if hass.services.has_service(DOMAIN, SERVICE_GET_PARAMETER):
        hass.services.async_remove(DOMAIN, SERVICE_GET_PARAMETER)

    if hass.services.has_service(DOMAIN, SERVICE_SET_PARAMETER):
        hass.services.async_remove(DOMAIN, SERVICE_SET_PARAMETER)
