# -*- coding: utf-8 -*-
# cSpell: words

import collections.abc
import os
from typing import Callable, Any


def _resolve_callable(value):
    if callable(value):
        return value()
    return value


class Safe:
    @staticmethod
    def resolve_callable(value):
        return _resolve_callable(value)

    @staticmethod
    def is_sequence(value):
        return isinstance(value, collections.abc.Sequence) and not isinstance(
            value, str
        )

    @staticmethod
    def first_available(values, default=None):
        """
        Get first available (not None) value from the list or default one
        """
        if not Safe.is_sequence(values):
            values = [values]

        for value in values:
            v = _resolve_callable(value)
            if v is not None:
                return v

        return _resolve_callable(default)

    @staticmethod
    def conditional(condition, value, default=None):
        if condition:
            return _resolve_callable(value)
        return _resolve_callable(default)

    @staticmethod
    def to_list(values, mapper: Callable[[Any], Any] | None = None):
        if values is None:
            return []

        if mapper is None:
            mapper = lambda v: v

        if Safe.is_sequence(values):
            result = []
            for r in values:
                result += Safe.to_list(r, mapper)
            return result
        return [mapper(values)]

    @staticmethod
    def to_string_list(values):
        return Safe.to_list(values, Safe.stringify)


    @staticmethod
    def stringify(value) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, os.PathLike):  # Path and file entries are also os.PathLike
            return str(os.fspath(value))
        return str(value)
