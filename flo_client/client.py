"""Client for the flo X5 API."""

import logging

from datetime import datetime, timedelta
from flo_client.auth import Auth
from flo_client.consts import STATIONS_URL
from flo_client.transport import Transport
from flo_client.protocols import LegacyAdapter, OcpiAdapter, ProtocolAdapter


class FloX5Client:
    def __init__(self, username: str, password: str) -> None:
        self.next_refresh = datetime.now()
        self._auth = Auth(username, password)

        self._transport = Transport(self._get_headers)

        self._selected_adapter: ProtocolAdapter | None = None
        self._selected_station: dict | None = None

        self._refresh()

    def _refresh(self) -> None:
        # Maintain a simple periodic tick if needed later.
        # Currently, adapter-backed methods fetch as needed.
        if datetime.now() >= self.next_refresh:
            from flo_client.consts import REFRESH_DELAY_SECS

            self.next_refresh = datetime.now() + timedelta(seconds=REFRESH_DELAY_SECS)

    def _get_stations_v30(self) -> list[dict]:
        return self._transport.get_json(STATIONS_URL)

    def _get_headers(self) -> dict:
        return {
            "Accept": "*/*",
            "Authorization": "Bearer " + self._auth.get_access_token(),
        }

    def get_station_by_name(self, name: str) -> dict | None:
        """Discover stations via adapters and select the first match by name.

        Order:
        - Try OCPI v3.1 homestation for ocpi and embedded legacy stations.
        - If unavailable, fall back to legacy v3.0 stations.
        Stores the selected adapter and station for subsequent calls.
        """
        self._refresh()

        # Try OCPI (homestation v3.1)
        try:
            # Fetch payload once to derive both ocpi and legacy lists
            from flo_client.consts import HOMESTATION_URL_V31

            hs = self._transport.get_json(HOMESTATION_URL_V31)
            ocpi_list = hs.get("ocpiHomeStations", []) or []
            legacy_list = hs.get("legacyHomeStations", []) or []

            ocpi_adapter = OcpiAdapter(ocpi_list)
            for s in ocpi_list:
                if ocpi_adapter.matches(s, name):
                    self._selected_adapter = ocpi_adapter
                    self._selected_station = s
                    return s

            legacy_adapter = LegacyAdapter()
            for s in legacy_list:
                if legacy_adapter.matches(s, name):
                    self._selected_adapter = legacy_adapter
                    self._selected_station = s
                    return s
        except Exception:
            # Ignore and fall back to v3.0
            pass

        # Legacy v3.0 fallback
        try:
            legacy_adapter = LegacyAdapter()
            for s in legacy_adapter.list_stations(self._transport):
                if legacy_adapter.matches(s, name):
                    self._selected_adapter = legacy_adapter
                    self._selected_station = s
                    return s
        except Exception:
            return None

        return None

    def get_session_by_id(self, id: str) -> dict | None:
        self._refresh()
        if not self._selected_adapter:
            # Default to legacy list if no adapter is set
            adapter: ProtocolAdapter = LegacyAdapter()
        else:
            adapter = self._selected_adapter

        try:
            sessions = adapter.sessions(self._transport)
        except Exception:
            # Fallback for OCPI to legacy sessions
            sessions = LegacyAdapter().sessions(self._transport)

        for session in sessions:
            st = session.get("station", {})
            if st.get("id") == id:
                return session

        return None

    def is_station_online(self, station: dict | None) -> bool:
        if station is None:
            return False
        adapter = self._selected_adapter or LegacyAdapter()
        return adapter.is_online(station)

    def is_vehicle_connected(self, station: dict | None) -> bool:
        if station is None:
            return False
        adapter = self._selected_adapter or LegacyAdapter()
        try:
            sessions = adapter.sessions(self._transport)
        except Exception:
            sessions = []
        return adapter.is_connected(station, sessions)

    def is_vehicle_charging(self, station: dict | None) -> bool:
        if station is None:
            return False
        adapter = self._selected_adapter or LegacyAdapter()
        try:
            sessions = adapter.sessions(self._transport)
        except Exception:
            sessions = []
        return adapter.is_charging(station, sessions)

    def get_device_meta(self, station: dict) -> dict:
        adapter = self._selected_adapter or LegacyAdapter()
        return adapter.device_meta(station)

    def station_id(self, station: dict) -> str:
        adapter = self._selected_adapter or LegacyAdapter()
        return adapter.station_id(station)
