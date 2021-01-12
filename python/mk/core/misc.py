# -*- coding: utf-8 -*-
# cSpell: words

import collections.abc
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
        return isinstance(value, collections.abc.Sequence) and not isinstance(value, str)

    @staticmethod
    def first_available(values, default=None):
        '''
            Get first available (not None) value from the list or default one
        '''
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
    def to_list(values, mapper: Callable[[Any], Any] = None):

        if values is None:
            return []

        if mapper is None:
            mapper = lambda v: v 

        if Safe.is_sequence(values):
            return list(map(mapper, values))

        return [mapper(values)]
