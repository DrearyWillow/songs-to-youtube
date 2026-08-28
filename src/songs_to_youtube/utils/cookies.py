import os
import posixpath
import shutil
from http.cookiejar import FileCookieJar, MozillaCookieJar
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from songs_to_youtube.utils.json_cookie_jar import JSONFileCookieJar


def get_cookie_path_from_username(username: str) -> str:
    appdata_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    general_cookies_folder_path = posixpath.join(appdata_path, "cookies")
    Path(general_cookies_folder_path).mkdir(exist_ok=True, parents=True)
    return posixpath.join(general_cookies_folder_path, username)


def get_all_usernames() -> list[str]:
    appdata_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    general_cookies_folder_path = posixpath.join(appdata_path, "cookies")
    Path(general_cookies_folder_path).mkdir(exist_ok=True, parents=True)
    return next(os.walk(general_cookies_folder_path))[1]


def remove_user_cookies(username: str) -> None:
    cookie_folder = get_cookie_path_from_username(username)
    shutil.rmtree(cookie_folder)


def save_user_cookies(username: str, cookie_file: str) -> None:
    cookie_folder = get_cookie_path_from_username(username)
    Path(cookie_folder).mkdir(exist_ok=True, parents=True)
    if cookie_file.endswith("json"):
        destination_path = posixpath.join(cookie_folder, "youtube.com.json")
    else:
        destination_path = posixpath.join(cookie_folder, "cookies.txt")
    shutil.copyfile(cookie_file, destination_path)


def get_cookie_jar_for_username(username: str) -> FileCookieJar:
    cookie_dir = get_cookie_path_from_username(username)
    txt_cookie_path = next(Path(cookie_dir).glob("*.txt"), None)
    json_cookie_path = next(Path(cookie_dir).glob("*.json"), None)
    if txt_cookie_path:
        return MozillaCookieJar(txt_cookie_path)
    if json_cookie_path:
        return JSONFileCookieJar(json_cookie_path)
    msg = f"No cookie files matching *.txt or *.json found in {cookie_dir}"
    raise FileNotFoundError(msg)
