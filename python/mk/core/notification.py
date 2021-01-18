# -*- coding: utf-8 -*-
# cSpell: words Sosumi pync icns

from typing import Optional
from enum import Enum
import pync
from .fs import Path
from .misc import Safe


# valid for macOS currently
class NotificationSound(Enum):
    ERROR = "Sosumi"
    SUCCESS = "Glass"


class NotificationConfig:
    def __init__(
        self, 
        sound: NotificationSound = None,
        icon=None   # ='/Applications/xxx.app/Contents/Resources/yyy.icns',
    ):
        self.sound = sound
        self.icon = icon


def show_notification(
    message: str,
    config: Optional[NotificationConfig],
    title: str = None,
    subtitle: str = None,
):
    sound = Safe.conditional(config, lambda: config.sound)
    icon = Safe.conditional(config, lambda: config.icon)

    args = {}
    if title is not None:
        args["title"] = title
    if subtitle is not None:
        args["subtitle"] = subtitle
    if sound is not None:
        args["sound"] = sound.value
    if icon is not None:
        args["appIcon"] = Path(icon).fspath

    pync.notify(message, **args)
