import logging
import json
import paho.mqtt.client as mqtt
import threading

logger = logging.getLogger(__name__)

class FloScheduler:
    # ⚠️ CHANGED: Added 'station_name' to arguments
    def __init__(self, device, station_name, mqtt_host, mqtt_port, mqtt_user=None, mqtt_pass=None):
        self.device = device
        self.station_name = station_name  # <--- Use the passed string directly
        self.mqtt_config = (mqtt_host, int(mqtt_port), mqtt_user, mqtt_pass)
        
        # Internal State (4 Slots)
        self.slots = {i: {"enabled": False, "start": "00:00", "stop": "00:00"} for i in range(1, 5)}
        
        # Dedicated MQTT Client
        self.client = mqtt.Client()
        if mqtt_user and mqtt_pass:
            self.client.username_pw_set(mqtt_user, mqtt_pass)
            
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def start(self):
        """Starts the background MQTT listener."""
        try:
            host, port, _, _ = self.mqtt_config
            self.client.connect(host, port, 60)
            self.client.loop_start()
            logger.info("✅ Scheduler: Service started in background.")
        except Exception as e:
            logger.error(f"❌ Scheduler: Failed to connect to MQTT: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("✅ Scheduler: Connected to MQTT.")
            client.subscribe(f"flo/{self.station_name}/config/#")
            self._publish_discovery()
            self._sync_states()
        else:
            logger.error(f"❌ Scheduler: MQTT Connection Bad Code: {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            parts = msg.topic.split('/')
            payload = msg.payload.decode()

            # Handle Setting Updates
            if "period" in parts and "set" in parts:
                idx = parts.index("period")
                slot = int(parts[idx + 1])
                attr = parts[idx + 2] # enabled, start, stop
                self._update_slot(slot, attr, payload)

            # Handle Apply
            elif msg.topic.endswith("/config/apply"):
                logger.info("🚀 Scheduler: Applying config...")
                payload = self._generate_flo_json()
                if self.device.set_schedule(payload):
                    logger.info("✅ Scheduler: Apply Successful.")

        except Exception as e:
            logger.error(f"⚠️ Scheduler Message Error: {e}")

    def _update_slot(self, slot, attr, value):
        """Updates memory and echoes state back to HA (Feedback Loop)."""
        if attr == "enabled":
            self.slots[slot][attr] = str(value).lower() in ['true', 'on', '1']
            payload = "on" if self.slots[slot][attr] else "off"
        else:
            self.slots[slot][attr] = str(value)
            payload = str(value)
            
        # Echo back to /state topic
        topic = f"flo/{self.station_name}/config/period/{slot}/{attr}/state"
        self.client.publish(topic, payload, retain=True)

    def _time_to_min(self, t_str):
        try:
            h, m = map(int, t_str.split(':'))
            return h * 60 + m
        except: return 0

    def _generate_flo_json(self):
        periods = []
        for i, s in self.slots.items():
            if s['enabled']:
                start_min = self._time_to_min(s['start'])
                end_min = self._time_to_min(s['stop'])
                
                # Si l'heure de fin est 00:00 et que l'heure de début est non-nulle,
                # on assume que 00:00 = 1440 minutes (fin de journée)
                if s['stop'] == "00:00" and start_min != 0:
                    end_min = 1440
                
                if start_min != end_min:
                    periods.append({
                        "days": [7, 1, 2, 3, 4, 5, 6],
                        "maxCurrent": 0, 
                        "from": start_min,
                        "to": end_min
                    })
        
        return {
            "enabled": len(periods) > 0,
            "seasons": [{"startDate": {"month": 1, "date": 1}, "endDate": {"month": 12, "date": 31}, "periods": periods}]
        }

    def _publish_discovery(self):
        logger.info("📢 Scheduler: Sending Discovery...")
        dev = {
            "identifiers": [self.station_name],
            "name": f"Flo X5: {self.station_name}",
            "manufacturer": "AddEnergie",
            "model": "AddEnergie_SmartHOME_v1"
        }
        
        # Apply Button
        self.client.publish(f"homeassistant/button/flo_{self.station_name}/apply/config", json.dumps({
            "name": "Apply Schedule", "unique_id": f"{self.station_name}_apply",
            "command_topic": f"flo/{self.station_name}/config/apply", "payload_press": "GO",
            "icon": "mdi:cloud-upload", "device": dev
        }), retain=True)

        # Slots
        for i in range(1, 5):
            self._publish_control(i, "active", "switch", "enabled", "on", "off", "mdi:timer-outline", dev)
            self._publish_control(i, "start", "text", "start", None, None, "mdi:clock-start", dev)
            self._publish_control(i, "stop", "text", "stop", None, None, "mdi:clock-end", dev)

    def _publish_control(self, i, uid_suffix, comp_type, attr_name, on_pay, off_pay, icon, dev):
        topic = f"homeassistant/{comp_type}/flo_{self.station_name}/p{i}_{uid_suffix}/config"
        payload = {
            "name": f"Period {i} {uid_suffix.capitalize()}",
            "unique_id": f"{self.station_name}_p{i}_{uid_suffix}",
            "command_topic": f"flo/{self.station_name}/config/period/{i}/{attr_name}/set",
            "state_topic": f"flo/{self.station_name}/config/period/{i}/{attr_name}/state",
            "icon": icon, "device": dev
        }
        if comp_type == "text":
            payload["pattern"] = "^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
            payload["mode"] = "text"
        if on_pay:
            payload["payload_on"] = on_pay
            payload["payload_off"] = off_pay
            
        self.client.publish(topic, json.dumps(payload), retain=True)

    def _sync_states(self):
        for i, s in self.slots.items():
            self._update_slot(i, "enabled", s['enabled'])
            self._update_slot(i, "start", s['start'])
            self._update_slot(i, "stop", s['stop'])