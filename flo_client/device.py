"""HomeAssistant MQTT device for flo X5."""

import os
import logging

from flo_client.client import FloX5Client
from flo_client.consts import *
from ha_mqtt_discoverable import Settings, DeviceInfo  # type: ignore
from ha_mqtt_discoverable.sensors import (  # type: ignore
    BinarySensor,
    BinarySensorInfo,
    Sensor,
    SensorInfo,
)


class FloX5Device:
    session_id = None

    def __init__(
        self,
        username: str,
        password: str,
        station_name: str,
        hass_mqtt_host: str,
        hass_mqtt_port: str,
        hass_mqtt_username: str | None,
        hass_mqtt_password: str | None,
    ) -> None:
        self.username: str = username
        self.password: str = password
        self.station_name: str = station_name
        self.hass_mqtt_host: str = hass_mqtt_host
        self.hass_mqtt_port: str = hass_mqtt_port
        self.hass_mqtt_username: str | None = hass_mqtt_username
        self.hass_mqtt_password: str | None = hass_mqtt_password

        self.logger: logging.Logger = logging.getLogger(__name__)

        self.client: FloX5Client = FloX5Client(username, password)
        self._initialize_device()
        self._initialize_sensors()

    def _initialize_device(self) -> None:
        # Configure the required parameters for the MQTT broker
        self.mqtt_settings = Settings.MQTT(
            host=self.hass_mqtt_host,
            port=self.hass_mqtt_port,
            username=self.hass_mqtt_username,
            password=self.hass_mqtt_password,
        )

        station = self.client.get_station_by_name(self.station_name)

        if station is None:
            raise Exception("Station not found: " + self.station_name)

        meta = self.client.get_device_meta(station)

        self.logger.info("Creating device for station: " + meta["name"])

        # Define the device. At least one of `identifiers` or `connections` must be supplied
        self.device_info = DeviceInfo(
            name=meta["name"],
            model=meta["model"],
            manufacturer=meta["manufacturer"],
            identifiers=meta["identifiers"],
        )

    def _initialize_sensors(self) -> None:
        self.logger.info("Initializing sensors...")

        # Online sensor
        online_sensor_info = BinarySensorInfo(
            name="Station Online",
            device_class="connectivity",
            unique_id="status",
            device=self.device_info,
        )
        online_sensor_settings = Settings(
            mqtt=self.mqtt_settings, entity=online_sensor_info
        )

        self.online_sensor = BinarySensor(online_sensor_settings)

        # Vehicle connected sensor
        vehicle_connected_sensor_info = BinarySensorInfo(
            name="Vehicle Connected",
            device_class="connectivity",
            unique_id="vehicle_connected",
            device=self.device_info,
        )
        vehicle_connected_sensor_settings = Settings(
            mqtt=self.mqtt_settings, entity=vehicle_connected_sensor_info
        )

        self.vehicle_connected_sensor = BinarySensor(vehicle_connected_sensor_settings)

        # Charging sensor
        vehicle_charging_sensor_info = BinarySensorInfo(
            name="Vehicle Charging",
            device_class="battery_charging",
            unique_id="vehicle_charging",
            device=self.device_info,
        )
        vehicle_charging_sensor_settings = Settings(
            mqtt=self.mqtt_settings, entity=vehicle_charging_sensor_info
        )

        self.vehicle_charging_sensor = BinarySensor(vehicle_charging_sensor_settings)

        # Amperage sensor
        amperage_charging_sensor_info = SensorInfo(
            name="Amperage",
            unit_of_measurement="A",
            state_class="measurement",
            device_class="current",
            unique_id="amperage_charging",
            device=self.device_info,
        )

        amperage_charging_sensor_settings = Settings(
            mqtt=self.mqtt_settings, entity=amperage_charging_sensor_info
        )

        self.amperage_charging_sensor = Sensor(amperage_charging_sensor_settings)

        # Amperage offered sensor
        amperage_offered_sensor_info = SensorInfo(
            name="Amperage Offered",
            unit_of_measurement="A",
            state_class="measurement",
            device_class="current",
            unique_id="amperage_offered",
            device=self.device_info,
        )

        amperage_offered_sensor_settings = Settings(
            mqtt=self.mqtt_settings, entity=amperage_offered_sensor_info
        )

        self.amperage_offered_sensor = Sensor(amperage_offered_sensor_settings)

        # Voltage sensor
        voltage_sensor_info = SensorInfo(
            name="Voltage",
            unit_of_measurement="V",
            state_class="measurement",
            device_class="voltage",
            unique_id="voltage",
            device=self.device_info,
        )

        voltage_sensor_settings = Settings(
            mqtt=self.mqtt_settings, entity=voltage_sensor_info
        )

        self.voltage_sensor = Sensor(voltage_sensor_settings)

        # Energy transferred sensor
        energy_transferred_sensor_info = SensorInfo(
            name="Energy Transferred",
            unit_of_measurement="kWh",
            state_class="total_increasing",
            device_class="energy",
            unique_id="session_energy_transferred",
            device=self.device_info,
        )

        energy_transferred_sensor_settings = Settings(
            mqtt=self.mqtt_settings, entity=energy_transferred_sensor_info
        )

        self.energy_transferred_sensor = Sensor(energy_transferred_sensor_settings)

    def _get_station(self) -> dict | None:
        return self.client.get_station_by_name(self.station_name)

    def _get_session(self) -> dict | None:
        station = self._get_station()

        if station is None:
            return None

        try:
            station_id = self.client.station_id(station)
        except Exception:
            station_id = (
                station.get("chargingStationUid") or station["information"]["id"]
            )

        return self.client.get_session_by_id(station_id)

    def _save_last_session_id(self, session_id: str) -> None:
        with open("./" + DATA_FOLDER + "/last-session", "w") as f:
            f.write(session_id)

    def _get_last_session_id(self) -> str | None:
        if os.path.exists("./" + DATA_FOLDER + "/last-session"):
            with open("./" + DATA_FOLDER + "/last-session", "r") as f:
                return f.read()

        return None

    def update_all_sensors(self) -> None:
        self.logger.info("Updating sensors...")

        self.update_station_online_sensor()
        self.update_vehicle_connected_sensor()
        self.update_vehicle_charging_sensor()

    def update_station_online_sensor(self) -> None:
        self.logger.debug("Updating station online sensor...")

        if self.client.is_station_online(self._get_station()):
            self.online_sensor.on()
        else:
            self.online_sensor.off()

    def update_vehicle_connected_sensor(self) -> None:
        self.logger.debug("Updating vehicle connected sensor...")

        if self.client.is_vehicle_connected(self._get_station()):
            self.vehicle_connected_sensor.on()
        else:
            self.vehicle_connected_sensor.off()

    def update_vehicle_charging_sensor(self) -> None:
        self.logger.debug("Updating vehicle charging sensor...")

        session = self._get_session()

        # Change the state of the sensor, publishing an MQTT message that gets picked up by HA
        if self.client.is_vehicle_charging(self._get_station()):
            self.vehicle_charging_sensor.on()

            if session is not None:
                if session[SESSION_ID] != self._get_last_session_id():
                    # New session, reset the energy transferred sensor to avoid duplicate total energy computation.
                    self.energy_transferred_sensor.set_state(0)
                    self._save_last_session_id(session[SESSION_ID])

                self.amperage_charging_sensor.set_state(
                    float(session[SESSION_AMPERAGE])
                )
                self.amperage_offered_sensor.set_state(
                    float(session[SESSION_AMPERAGE_OFFERED])
                )
                self.voltage_sensor.set_state(float(session[SESSION_VOLTAGE]))

                # Convert from Wh to kWh with 2 decimal points.
                self.energy_transferred_sensor.set_state(
                    "{:.2f}".format(
                        float(session[SESSION_ENERGY_TRANSFERRED_WH]) / 1000
                    )
                )
        else:
            self.vehicle_charging_sensor.off()
            self.amperage_charging_sensor.set_state(0)
            self.amperage_offered_sensor.set_state(0)
            self.voltage_sensor.set_state(0)

    
    # Add to flo_client/device.py inside FloX5Device class

    def set_schedule(self, schedule_data):
        """
        Pushes a schedule to the Flo v3.0 API.
        """
        import requests
        from flo_client.consts import STATIONS_URL

        # 1. Resolve Station UUID (Handles method vs property difference)
        try:
            # Try calling as function first (most likely)
            real_uuid = self.client.station_id()
        except TypeError:
            # Fallback to property or passing self
            try:
                real_uuid = self.client.station_id(self.client._selected_station)
            except:
                real_uuid = getattr(self.client, 'station_id', None)

        if not real_uuid:
            print("❌ [Device] Error: Could not resolve Station UUID.")
            return False

        # 2. Resolve Auth Headers (Bypassing read-only transport)
        try:
            headers = self.client._get_headers()
        except TypeError:
            headers = self.client._get_headers

        # 3. Send Request
        url = f"{STATIONS_URL}/{real_uuid}/power-schedule"
        try:
            resp = requests.put(url, json=schedule_data, headers=headers, timeout=10)
            if resp.status_code == 200:
                return True
            else:
                print(f"❌ [Device] API Error {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            print(f"❌ [Device] Request Exception: {e}")
            return False