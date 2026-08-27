import posixpath
from contextlib import suppress
from typing import cast

import mutagen
from mutagen import FileType, easyid3, easymp4, flac, id3
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4
from mutagen.mp4 import MP4Tags
from PySide6.QtCore import QByteArray, QDir, QIODeviceBase, QTemporaryFile

from songs_to_youtube.const import APPLICATION
from songs_to_youtube.log import applogger
from songs_to_youtube.utils import make_value_qt_safe

type MetadataValue = str | bytes | list[str] | list[bytes]
type MetadataTags = dict[str, MetadataValue]


class MetadataFile(FileType):
    tags: MetadataTags | None


# can expand these if wanted
EasyMP4.RegisterTextKey("url", "purl")
EasyMP4.RegisterTextKey("wwwaudiofile", "----:com.apple.iTunes:WWWAUDIOFILE")


class Metadata:
    def __init__(self, song_path: str) -> None:
        self.pictures: list[bytes] = []
        self.path = song_path
        self.tags: dict[str, str] = {}
        try:
            self.load_song(song_path)
        except Exception as err:
            applogger.error(f"Could not load metadata for {song_path}: {err.__class__}: {err}")

    def load_song(self, path: str) -> None:
        file: MetadataFile | None = mutagen.File(path, easy=True)
        raw_file: FileType | None = mutagen.File(path)
        applogger.debug(file)

        if file is None or file.tags is None:
            self.apply_file_info(file)
            return

        applogger.debug(f"Tags: {file.keys()}")
        self.apply_tag_items(file)

        if isinstance(file.tags, easyid3.EasyID3):
            if raw_file is not None:
                self.apply_id3_tags(raw_file.tags)
                file = raw_file

        elif isinstance(file.tags, id3.ID3):
            self.apply_id3_tags(file.tags)
            if raw_file is not None:
                self.apply_id3_id3_tags(raw_file.tags)
                file = raw_file

        elif isinstance(file.tags, easymp4.EasyMP4Tags):
            if raw_file is not None:
                self.apply_easy_mp4_tags(raw_file.tags)
                file = raw_file

        elif isinstance(file, flac.FLAC):
            self.apply_flac(file)

        self.apply_file_info(file)

    def apply_tag_items(self, file: MetadataFile) -> None:
        if file.tags is None:
            return

        for key, value in file.tags.items():
            if isinstance(value, list):
                safe_value = [v.decode("utf-8") if isinstance(v, bytes) else v for v in value]
            elif isinstance(value, bytes):
                safe_value = value.decode("utf-8")
            else:
                safe_value = value
            self.tags[key] = make_value_qt_safe(safe_value)

    def apply_id3_tags(self, tags: id3.ID3) -> None:
        for key in tags:
            if key.startswith(("WOAF", "WAF")):
                self.tags["website"] = make_value_qt_safe(tags[key])
            if key.startswith("COM"):
                # load comment data here since comment frame keys have
                # language suffix we can't just register text key COMM
                self.tags["comment"] = make_value_qt_safe(tags[key])
            if key.startswith(("APIC", "PIC")):
                # get cover art
                self.pictures.append(tags[key].data)

    def apply_id3_id3_tags(self, tags: id3.ID3) -> None:
        for key, getter in EasyID3.Get.items():
            with suppress(KeyError):
                value = getter(tags, key)
                self.tags[key] = make_value_qt_safe(value)

    def apply_easy_mp4_tags(self, tags: MP4Tags) -> None:
        if "covr" in tags:
            for art in tags["covr"]:
                self.pictures.append(bytes(art))

    def apply_flac(self, file: flac.FLAC) -> None:
        for picture in cast("list[flac.MetadataBlock]", file.pictures):
            self.pictures.append(cast("bytes", picture.data))

    def apply_file_info(self, file: FileType | None) -> None:
        if file is not None and file.info:
            for key, value in vars(file.info).items():
                self.tags[key] = make_value_qt_safe(value)

    def get_cover_art(self) -> str | None:
        # extract cover art if it exists
        if len(self.pictures) > 0:
            art_bytes = QByteArray(self.pictures[0])
            cover = QTemporaryFile(posixpath.join(QDir().tempPath(), APPLICATION, "XXXXXX.cover"))
            cover.setAutoRemove(False)
            cover.open(QIODeviceBase.OpenModeFlag.WriteOnly)
            cover.write(art_bytes)
            cover.close()
            return cover.fileName()
        return None

    def get_tags(self) -> dict[str, str]:
        return self.tags
