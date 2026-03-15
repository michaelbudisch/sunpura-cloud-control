import hashlib
import json
import logging
from datetime import timedelta, datetime
from typing import Any

from aiohttp import ClientError, ContentTypeError

from .const import (
    BASE_URL,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DOMAIN,
    MAX_POLL_INTERVAL_SECONDS,
    MIN_POLL_INTERVAL_SECONDS,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)
IOS_APP_VERSION = "1.260204.2"
IOS_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "Html5Plus/1.0 (Immersed/20) uni-app"
)
SUNPURA_PROJECT_TYPE = "14"
SUNPURA_INTERFACE_TYPE = "2"
LEGACY_BASE_URL = "https://monitor.ai-ec.cloud:8443"


def md5_hash(password: str):
    """Return an MD5 hash for the given password."""
    # 创建一个md5哈希对象
    hasher = hashlib.md5()
    # 更新哈希对象以添加待哈希的密码字符串, 需要先将字符串编码为字节
    hasher.update(password.encode('utf-8'))

    # 获取十六进制表示的哈希值
    return hasher.hexdigest()
langs = {
        'zh-hans': 'zh-CN',
        'zh-hant': 'zh-HK',
        # ar_QA
        'ar': 'ar-QA',
        # de_DE
        'de': 'de-DE',
        # en_US
        'en': 'en-US',
        # es_ES
        'es': 'es-ES',
        # fr_FR
        'fr': 'fr-FR',
        # it_IT
        'it': 'it-IT',
        # nl_NL
        'nl': 'nl-NL',
        # ru_RU
        'ru': 'ru-RU',
        # th_TH
        'th': 'th-TH',
        # vi_VN
        'vi': 'vi-VN'
    }

