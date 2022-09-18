from dataclasses import dataclass
import os
import re

from transmission_rpc.torrent import Torrent


class TorrentDefault:

    STATUS = {
        0: "stopped",
        1: "check pending",
        2: "checking",
        3: "download pending",
        4: "downloading",
        5: "seed pending",
        6: "seeding",
    }

    def __init__(self, torrent: Torrent, root_dir: str) -> None:
        self.torrent = torrent
        self.root_dir = root_dir

    @staticmethod
    def is_type(torrent: Torrent) -> bool:
        return True

    @property
    def name(self) -> str:
        return self.torrent.name

    @property
    def destination_dir(self) -> str:
        return self.root_dir

    @property
    def labels(self) -> list[str]:
        return self.torrent._fields["labels"].value

    @property
    def is_finished(self) -> bool:
        return self.torrent._fields["isFinished"].value

    @property
    def status(self) -> str:
        code = self.torrent._fields["status"].value
        return self.STATUS[code]


@dataclass
class Movie(TorrentDefault):
    torrent: Torrent
    root_dir: str

    def __post_init__(self):
        super().__init__(self.torrent, self.root_dir)

    @staticmethod
    def is_type(torrent: Torrent) -> bool:
        """
        Checks if torrent is movies_pattern.

        Returns:
            bool value.
        """
        movies_pattern = r"(?P<year>\d{4})(?P<separator>.*?)(?P<resolution>\d{3,4}p)"
        movies_search = re.search(movies_pattern, torrent.name)

        if movies_search:
            return True
        return False


@dataclass
class TvShow(TorrentDefault):
    torrent: Torrent
    root_dir: str

    def __post_init__(self):
        super().__init__(self.torrent, self.root_dir)

    @staticmethod
    def is_type(torrent: Torrent) -> bool:
        season_pattern = r"\.+[Ss]+\d{1,2}"
        season_search = re.search(season_pattern, torrent.name)

        if season_search:
            return True

        return False

    @property
    def destination_dir(self) -> str:
        """Get torrent final destination."""
        season_pattern = r"\.+[Ss]+\d{1,2}"
        season_search = re.search(season_pattern, self.torrent.name)

        season = season_search.group(0).replace(".", "")  # type: ignore
        show_name = self.name[: season_search.start()].lower().replace(".", "_")  # type: ignore

        self.root_dir = os.path.join(self.root_dir, show_name)

        destination = os.path.join(self.root_dir, season.lower())
        return destination


@dataclass
class SystemOS(TorrentDefault):
    torrent: Torrent
    root_dir: str

    def __post_init__(self):
        super().__init__(self.torrent, self.root_dir)

    @staticmethod
    def is_type(torrent: Torrent) -> bool:

        if torrent.name.endswith("iso"):
            return True

        for file in torrent.files():
            if file.name.endswith("iso"):
                return True
        return False


@dataclass
class Audio(TorrentDefault):
    torrent: Torrent
    root_dir: str

    def __post_init__(self):
        super().__init__(self.torrent, self.root_dir)

    @staticmethod
    def is_type(torrent: Torrent) -> bool:
        audio_formats = ("flac", "mp3", "acc", "ogg", "m4a", "wav")
        torrent_files = torrent.files()

        if torrent_files:
            for file in torrent_files:
                if file.name.endswith(audio_formats):
                    return True
        return False


@dataclass
class Default(TorrentDefault):
    torrent: Torrent
    root_dir: str

    def __post_init__(self):
        super().__init__(self.torrent, self.root_dir)
