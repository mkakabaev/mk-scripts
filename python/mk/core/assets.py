# -*- coding: utf-8 -*-
# cSpell: words

import inspect
import pathlib
from .fs import Directory, Path

class IconAsset:
    def __init__(self, path):
        self.path = Path(path)

    # os.PathLike implementation
    def __fspath__(self):
        return self.path.fspath        

class Assets:

    @classmethod
    def _init(cls):
        p = pathlib.Path(inspect.getframeinfo(inspect.currentframe()).filename).resolve().parent.parent.parent.parent.joinpath('assets')
        cls._directory = Directory(p, must_exist=True, create_if_needed=False)

    @classmethod
    def get_icon(cls, icon_name: str) -> Path:
        return IconAsset(Path([cls._directory, f'{icon_name}.png']))


Assets._init()  # pylint: disable=protected-access
