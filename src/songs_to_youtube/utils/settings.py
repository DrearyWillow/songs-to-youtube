from PySide6.QtCore import QSettings

from songs_to_youtube.const import ORGANIZATION, SETTINGS_FILENAME
from songs_to_youtube.utils import resource_path


def get_settings() -> QSettings:
    """Returns the QSettings for this application"""
    settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, ORGANIZATION, SETTINGS_FILENAME)
    # for some reason this doesn't work when the settings are first initialized so we do this
    return QSettings(settings.fileName(), QSettings.Format.IniFormat)


def get_setting(setting: str, settings: QSettings | None = None) -> str:
    """Returns the value of the given setting"""
    if settings is None:
        settings = get_settings()
    if not settings.contains(setting):
        # try to load from default settings
        defaults = QSettings(resource_path("config/default.ini"), QSettings.Format.IniFormat)
        if not defaults.contains(setting):
            msg = f"Setting {setting} does not exist"
            raise ValueError(msg)
        return defaults.value(setting)
    return settings.value(setting)
