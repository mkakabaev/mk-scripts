# -*- coding: utf-8 -*-
# cSpell: words

def _unresolved(method_name):
    raise Exception(f"Dependency error: {method_name}() is not resolved")


class Dependencies: 
    die = lambda s: _unresolved("int_die")


def int_die(s):
    Dependencies.die(s)
