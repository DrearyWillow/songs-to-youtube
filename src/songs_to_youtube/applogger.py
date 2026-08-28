import logging
from collections.abc import Mapping
from types import TracebackType

from songs_to_youtube.const import APPLICATION

SUCCESS = 60


type SysExcInfoType = tuple[type[BaseException], BaseException, TracebackType | None] | tuple[None, None, None]
type ExcInfoType = bool | SysExcInfoType | BaseException | None
type ArgsType = tuple[object, ...] | Mapping[str, object]


class SuccessLogger(logging.Logger):
    def success(
        self,
        message: object,
        *args: ArgsType,
        exc_info: ExcInfoType = None,
        extra: dict[str, object] | None = None,
        stack: bool = False,
        stacklevel: int = 1,
    ) -> None:
        if self.isEnabledFor(SUCCESS):
            self._log(SUCCESS, message, args, exc_info=exc_info, extra=extra, stack_info=stack, stacklevel=stacklevel)


logging.addLevelName(SUCCESS, "SUCCESS")

applogger = SuccessLogger(APPLICATION)