class MyIntegrationHub:
    def __init__(
        self,
        hass,
        username,
        password,
        senceId,
        base_url=BASE_URL,
        poll_interval_seconds=DEFAULT_POLL_INTERVAL_SECONDS,
    ):

        self._entities = []
        self.senceId = senceId
        self.hass = hass
        self.devices_info: dict[str, list[Any]] = {}
        self._username = username
        self._password = password
        self._session = async_get_clientsession(self.hass)  # 存储登录后的会话
        self._unsub_polling = None  #存储定时器取消函数 
        self._unsub_login = None
        self.total_data = {}
        self.device_data: dict[str, Any] = {}
        self.plants = []
        self.home_control_devices=[]
        self.cur_ctl_devices = None
        self.base_url = (base_url or BASE_URL).strip().rstrip("/")
        self.poll_interval_seconds = max(
            MIN_POLL_INTERVAL_SECONDS,
            min(MAX_POLL_INTERVAL_SECONDS, int(poll_interval_seconds)),
        )
        try:
            language_key = hass.config.language.lower() if hasattr(hass.config, 'language') else 'en'
            self.lang = langs.get(language_key, 'en-US')
            _LOGGER.debug(f'Language set to: {self.lang}')
        except Exception as e:
            _LOGGER.warning(f'Failed to get language config, using default: {e}')
            self.lang = 'en-US'

    async def login(self, now=None):
        # 重新登录 并启动轮询
        """执行登录操作"""
        _LOGGER.warning("开始登录")
        success = await self._login(self._username, self._password)
        if not success:
            raise Exception("Sunpura cloud login failed")
        # 登录成功后启动轮询
        # await self.start_polling()

    async def _login(self, username, password):
        self._session = async_get_clientsession(self.hass)
        username = username.strip()
        headers = {
            **self._build_common_headers(),
            "Content-Type": "application/json;charset=UTF-8",
        }
        last_message = "Login failed"
        last_connect_message = ""

        for candidate_base_url in self._candidate_base_urls(self.base_url):
            url = candidate_base_url + "/user/login"

            # Prime session cookie (JSESSIONID) before POST /user/login.
            try:
                async with self._session.get(url, headers=self._build_common_headers()) as resp:
                    self._session.cookie_jar.update_cookies(resp.cookies)
            except ClientError:
                pass

            for variant_name, req in self._build_login_payloads(username, password):
                try:
                    async with self._session.post(url, headers=headers, data=json.dumps(req)) as resp:
                        if resp.status != 200:
                            response_text = await resp.text()
                            raise Exception(
                                f"Login failed (HTTP {resp.status}): {response_text[:200]}"
                            )
                        self._session.cookie_jar.update_cookies(resp.cookies)
                        try:
                            resp_data = await resp.json()
                        except (json.JSONDecodeError, ContentTypeError) as err:
                            response_text = await resp.text()
                            raise Exception(
                                f"Unexpected login response: {response_text[:200]}"
                            ) from err
                except ClientError as err:
                    last_connect_message = f"HTTP error during login: {err}"
                    continue
                except Exception as err:
                    message = str(err)
                    if self._looks_like_connectivity_error(message):
                        last_connect_message = message
                    continue

                _LOGGER.debug("登录响应（%s/%s）：%s", candidate_base_url, variant_name, resp_data)
                if isinstance(resp_data, dict) and resp_data.get("result") == 1:
                    self.base_url = candidate_base_url
                    _LOGGER.info("登录成功，使用 %s（变体：%s）", candidate_base_url, variant_name)
                    return True

                if isinstance(resp_data, dict):
                    message = str(resp_data.get("msg", "Login failed"))
                    result = resp_data.get("result")
                    _LOGGER.debug(
                        "登录失败（%s/%s）：result=%s msg=%s",
                        candidate_base_url,
                        variant_name,
                        result,
                        message,
                    )
                    last_message = message
                    if self._looks_like_connectivity_error(message):
                        last_connect_message = message
                else:
                    last_connect_message = f"Invalid login response format: {resp_data}"

        if last_connect_message and last_message == "Login failed":
            _LOGGER.error(f"登录失败（连接问题）：{last_connect_message}")
        else:
            _LOGGER.error(f"登录失败，最后错误：{last_message}")
        return False

    async def start_polling(self):
        """启动定时轮询"""
        # 先取消已有轮询（如果存在）
        await self.stop_polling()

        # 设置轮询间隔
        update_interval = timedelta(seconds=self.poll_interval_seconds)
        _LOGGER.info(
            "Starting Sunpura polling every %s seconds",
            self.poll_interval_seconds,
        )

        # 注册定时任务
        self._unsub_polling = async_track_time_interval(
            self.hass,
            self.async_update_data,  # 更新数据的回调函数
            update_interval
        )

        # 立即执行首次更新
        await self.async_update_data()

    async def stop_polling(self):
        """停止轮询"""
        if self._unsub_polling:
            self._unsub_polling()
            self._unsub_polling = None

    async def start_schedule_login(self):
        """启动定时轮询"""
        # 先取消已有轮询（如果存在）
        await self.stop_schedule_login()
        # 设置轮询间隔
        update_interval = timedelta(hours=8)
        # 注册定时任务
        self._unsub_login = async_track_time_interval(
            self.hass,
            self.login,  # 更新数据的回调函数
            update_interval
        )

    async def stop_schedule_login(self):
        """停止轮询"""
        if self._unsub_login:
            self._unsub_login()
            self._unsub_login = None

    def add_entity(self, entity):
        """添加需要更新的实体"""
        self._entities.append(entity)

    async def async_update_data(self, now=None):
        """执行数据更新操作"""
        _LOGGER.debug("开始更新数据")
        start_time = datetime.now()
        try:
            # 更新主页数据
            await self.getPlantVos()
            await self.get_home_control_devices()
            new_data = await self.getHomeCountData(self.cur_ctl_devices)
            if new_data:
                devices_manager = self.hass.data[DOMAIN]['device_manager']
                # 按设备sn请求设备详细数据
                for device in devices_manager.devices:
                    if device.type != -1:
                        _LOGGER.debug(f"开始更新设备：{device.type},{device.device_sn}")
                        try:
                            res = await self.fetch_device_info(device.type, device.device_sn)
                            _LOGGER.debug(f"获取到设备信息：{res}")
                            if res and res.get("displayMap"):
                                self.devices_info[device.device_sn] = res["displayMap"]
                        except Exception as e:
                            _LOGGER.error(f"Error fetching device info for {device.device_sn}: {e}")
                
                # 更新设备所有关联实体
                # 检测更新用时 获取当前时间
                try:
                    ai = await self.getAiSystemByPlantId()
                    for entity in self._entities:
                        if hasattr(entity, 'update_data'):
                            entity.update_data(new_data, self.devices_info, ai)
                except Exception as e:
                    _LOGGER.error(f"Error updating entity data: {e}")
            else:
                _LOGGER.warning("No new data received from getHomeCountData")

        except Exception as e:
            _LOGGER.error(f"发生异常的行号是: {e.__traceback__.tb_lineno}, 异常信息: {e}")
        end_time = datetime.now()
        _LOGGER.info(f"更新数据getHomeCountData完成，耗时：{end_time - start_time}")

    async def getHomeCountData(self, sn=""):
        url = self.base_url + "/energy/getHomeCountData"
        try:
            resp = await self.post({}, url, params={
                "plantId": self.senceId,
                "deviceSn": sn if sn else ""
            })
            if resp and resp.get('obj'):
                _LOGGER.info(f"获取到能流数据：{resp}")
                res = resp['obj']
                _LOGGER.debug(res)
                self.total_data = res
                return res
            else:
                _LOGGER.error(f"Invalid response from getHomeCountData: {resp}")
                return None
        except Exception as e:
            _LOGGER.error(f"Error in getHomeCountData: {e}")
            return None

    # 获取用户下所有电站
    async def getPlantVos(self):
        url = self.base_url + "/plant/getPlantVos"
        resp = await self.get({}, url, {})
        if not isinstance(resp, dict):
            raise Exception(f"Invalid getPlantVos response: {resp}")
        _LOGGER.debug(f"<UNK>{resp}")
        res = resp.get('obj', [])
        # _LOGGER.info(res)
        self.plants = res
        return res

    # AI能流详情
    async def getAiSystemByPlantId(self):
        # _LOGGER.info(self._session)
        url = self.base_url + "/aiSystem/getAiSystemByPlantId"
        resp = await self.get({}, url, params={
            "plantId": self.senceId
        })
        if not isinstance(resp, dict):
            raise Exception(f"Invalid getAiSystemByPlantId response: {resp}")
        _LOGGER.debug(f"ai模式响应：{resp}")
        res = resp.get('obj')
        _LOGGER.debug(f"res:{res}")
        return res

    # 获取设备数据详情
    async def fetch_device_info(self, device_type, device_sn):
        # _LOGGER.info(self._session)
        url = self.base_url + "/device/getDeviceBySn"
        # 获取当前日期的yyyy-MM-dd格式字符串
        a = datetime.now().strftime("%Y-%m-%d")
        resp = await self.post({}, url, params={
            'deviceType': device_type,
            'time': a,
            'sn': device_sn,
        })
        if not isinstance(resp, dict):
            raise Exception(f"Invalid fetch_device_info response: {resp}")
        _LOGGER.debug(f"设备数据详情响应：{resp}")
        res = resp.get('obj')
        if isinstance(res, dict):
            _LOGGER.debug(res.get('chartMap'))
            # 置空
            res['chartMap'] = None
        else:
            raise Exception(f"Invalid device detail payload: {resp}")
        # _LOGGER.debug(res)
        self.device_data[device_sn] = res
        return res

    # 开关
    async def switch_socket(self, sn, v):
        # _LOGGER.info(self._session)
        url = self.base_url + "/device/setDeviceParam"
        resp = await self.post({'Content-Type': 'application/x-www-form-urlencoded'}, url, {
            'deviceSn': sn,
            'startAddr': 0x0000,
            'data': v,
        })
        _LOGGER.info(f"下发开关设置响应：{resp}")
        res = resp['msg']
        # _LOGGER.info(res)
        return res

    # 开关
    async def switch_charger(self, sn, v):
        url = self.base_url + "/device/setDeviceParam"
        resp = await self.post({'Content-Type': 'application/x-www-form-urlencoded'}, url, {
            'deviceSn': sn,
            'startAddr': 0x00AF,
            'data': v,
        })
        _LOGGER.info(f"下发开关设置响应：{resp}")
        res = resp['msg']
        # _LOGGER.info(res)
        return res

    # 开关
    async def switch_product(self, sn, v):
        url = self.base_url + "/energyProduct/setEnergyProductSwitch"
        resp = await self.post({}, url, params={
            "deviceSn": sn,
            "switchStatus": v
        })
        _LOGGER.info(f"下发开关设置响应：{resp}")
        res = resp['msg']
        # _LOGGER.info(res)
        return res

    # 电站日统计数据
    async def get_energy_data_day(self, plant_id, sn=""):
        url = self.base_url + "/energy/getEnergyDataDay"
        a = datetime.now().strftime("%Y-%m-%d")
        resp = await self.post({}, url, params={
            'plantId':plant_id,
            'time': a,
            "deviceSn": sn
        })
        res = resp['obj']
        # _LOGGER.info(res)
        return res

    # 电站月统计数据
    async def get_energy_data_month(self, plant_id, sn=""):
        url = self.base_url + "/energy/getEnergyDataMonth"
        a = datetime.now().strftime("%Y-%m")
        resp = await self.post({}, url, params={
            'plantId':plant_id,
            'time': a,
            "deviceSn": sn
        })
        res = resp['obj']
        # _LOGGER.info(res)
        return res
    # 电站年统计数据
    async def get_energy_data_year(self, plant_id, sn=""):
        url = self.base_url + "/energy/getEnergyDataYear"
        a = datetime.now().strftime("%Y")
        resp = await self.post({}, url, params={
            'plantId':plant_id,
            'time': a,
            "deviceSn": sn
        })
        res = resp['obj']
        # _LOGGER.info(res)
        return res
    # 电站总计数据
    async def get_energy_data_total(self, plant_id, sn=""):
        url = self.base_url + "/energy/getEnergyDataTotal"
        a = datetime.now().strftime("%Y")
        resp = await self.post({}, url, params={
            'plantId':plant_id,
            'time': a,
            "deviceSn": sn
        })
        res = resp['obj']
        # _LOGGER.info(res)
        return res
    async def get_home_control_devices(self):
        url = self.base_url + "/energy/getHomeControlSn/"+self.senceId
        resp = await self.get({}, url)
        if resp and resp.get('obj'):
            res = resp['obj']
            _LOGGER.info(res)
            self.home_control_devices=res
            if res and len(res) > 0 and 'deviceSn' in res[0]:
                self.cur_ctl_devices=res[0]['deviceSn']
            else:
                _LOGGER.warning("No control devices found or missing deviceSn")
                self.cur_ctl_devices = None
            return res
        else:
            _LOGGER.error("Failed to get home control devices")
            self.home_control_devices = []
            self.cur_ctl_devices = None
            return []

    # 通用POST请求
    @staticmethod
    def _login_field_variants() -> tuple[str, ...]:
        return ("email", "username", "userName", "account", "phone")

    def _build_login_payloads(self, username: str, password: str) -> list[tuple[str, dict]]:
        hashed_password = md5_hash(password)
        client_variants = (
            {"phoneOs": "2", "phoneModel": "apple", "appVersion": IOS_APP_VERSION},
            {"phoneOs": 2, "phoneModel": "iPhone", "appVersion": "V1.1"},
            {"phoneOs": 1, "phoneModel": "1.1", "appVersion": "V1.1"},
        )
        payloads: list[tuple[str, dict]] = []
        seen_payloads: set[str] = set()
        for client in client_variants:
            phone_os = client["phoneOs"]
            for field_name in self._login_field_variants():
                for password_mode, password_value in (("md5", hashed_password), ("plain", password)):
                    payload = {field_name: username, "password": password_value, **client}
                    payload_key = json.dumps(payload, sort_keys=True)
                    if payload_key in seen_payloads:
                        continue
                    seen_payloads.add(payload_key)
                    payloads.append((f"os{phone_os}/{field_name}/{password_mode}", payload))
        return payloads

    def _build_common_headers(self) -> dict:
        return {
            "Accept": "*/*",
            "Accept-Language": self.lang,
            "User-Agent": IOS_USER_AGENT,
            "interfacetype": SUNPURA_INTERFACE_TYPE,
            "appversion": IOS_APP_VERSION,
            "projecttype": SUNPURA_PROJECT_TYPE,
            "token": "<null>",
        }

    @staticmethod
    def _looks_like_connectivity_error(message: str) -> bool:
        if not message:
            return False
        lowered = message.lower()
        markers = (
            "timeout",
            "timed out",
            "network",
            "server",
            "gateway",
            "service",
            "connection",
            "connect",
            "系统",
            "服务",
            "连接",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _candidate_base_urls(base_url: str) -> list[str]:
        primary = (base_url or BASE_URL).strip().rstrip("/")
        candidates = [primary]
        if primary == LEGACY_BASE_URL:
            candidates.append(BASE_URL)
        elif primary == BASE_URL:
            candidates.append(LEGACY_BASE_URL)
        return candidates

    # 通用POST请求
    @staticmethod
    def _is_login_required_response(resp_data: Any) -> bool:
        if not isinstance(resp_data, dict):
            return False
        if str(resp_data.get("result")) == "10000":
            return True
        for value in resp_data.values():
            value_text = str(value)
            if "请登录" in value_text or "Please login" in value_text:
                return True
        return False

    async def post(self, headers, url, data=None, params=None, retry_on_login=True):
        req_headers = {**self._build_common_headers(), **(headers or {})}
        try:
            async with self._session.post(url, headers=req_headers, params=params, data=data) as resp:
                if resp.status != 200:
                    response_text = await resp.text()
                    raise Exception(
                        f"Failed to fetch data from {url} (HTTP {resp.status}): {response_text[:200]}"
                    )
                self._session.cookie_jar.update_cookies(resp.cookies)
                try:
                    resp_data = await resp.json()
                except (json.JSONDecodeError, ContentTypeError) as err:
                    resp_text = await resp.text()
                    _LOGGER.warning(f"Unexpected non-JSON POST response from {url}: {resp_text}")
                    raise Exception(f"Unexpected non-JSON response from {url}") from err
        except ClientError as err:
            raise Exception(f"HTTP error while requesting {url}: {err}") from err

        if self._is_login_required_response(resp_data):
            _LOGGER.warning("需要登录")
            if retry_on_login:
                await self.login()
                return await self.post(
                    headers,
                    url,
                    data=data,
                    params=params,
                    retry_on_login=False
                )
            return None
        return resp_data

        # 通用Get请求

    # 通用GET请求
    async def get(self, headers, url, data=None, params=None, retry_on_login=True):
        req_headers = {**self._build_common_headers(), **(headers or {})}
        try:
            async with self._session.get(url, headers=req_headers, params=params, data=data) as resp:
                if resp.status != 200:
                    response_text = await resp.text()
                    raise Exception(
                        f"Failed to fetch data from {url} (HTTP {resp.status}): {response_text[:200]}"
                    )
                self._session.cookie_jar.update_cookies(resp.cookies)
                try:
                    resp_data = await resp.json()
                except (json.JSONDecodeError, ContentTypeError) as err:
                    resp_text = await resp.text()
                    _LOGGER.warning(f"Unexpected non-JSON GET response from {url}: {resp_text}")
                    raise Exception(f"Unexpected non-JSON response from {url}") from err
        except ClientError as err:
            raise Exception(f"HTTP error while requesting {url}: {err}") from err

        if self._is_login_required_response(resp_data):
            _LOGGER.warning("需要登录")
            _LOGGER.warning(resp_data)
            if retry_on_login:
                await self.login()
                return await self.get(
                    headers,
                    url,
                    data=data,
                    params=params,
                    retry_on_login=False
                )
            return None
        return resp_data

    # Battery Control API Methods
    async def set_ai_system_energy_mode(self, payload: dict):
        """Set AI system energy mode for battery control."""
        url = self.base_url + "/aiSystem/setAiSystemTimesWithEnergyMode"
        
        # Use the existing authenticated session via post() method
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json",
            "User-Agent": "okhttp/4.10.0"
        }
        
        # Convert payload to JSON string for data parameter
        import json
        json_data = json.dumps(payload)
        
        try:
            result = await self.post(headers, url, data=json_data)
            if result and result.get("result") == 0:
                _LOGGER.info(f"Successfully set AI system energy mode")
                return result
            elif result:
                _LOGGER.error(f"Failed to set AI system energy mode: {result.get('msg', 'Unknown error')}")
                raise Exception(f"API error: {result.get('msg', 'Unknown error')}")
            else:
                raise Exception("No response from API")
        except Exception as e:
            _LOGGER.error(f"Exception in set_ai_system_energy_mode: {e}")
            raise

    async def set_device_parameter(self, param_name: str, param_value: str):
        """Set a single device parameter using the existing authentication."""
        # Note: This method may require additional API credentials (companyCode, API key)
        # that are not available in the current config flow.
        # For now, we'll focus on the setAiSystemTimesWithEnergyMode API
        # which appears to work with the existing session authentication.
        
        _LOGGER.warning(f"set_device_parameter not yet implemented for {param_name}={param_value}")
        _LOGGER.warning("This requires additional API credentials not available in config flow")
        raise NotImplementedError("Device parameter setting requires additional API setup")
