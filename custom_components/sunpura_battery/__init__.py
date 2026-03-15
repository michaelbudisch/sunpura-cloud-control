"""The Detailed Hello World Push integration."""

from __future__ import annotations

import logging

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from .hub import MyIntegrationHub
from .const import (
    BASE_URL,
    CONF_POLL_INTERVAL_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DOMAIN,
)  # pylint:disable=unused-import

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER, Platform.SELECT]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry):
        """Set up the sensor platform from a config entry."""
        try:
            _LOGGER.info("Starting Sunpura Battery integration setup")
            
            # Initialize your integration here (e.g., fetch data)
            hass.data.setdefault(DOMAIN, {})
            
            _LOGGER.debug("Creating hub instance")
            poll_interval_seconds = int(
                entry.options.get(
                    CONF_POLL_INTERVAL_SECONDS,
                    entry.data.get(
                        CONF_POLL_INTERVAL_SECONDS,
                        DEFAULT_POLL_INTERVAL_SECONDS,
                    ),
                )
            )
            hub = MyIntegrationHub(
                hass,
                entry.data["username"],
                entry.data["password"],
                entry.data["selected_device_id"],
                entry.data.get("base_url", BASE_URL),
                poll_interval_seconds=poll_interval_seconds,
            )
            hass.data[DOMAIN]['hub'] = hub
            hass.data[DOMAIN]['cur_plant_name']= entry.data["selected_device_name"]
            entry.async_on_unload(entry.add_update_listener(_async_update_listener))
            
            _LOGGER.debug("Importing DeviceEntityManager")
            # 创建设备实体管理器
            from .device_entity_manager import DeviceEntityManager
            device_manager = DeviceEntityManager(hass, hub)
            hass.data[DOMAIN]['device_manager'] = device_manager
            
            _LOGGER.debug("Starting API calls")
            # 获取设备数据并创建实体
            await hub.login()
            _LOGGER.debug("Login completed")
            
            await hub.getPlantVos()
            _LOGGER.debug("getPlantVos completed")
            
            await hub.get_home_control_devices()
            _LOGGER.debug("get_home_control_devices completed")
            
            try:
                device_data = await hub.getHomeCountData()
                _LOGGER.debug(f"getHomeCountData completed: {device_data is not None}")
                
                if device_data:
                    _LOGGER.info(f"设备数据: {device_data}")
                    entities = await device_manager.create_entities_from_data(device_data)
                    _LOGGER.info(f"创建的实体: {entities}")
                    _LOGGER.info(f"创建的设备: {device_manager.devices}")

                    if entities:
                        _LOGGER.debug("Setting up platforms")
                        # for platform in PLATFORMS:
                        await hass.async_create_task(
                            hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
                        )
                        _LOGGER.debug("Platforms setup completed")
                else:
                    _LOGGER.error("Failed to get device data from API")
                    return False
            except Exception as e:
                _LOGGER.error(f"Error during device data setup: {e}", exc_info=True)
                return False
            
            _LOGGER.debug("Starting polling")
            await hub.start_polling()
            await hub.start_schedule_login()
            
            _LOGGER.info("Sunpura Battery integration setup completed successfully")
        except Exception as e:
            _LOGGER.error(f"Fatal error during integration setup: {e}", exc_info=True)
            return False



        """注册服务   先这么写，后期再优化"""
        #电站切换api
        async def async_switch_plant_service(call):
            """服务处理函数：调用服务"""
            plant_id =call.data['plant_id']
            device_sn = call.data['device_sn']
            # _LOGGER.info(f"plant_id: {plant_id}")
            hub = hass.data[DOMAIN]['hub']
            hub.senceId=str(plant_id)
            if device_sn is not None and device_sn != '':
                hub.cur_ctl_devices=device_sn
            hass.data[DOMAIN]['cur_plant_name']=str(plant_id)
            await hub.async_update_data()
        # 注册电站服务
        hass.services.async_register(
            DOMAIN,
            "service_switch_plant",
            async_switch_plant_service,
        )

        #注册获取电站每日统计数据
        async def async_get_energy_data_day(call):
            await hub.get_energy_data_day(hub.senceId)

        hass.services.async_register(
            DOMAIN,
            "service_get_energy_data_day",
            async_get_energy_data_day,
        )

        # 注册获取电站每日统计数据
        async def async_get_energy_data_month(call):
            await hub.get_energy_data_month(hub.senceId)

        hass.services.async_register(
            DOMAIN,
            "service_get_energy_data_month",
            async_get_energy_data_month,
        )

        # 注册获取电站每日统计数据
        async def async_get_energy_data_year(call):
            await hub.get_energy_data_year(hub.senceId)

        hass.services.async_register(
            DOMAIN,
            "service_get_energy_data_year",
            async_get_energy_data_year,
        )

        # 注册获取电站每日统计数据
        async def async_get_energy_data_total(call):
            await hub.get_energy_data_total(hub.senceId)

        hass.services.async_register(
            DOMAIN,
            "service_get_energy_data_total",
            async_get_energy_data_total,
        )

        # 立即刷新主页数据
        async def refresh_data(call):
            await hub.async_update_data()

        hass.services.async_register(
            DOMAIN,
            "service_refresh_data",
            refresh_data,
        )

        return True



async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
        entry.async_on_unload(hass.data[DOMAIN]['hub'].stop_polling)
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if unload_ok:
            hass.data[DOMAIN].pop(entry.entry_id)
        return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Reload integration when options change."""
        await hass.config_entries.async_reload(entry.entry_id)
