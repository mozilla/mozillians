from functools import partial


def _set_attribute_func(function, attribute, value):
    """Helper to set attributes to func and methods."""
    orig_func = function
    while isinstance(orig_func, partial):
        orig_func = orig_func.func
    setattr(orig_func, attribute, value)


def allow_public(function):
    """Allow view to be accessed by anonymous users."""
    _set_attribute_func(function, '_allow_public', True)
    return function


def allow_unvouched(function):
    """Allow view to be accessed by unvouched users."""
    _set_attribute_func(function, '_allow_unvouched', True)
    return function
