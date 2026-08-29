import json
import time
from http.cookiejar import Cookie, FileCookieJar
from pathlib import Path
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from io import TextIOWrapper


class JSONFileCookieJar(FileCookieJar):
    def _really_load(
        self, f: TextIOWrapper, filename: str | None, *, ignore_discard: bool, ignore_expires: bool
    ) -> None:
        now = int(time.time())
        cookies = json.load(f)
        for cookie in cookies:
            rest: dict[str, str] = {}
            if cookie.get("httpOnly"):
                rest["HTTPOnly"] = ""
            if isinstance(cookie["secure"], str):
                cookie["secure"] = cookie["secure"] == "TRUE"
            c = Cookie(
                version=0,
                name=cookie["name"],
                value=cookie["value"],
                port=None,
                port_specified=False,
                domain=cookie["domain"],
                domain_specified=True,
                domain_initial_dot=cookie["domain"].startswith("."),
                path=cookie["path"],
                path_specified=True,
                secure=cookie["secure"],
                expires=cookie["expires"] or None,
                discard=False,
                comment=None,
                comment_url=None,
                rest=rest,
            )
            if not ignore_discard and c.discard:
                continue
            if not ignore_expires and c.is_expired(now):
                continue
            self.set_cookie(c)

    @override
    def save(self, filename: str | None = None, ignore_discard: bool = False, ignore_expires: bool = False) -> None:
        now = int(time.time())
        cookies: list[dict[str, str | bool]] = []
        for cookie in self:
            domain = cookie.domain
            if not ignore_discard and cookie.discard:
                continue
            if not ignore_expires and cookie.is_expired(now):
                continue
            secure = cookie.secure
            expires = str(cookie.expires) if cookie.expires is not None else ""
            if cookie.value is None:
                name = ""
                value = cookie.name
            else:
                name = cookie.name
                value = cookie.value
            http_only = False
            if cookie.has_nonstandard_attr("HTTPOnly"):
                http_only = True
            cookies.append(
                {
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": cookie.path,
                    "expires": expires,
                    "httpOnly": http_only,
                    "secure": secure,
                }
            )

        if filename is None and self.filename is not None:
            filename = self.filename

        if filename is not None:
            with Path(filename).open("w", encoding="utf-8") as f:
                json.dump(cookies, f)
