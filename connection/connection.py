import logging
import re
from typing import Any, Optional, Union

import httpx as request

from config import Locations
from torrents import utils
from torrents.categories import TorrentWithCategory
from torrents.factory import Cataloger
from torrents.torrent import Torrent

from .arguments import Args, ArgumentsConstructor

log = utils.get_logger(logging.INFO)


class TransmissionClient:

    _torrent_ids: list[int]
    _headers: dict[str, Any] = {
        "server": "Transmission",
        "x-transmission-session-id": "",
        "content-type": "text/html; charset=ISO-8859-1",
    }

    def __init__(
        self,
        constructor: ArgumentsConstructor,
        locations: Locations,
        host: str = "http://127.0.0.1",
        port: int = 9091,
    ) -> None:
        self._host = host
        self.port = port
        self.constructor = constructor
        self.locations = locations
        self._rpc = "/transmission/rpc"

        self._connect()

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}{self._rpc}"

    @property
    def host(self) -> str:
        return self._host

    def __str__(self) -> str:
        return f"{type(self).__name__}(url={self.url})"

    def get_torrent_fields(
        self,
        torrent_id: int,
        fields: Union[str, list[str]],
    ) -> dict[str, Any]:
        """Get fields from single torrent."""
        args = self.constructor.fields(torrent_id=torrent_id, fields=fields)
        response = self._handle_post_response(arguments=args)

        data = response["arguments"]["torrents"]
        return data[0]

    def get_torrent(self, torrent_id: int) -> Torrent:
        """Get torrent with all fields."""
        args = self.constructor.fields(torrent_id=torrent_id)
        response = self._handle_post_response(arguments=args)
        data = response["arguments"]["torrents"]
        processed_torrent = utils.process_data_torrent(data[0])

        return Torrent(**processed_torrent)

    def get_torrent_and_category(self, torrent_id: int) -> TorrentWithCategory:
        raw_torrent = self.get_torrent(torrent_id)
        return Cataloger.get_category(raw_torrent, self.locations)

    def get_torrents_fields(self, fields: Union[str, list[str]]) -> list[dict[str, Any]]:
        """Get fields from all torrents."""
        args = self.constructor.fields(fields=fields)
        response = self._handle_post_response(arguments=args)
        data = response["arguments"]["torrents"]
        return data

    def get_torrents_ids(self) -> list[int]:
        ids_object = self.get_torrents_fields("id")
        return [id["id"] for id in ids_object]

    def set_labels(self, torrent: TorrentWithCategory, labels: list[str]) -> None:
        args = self.constructor.set_fields(torrent.id, "labels", labels)
        self._handle_post_response(arguments=args)
        message = "Torrent[%s] '%s' updated with labels %s."
        log.info(message, torrent.id, torrent.name, labels)

    def move_torrent_data(self, torrent: TorrentWithCategory) -> None:
        if torrent.download_dir == torrent.destination_dir:
            return
        args = self.constructor.move_torrent_query(torrent.id, torrent.destination_dir, True)
        message = "Torrent[%s] '%s' updated with location %s."
        log.info(message, torrent.id, torrent.name, torrent.destination_dir)
        self._handle_post_response(arguments=args)

    @property
    def _session_id(self) -> Optional[str]:
        return self._headers.get("x-transmission-session-id")

    @_session_id.setter
    def _session_id(self, session_id) -> None:
        return self._headers.update({"x-transmission-session-id": session_id})

    def _update_sesion_id(self) -> None:
        """Use regex to find the 48 character string from 409 error response."""
        make_409_error = request.post(self.url, json={}).text.split()[-1]
        search_pattern = r"[a-zA-Z0-9][a-zA-Z0-9\.\-]{35,50}[a-zA-Z0-9]"
        final_session_id = re.search(search_pattern, make_409_error).group(0)  # type: ignore
        self._session_id = final_session_id

    def _connect(self) -> None:
        """Connect to transmission/rpc."""
        self._update_sesion_id()

        response = request.post(self.url, json=self.constructor.arguments, headers=self._headers)
        if response.status_code != 200:
            raise Exception(f"Something went wrong:\nStatus Code: {response.status_code}\n{response.text}")

        log.info("Connected to %s\n", self.url)

    def _handle_post_response(self, arguments: Args) -> Any:
        response = request.post(self.url, json=arguments, headers=self._headers)

        if response.status_code != 200:
            raise Exception(f"Something went wrong:\nStatus Code: {response.status_code}\n{response.text}")

        return response.json()

    def _validate_torrent_id(self, torrent_id) -> None:
        torrent_ids = self.get_torrents_ids()
        if torrent_id not in torrent_ids:
            raise ValueError(f"TorrentID '{torrent_id}' not found.")
