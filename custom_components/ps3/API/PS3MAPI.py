import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote

class SensorError(Exception):
    pass

class NotificationError(Exception):
    pass

class FanModeError(Exception):
    pass

class PS3MAPIWrapper:
    def __init__(self, ip: str):
        self.ip = ip
        self._state = None
        self._cpu_temp = None
        self._rsx_temp = None
        self._fan_speed = None
        self._fan_mode = None
        self._fan_modes_mapping = {
            'SYSCON': 'SYSCON',
            'Manual': 'Manual',
            'MAX': 'Dynamic',
            'AUTO': 'Auto'
        }

    async def _update(self):
        endpoint_temps_fan = f"http://{self.ip}/cpursx.ps3"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint_temps_fan, timeout = 5) as response:
                    if response.status == 200:
                        self._state = "On"
                        soup = BeautifulSoup(await response.text(), 'html.parser')
                        temperature_text = soup.find('a', class_='s', href = '/cpursx.ps3?up').text
                        self._cpu_temp = temperature_text.split(': ')[1].split('°C')[0]
                        self._rsx_temp = temperature_text.split(': ')[-1].split('°C')[0]
                        fan_speed_text = soup.find('a', class_='s', href = '/cpursx.ps3?mode').text
                        self._fan_speed = fan_speed_text.split(': ')[1].split('%')[0]

                        for substring, fan_mode in self._fan_modes_mapping.items():
                            if substring in temperature_text:
                                self._fan_mode = fan_mode
                                break
                        else:
                            raise SensorError("Fan mode sensor does not work")
                        
                    else:
                        self._state = None
                        self._cpu_temp = None
                        self._rsx_temp = None
                        self._fan_speed = None
                        self._fan_mode = None
                        raise SensorError(f"Unexpected response code: {response.status}")
        except asyncio.TimeoutError:
            self._state = "Off"
            self._cpu_temp = None
            self._rsx_temp = None
            self._fan_speed = None
            self._fan_mode = None
        except SensorError:
            raise

    async def _send_notification(self, notification: str, icon: int, sound: int):
        notification_url = quote(notification)
        endpoint_notification = f"http://{self.ip}/popup.ps3?{notification_url}&icon={icon}&snd={sound}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint_notification, timeout = 5) as response:
                    if response.status == 200:
                        pass
                    else:
                        raise NotificationError(f"Unexpected response code: {response.status}")
        except asyncio.TimeoutError:
            raise NotificationError("Notification service not available")
        except NotificationError:
            raise
        except Exception:
            raise NotificationError("Invalid host")
        
    async def _set_fan_mode(self, fan_mode: str):
        url_substrings = {'SYSCON': 'fan=0', 'Manual': 'fan=1;/cpursx.ps3?man', 'Dynamic': 'fan=1;/cpursx.ps3?man;/cpursx.ps3?mode', 'Auto': 'fan=2'}

        try:
            fan_mode_substring = url_substrings[fan_mode]
            endpoint_fan_mode = f"http://{self.ip}/cpursx.ps3?{fan_mode_substring}"

            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint_fan_mode, timeout = 5) as response:
                    if response.status == 200:
                        pass
                    else:
                        raise FanModeError(f"Unexpected response code: {response.status}")
        except asyncio.TimeoutError:
            raise FanModeError("Fan mode service not available")
        except FanModeError:
            raise
        except KeyError:
            raise FanModeError("Fan mode does not exist")


    async def update(self):
        try:
            await self._update()
        except SensorError:
            raise

    async def send_notification(self, notification: str, icon: int = 1, sound: int = 1):
        try:
            await self._send_notification(notification, icon, sound)
        except NotificationError:
            raise

    async def set_fan_mode(self, fan_mode: str):
        try:
            await self._set_fan_mode(fan_mode)
        except FanModeError:
            raise

    @property
    def state(self):
        return self._state

    @property
    def cpu_temp(self):
        return self._cpu_temp

    @property
    def rsx_temp(self):
        return self._rsx_temp
    
    @property
    def fan_speed(self):
        return self._fan_speed
    
    @property
    def fan_mode(self):
        return self._fan_mode