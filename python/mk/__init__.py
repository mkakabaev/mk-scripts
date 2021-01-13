#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# cSpell: words

import sys

from .core import * 

if sys.version_info < (3, 7, 0):
    die(f'Python 3.7+ version is required, the current is {sys.version}.')

__all__ = [
    "Console", "ConsoleStyle",
    "Path", "FSEntry", "File", "Directory",
    "Script", "die", "success",
    "DateTime", "DateTimeFormat", "TimeCounter", "Duration", "DurationFormat",
    "NotificationConfig", "show_notification",
    "Assets",
    "Runner"
]
