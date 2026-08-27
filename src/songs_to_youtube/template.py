from re import Match
from string import Template

from pathvalidate import sanitize_filename


class SettingTemplate(Template):
    # template placeholders are of the form ~{key}
    # can be escaped by writing ~~{key}
    delimiter = "~"

    # placeholder must be surrounded by braces
    idpattern = None  # pyright: ignore[reportAssignmentType]

    # key can be anything without braces
    braceidpattern = r"[^{}]*"

    def safe_substitute(self, _: str | None, /, **kws: str) -> str:
        mapping: dict[str, str] = kws
        two = 2

        # Helper function for .sub()
        def convert(mo: Match[str]) -> str:
            named = mo.group("named") or mo.group("braced")
            if named is not None:
                for arg in named.split("|"):
                    if arg in mapping:
                        return str(mapping[arg])
                    if len(arg) >= two and arg[0] == '"' and arg[-1] == '"':
                        # string literal
                        return arg[1:-1]
                    if len(arg) >= two and arg[0] == "<" and arg[-1] == ">":
                        # make value filename-safe
                        arg_ = arg[1:-1]
                        if arg_ in mapping:
                            return sanitize_filename(str(mapping[arg_]))
                        return "INVALID"
                return mo.group()
            if mo.group("escaped") is not None:
                return self.delimiter
            if mo.group("invalid") is not None:
                return mo.group()
            raise ValueError("Unrecognized named group in pattern", self.pattern)

        return self.pattern.sub(convert, self.template)
