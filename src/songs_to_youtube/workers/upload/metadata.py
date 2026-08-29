from typing import TYPE_CHECKING

from youtube_up import Metadata as YTMetadata
from youtube_up import Playlist as YTPlaylist
from youtube_up import PrivacyEnum

from songs_to_youtube.utils.misc import SETTINGS_VALUES

if TYPE_CHECKING:
    from songs_to_youtube.panes.tree.widget_item.album import AlbumTreeWidgetItem
    from songs_to_youtube.panes.tree.widget_item.song import SongTreeWidgetItem


def make_metadata_safe(metadata: YTMetadata) -> YTMetadata:
    metadata.title = metadata.title[:100]
    metadata.description = metadata.description[:5000]
    metadata.title = metadata.title.replace("<", "＜").replace(">", "＞")  # ruff: ignore[ambiguous-unicode-character-string]
    metadata.description = metadata.description.replace("<", "＜").replace(">", "＞")  # ruff: ignore[ambiguous-unicode-character-string]
    return metadata


def get_album_metadata(album: AlbumTreeWidgetItem) -> YTMetadata:
    album.before_upload()
    privacy = album.get("videoVisibilityAlbum")
    notify_subs = album.get("notifySubsAlbum") == SETTINGS_VALUES.CheckBox.CHECKED
    tags = album.get("videoTagsAlbum").split(",") if album.get("videoTagsAlbum") else []
    return make_metadata_safe(
        YTMetadata(
            album.get("videoTitleAlbum"),
            album.get("videoDescriptionAlbum"),
            PrivacyEnum(privacy),
            made_for_kids=False,
            tags=tuple(tags),
            publish_to_feed=notify_subs,
        )
    )


def get_song_metadata(song: SongTreeWidgetItem) -> YTMetadata:
    song.before_upload()
    privacy = song.get("videoVisibility")
    notify_subs = song.get("notifySubs") == SETTINGS_VALUES.CheckBox.CHECKED
    tags = song.get("videoTags").split(",") if song.get("videoTags") else []
    playlist_names = song.get("playlistName").split("\n")

    playlists = [
        YTPlaylist(
            name,
            privacy=PrivacyEnum(privacy),
            create_if_title_exists=False,
            create_if_title_doesnt_exist=True,
        )
        for name in playlist_names
        if name
    ]

    return make_metadata_safe(
        YTMetadata(
            song.get("videoTitle"),
            song.get("videoDescription"),
            PrivacyEnum(privacy),
            made_for_kids=False,
            tags=tuple(tags),
            playlists=playlists,
            publish_to_feed=notify_subs,
        )
    )
