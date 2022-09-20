import re
from typing import Any, Optional, Union

import httpx as request
from arguments import ArgumentsConstructor


class TorrentClient:

    _torrent_ids: list[int]
    _headers: dict[str, Any] = {
        "server": "Transmission",
        "x-transmission-session-id": "",
        "content-type": "text/html; charset=ISO-8859-1",
    }

    def __init__(
        self,
        constructor: ArgumentsConstructor,
        host: str = "http://localhost:9091/transmission/rpc",
    ) -> None:
        self._host = host
        self.constructor = constructor

        self._connect()

    @property
    def url(self) -> str:
        return self._host

    @property
    def _session_id(self) -> Optional[str]:
        return self._headers.get("x-transmission-session-id")

    @_session_id.setter
    def _session_id(self, session_id) -> None:
        return self._headers.update({"x-transmission-session-id": session_id})

    def _update_sesion_id(self) -> str:
        """Use regex to find the 48 character string from 409 error response."""
        make_409_error = request.post(self.url, json={}).text
        split_error = make_409_error.split()
        session_id = split_error[-1]
        pattern = r"[a-zA-Z0-9][a-zA-Z0-9\.\-]{20,50}[a-zA-Z0-9]"
        final_session_id = re.search(pattern, session_id)
        self._session_id = final_session_id.group(0)  # type: ignore
        return self._session_id

    def _connect(self) -> None:
        """Connect to transmission/rpc."""
        self._update_sesion_id()

        response = request.post(self.url, json=self.constructor._arguments, headers=self._headers)

        if response.status_code != 200:
            raise Exception(f"Something went wrong:\nStatus Code: {response.status_code}\n{response.text}")

    def _handle_post_response(self, arguments: dict[str, str]) -> Any:
        response = request.post(self.url, json=arguments, headers=self._headers)

        if response.status_code != 200:
            raise Exception(f"Something went wrong:\nStatus Code: {response.status_code}\n{response.text}")

        return response.json()

    # def get_torrent_ids(self) -> list[int]:
    #     args = self.constructor._get_fields("id")
    #     response = self._handle_post_response(arguments=args)
    #     torrents = response["arguments"]["torrents"]
    #     return [torrent["id"] for torrent in torrents]

    def _get_fields(self, fields: Union[str, list[str]]) -> list[Any]:
        args = self.constructor._get_fields(fields)
        response = self._handle_post_response(arguments=args)

        torrents = response["arguments"]["torrents"]

        if isinstance(fields, str):
            return [torrent[fields] for torrent in torrents]

        return torrents
