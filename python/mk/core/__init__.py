# -*- coding: utf-8 -*-
# cSpell: words

from .console import Console
from .fs import *
from .misc import *
from .to_string_builder import *
from .runner import *
from .script import *
from .time_utils import *
from .notification import *
from ._internal import *
from .assets import *

__all__ = [
    "Console", "ConsoleStyle",
    "Path", "FSEntry", "File", "Directory",
    "ToStringBuilder", "ReprBuilderMixin",
    "Runner",
    "Script", "die", "success",
    "DateTime", "DateTimeFormat", "TimeCounter", "Duration", "DurationFormat",
    "NotificationConfig", "show_notification",
    "Safe",
    "Assets", "IconAsset",
    "strip_comments",
]

# dependencies injection
Dependencies.die = Script.die
