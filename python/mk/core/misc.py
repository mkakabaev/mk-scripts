# -*- coding: utf-8 -*-
# cSpell: words

import collections.abc
import os
from typing import Callable, Any, Optional, TypeVar, Union

T = TypeVar('T')

def _resolve_callable(value: Union[T, Callable[[], T]]) -> T:
    if callable(value):
        return value() # type: ignore
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
    def conditional(condition, value: T, default: Optional[T] = None) -> Optional[T]:
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


def _handle_code_line(s: str, pad: str):
    state = "code"
    while True:
        block_index = s.find("/*")
        line_index = s.find("//")

        # nothing found,
        if block_index < 0 and line_index < 0:
            break

        # strip line comments if any
        if line_index >= 0 and (line_index < block_index or block_index < 0):
            s = s[:line_index] + pad * (len(s) - line_index)
            continue

        # strip block comments if any
        if block_index >= 0:
            block_end_index = s.find("*/")
            # strip single-line completed block comments
            if block_end_index >= 0:
                s = (
                    s[:block_index]
                    + pad * (block_end_index - block_index + 2)
                    + s[block_end_index + 2 :]
                )
                continue
            # start multi-line block comment
            s = s[:block_index] + pad * (len(s) - block_index)
            state = "block_comment"
            break
    return s, state


def strip_comments(content: str, pad=" ") -> list[str]:
    """
    Parse multiline code and strip C-Style comments from it.
    Return list of lines with comments replaced by padding.
    """
    state = "code"
    result = []

    for s in content.split("\n"):
        if state == "code":
            s1, state1 = _handle_code_line(s, pad)
            result.append(s1)
            state = state1
            continue

        if state == "block_comment":
            block_end_index = s.find("*/")
            if block_end_index < 0:  # still in block comment
                result.append(pad * len(s))
                continue
            # block comment ends
            s = pad * block_end_index + s[block_end_index + 2 :]
            s1, state1 = _handle_code_line(s, pad)
            result.append(s1)
            state = state1
            continue

    return result
