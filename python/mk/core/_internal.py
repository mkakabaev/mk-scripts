# -*- coding: utf-8 -*-
# cSpell: words
from typing import NoReturn, Callable

def _unresolved(method_name):
    raise Exception(f"Dependency error: {method_name}() is not resolved")

class Dependencies: 
    die: Callable[[str], NoReturn] = lambda s: _unresolved("int_die")

def int_die(s) -> NoReturn: # type: ignore
    Dependencies.die(s)
