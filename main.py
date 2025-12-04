"""flo X5 sync daemon."""
import os
import time
import logging
from flo_client.device import FloX5Device
from flo_client.scheduler import FloScheduler
from flo_client.consts import *


logger = logging.getLogger(__name__)

def configure_logging(log_level: str | None) -> None:
    level = logging.INFO
    if log_level: level = logging.getLevelName(log_level)
    logging.basicConfig(level=level, format="[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s")

if __name__ == "__main__":
    # 1. Load Configuration
    username = os.environ.get("FLO_USERNAME")
    password = os.environ.get("FLO_PASSWORD")
    station_name = os.environ.get("FLO_STATION_NAME")
    log_level = os.environ.get("FLO_LOG_LEVEL")
    mqtt_host = os.environ.get("HASS_MQTT_HOST")
    mqtt_port = os.environ.get("HASS_MQTT_PORT")
    mqtt_user = os.environ.get("HASS_MQTT_USERNAME")
    mqtt_pass = os.environ.get("HASS_MQTT_PASSWORD")

    configure_logging(log_level)
    if not os.path.exists("./" + DATA_FOLDER): raise Exception(f"Data folder '{DATA_FOLDER}' missing.")

    logger.info("--- Starting Flo X5 Bridge ---")

    try:
        # 2. Initialize the Device (Standard Logic)
        device = FloX5Device(
            username, password, station_name,
            mqtt_host, mqtt_port, mqtt_user, mqtt_pass
        )

        # 3. Initialize the Scheduler (New Logic)
        # This keeps main.py clean and delegates all the complexity to the new class
        scheduler = FloScheduler(device, station_name, mqtt_host, mqtt_port, mqtt_user, mqtt_pass)
        scheduler.start()

        # 4. Run Main Loop
        while True:
            try:
                device.update_all_sensors()
            except Exception as e:
                logger.error(f"Sensor Update Failed: {e}")
            
            logger.debug(f"Sleeping {REFRESH_DELAY_SECS}s...")
            time.sleep(REFRESH_DELAY_SECS)

    except Exception as e:
        logger.fatal(f"Fatal Error: {e}")