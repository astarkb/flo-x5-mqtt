"""Protocol adapters for legacy (v3.0) and OCPI (v3.1) stations.

Each adapter encapsulates:
- Station matching
- Online/connected/charging state logic
- Sessions endpoint selection and correlation
- Device metadata extraction

TODO: Expand OCPI EVSE status mapping as more statuses are discovered.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from flo_client.consts import (
    STATIONS_URL,
    SESSIONS_URL,
    HOMESTATION_URL_V31,
    SESSIONS_URL_V31,
    STATUS_KEY,
    STATE_KEY,
    STATE_AVAILABLE,
    STATE_INUSE,
    PILOT_STATE_KEY,
    PILOT_STATE_CONNECTED,
    PILOT_STATE_CHARGING,
    SESSION_CHARGING,
    SESSION_NOT_CHARGING,
)


class ProtocolAdapter:
    def list_stations(self, transport) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def matches(self, station: Dict[str, Any], name: str) -> bool:
        raise NotImplementedError

    def station_id(self, station: Dict[str, Any]) -> str:
        raise NotImplementedError

    def device_meta(self, station: Dict[str, Any]) -> Dict[str, str]:
        raise NotImplementedError

    def sessions(self, transport) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def is_online(self, station: Dict[str, Any]) -> bool:
        raise NotImplementedError

    def is_connected(self, station: Dict[str, Any], sessions: List[Dict[str, Any]]) -> bool:
        raise NotImplementedError

    def is_charging(self, station: Dict[str, Any], sessions: List[Dict[str, Any]]) -> bool:
        raise NotImplementedError


class LegacyAdapter(ProtocolAdapter):
    def list_stations(self, transport) -> List[Dict[str, Any]]:
        return transport.get_json(STATIONS_URL)

    def matches(self, station: Dict[str, Any], name: str) -> bool:
        return station.get("information", {}).get("name") == name

    def station_id(self, station: Dict[str, Any]) -> str:
        return station["information"]["id"]

    def device_meta(self, station: Dict[str, Any]) -> Dict[str, str]:
        return {
            "name": f"Flo X5: {station['information']['name']}",
            "model": station["information"]["model"],
            "manufacturer": "AddEnergie",
            "identifiers": station["information"]["id"],
        }

    def sessions(self, transport) -> List[Dict[str, Any]]:
        return transport.get_json(SESSIONS_URL)

    def is_online(self, station: Dict[str, Any]) -> bool:
        return (
            station[STATUS_KEY][STATE_KEY] == STATE_AVAILABLE
            or station[STATUS_KEY][STATE_KEY] == STATE_INUSE
        )

    def is_connected(self, station: Dict[str, Any], sessions: List[Dict[str, Any]]) -> bool:
        return (
            station[STATUS_KEY][PILOT_STATE_KEY] == PILOT_STATE_CONNECTED
            or station[STATUS_KEY][PILOT_STATE_KEY] == PILOT_STATE_CHARGING
        )

    def is_charging(self, station: Dict[str, Any], sessions: List[Dict[str, Any]]) -> bool:
        return station[STATUS_KEY][PILOT_STATE_KEY] == PILOT_STATE_CHARGING


class OcpiAdapter(ProtocolAdapter):
    def __init__(self, ocpi_stations: Optional[List[Dict[str, Any]]] = None) -> None:
        self._ocpi_stations = ocpi_stations
        self._homestation_payload: Optional[Dict[str, Any]] = None

    def list_stations(self, transport) -> List[Dict[str, Any]]:
        # If provided via constructor, return directly; otherwise fetch v3.1 homestation
        if self._ocpi_stations is not None:
            return self._ocpi_stations
        payload = transport.get_json(HOMESTATION_URL_V31)
        self._homestation_payload = payload
        return payload.get("ocpiHomeStations", []) or []

    def matches(self, station: Dict[str, Any], name: str) -> bool:
        return station.get("physicalReference") == name

    def station_id(self, station: Dict[str, Any]) -> str:
        return station.get("chargingStationUid")

    def device_meta(self, station: Dict[str, Any]) -> Dict[str, str]:
        return {
            "name": f"Flo X5: {station.get('physicalReference')}",
            "model": "X5",
            "manufacturer": "AddEnergie",
            "identifiers": station.get("chargingStationUid"),
        }

    def sessions(self, transport) -> List[Dict[str, Any]]:
        return transport.get_json(SESSIONS_URL_V31)

    def is_online(self, station: Dict[str, Any]) -> bool:
        return station.get("connectionStatus") == "Online"

    def is_connected(self, station: Dict[str, Any], sessions: List[Dict[str, Any]]) -> bool:
        # Prefer session presence with charging/not-charging states
        station_id = self.station_id(station)
        for s in sessions:
            st = s.get("station", {})
            if st.get("id") == station_id and s.get("sessionState") in (
                SESSION_CHARGING,
                SESSION_NOT_CHARGING,
            ):
                return True
        # Fallback: treat Charging as connected
        evse = station.get("evse", {})
        return evse.get("status") == "Charging"

    def is_charging(self, station: Dict[str, Any], sessions: List[Dict[str, Any]]) -> bool:
        evse = station.get("evse", {})
        return evse.get("status") == "Charging"

