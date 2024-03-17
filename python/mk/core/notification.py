# -*- coding: utf-8 -*-
# cSpell: words Sosumi pync icns

from typing import Optional
from enum import Enum
import pync
from .fs import Path
from .misc import Safe


# valid for macOS currently. Copy your sounds to ~/Library/Sounds. I personally use old (prior to BigSur) Sosumi.aiff and Glass.aiff 
class NotificationSound(Enum):
    ERROR = "MKError"
    SUCCESS = "MKSuccess"


class NotificationConfig:
    def __init__(
        self, 
        sound: NotificationSound | None = None,
        icon=None   # ='/Applications/xxx.app/Contents/Resources/yyy.icns',
    ):
        self.sound = sound
        self.icon = icon


def show_notification(
    message: str,
    config: NotificationConfig,
    title: str | None = None,
    subtitle: str | None = None,
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
