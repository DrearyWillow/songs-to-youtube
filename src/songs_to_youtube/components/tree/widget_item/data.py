import pathlib

from songs_to_youtube.applogger import applogger
from songs_to_youtube.components.tree.tree_widget_item import SongTreeWidgetItem
from songs_to_youtube.components.tree.widget_item.template import SettingTemplate
from songs_to_youtube.const import APPLICATION_IMAGES, SETTINGS_VALUES, TreeWidgetType
from songs_to_youtube.field import InputField
from songs_to_youtube.metadata import Metadata
from songs_to_youtube.utils import get_setting


class TreeWidgetItemData:
    def _set_application_values(self, item_type: TreeWidgetType, **kwargs: str) -> None:
        self.dict: dict[str, str] = {}
        app_fields = InputField.SONG_FIELDS if item_type == TreeWidgetType.SONG else InputField.ALBUM_FIELDS
        for field in set(kwargs) | app_fields:
            # set all mandatory settings to their defaults if not
            # specified in the parameters
            # and any extra settings specified in the parameters
            self.dict[field] = kwargs[field] if field in kwargs else get_setting(field)

            if field == "coverArt" and self.dict[field] in APPLICATION_IMAGES:
                # convert resource path to real file path for ffmpeg
                self.dict[field] = APPLICATION_IMAGES[get_setting(field)]

    def __init__(
        self, item_type: TreeWidgetType, songs: list["SongTreeWidgetItem"] | None = None, **kwargs: str
    ) -> None:
        # metadata values
        self.metadata: Metadata | None = None

        # application values
        self._set_application_values(item_type, **kwargs)

        # add song metadata
        if item_type == TreeWidgetType.SONG:
            self._add_song_metadata()
        # album gets metadata from children
        # song metadata is stored as song.<key>
        # e.g. song.album would be the album name
        #
        # we will only get metadata from one song
        # because the album shouldn't care about
        # the varying metadata values for the songs
        # such as title or track number
        elif songs:
            for song in songs:
                for key, value in song.to_dict().items():
                    self.dict[f"song.{key}"] = value
                break

        self.update_fields()

    def _add_song_metadata(self) -> None:
        try:
            self.metadata = Metadata(self.dict["song_path"])
            cover_file = self._get_cover_file()
            self._set_cover_art(cover_file, self.metadata)
        except Exception as e:
            applogger.warning("Error while getting cover art")
            applogger.warning(e)
            applogger.warning(self.dict["song_path"])

    def _get_cover_file(self) -> str | None:
        cover_exts = {".jpg", ".jpeg", ".bmp", ".gif", ".png"}
        cover_names = {"cover", "folder", "front", pathlib.Path(self.dict["song_file"]).stem}
        for path in pathlib.Path(self.dict["song_dir"]).iterdir():
            if path.is_file() and path.stem.lower() in cover_names and path.suffix.lower() in cover_exts:
                applogger.info("Found cover file %s", path)
                return str(path)
        return None

    def _set_cover_art(self, cover_file: str | None, metadata: Metadata) -> None:
        if get_setting("preferCoverArtFile") == SETTINGS_VALUES.CheckBox.CHECKED and cover_file:
            self.set_value("coverArt", cover_file)
        elif get_setting("extractCoverArt") == SETTINGS_VALUES.CheckBox.CHECKED:
            if (cover_path := metadata.get_cover_art()) is not None:
                self.set_value("coverArt", cover_path)
            elif cover_file:
                self.set_value("coverArt", cover_file)

    def update_fields(self) -> None:
        for field, value in self.dict.items():
            self.set_value(field, value)

    def to_dict(self) -> dict[str, str]:
        return {
            **self.dict,
            **(self.metadata.get_tags() if self.metadata is not None else {}),
        }

    def get_value(self, field: str) -> str:
        return self.dict[field]

    def get_metadata_value(self, key: str) -> str | None:
        if self.metadata and key in self.metadata.get_tags():
            return self.metadata.get_tags()[key]
        return None

    def set_value(self, field: str, value: str) -> None:
        # replace {variable} with value from metadata
        value = SettingTemplate(value).safe_substitute(None, **self.to_dict())
        self.dict[field] = value

    def get_duration_ms(self) -> float:
        if self.metadata and "length" in self.metadata.get_tags():
            duration = float(self.metadata.get_tags()["length"]) * 1000
            applogger.debug(f"Duration (ms): {duration}")
            return duration
        msg = f"Could not find duration of file {self.dict['song_path']}"
        raise ValueError(msg)

    def get_track_number(self) -> int:
        if self.metadata and "tracknumber" in self.metadata.get_tags():
            try:
                tracknumber = self.metadata.get_tags()["tracknumber"]
                if "/" in tracknumber:
                    # sometimes track number is represented as a fraction
                    tracknumber = tracknumber[: tracknumber.index("/")]
                return int(tracknumber)
            except ValueError:
                applogger.warning("Could not convert %s to int", self.metadata.get_tags()["tracknumber"])
                return 0
        return 0

    def __str__(self) -> str:
        return str(self.dict)
