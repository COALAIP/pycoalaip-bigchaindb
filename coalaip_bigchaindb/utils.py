from coalaip.exceptions import PersistenceError


def reraise_as_persistence_error_if_not(*allowed_exceptions):
    """Decorator: Reraises any exception from the wrapped function
    by wrapping it around a :exc:`coalaip.PersistenceError` unless it's
    one of the given :attr:`allowed_exceptions`.

    Args:
        *allowed_exceptions (:exc:`Exception`): Exceptions to not
            reraise with :exc:`coalaip.PersistenceError`
    """
    def decorator(func):
        def reraises_if_not(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as ex:
                if not isinstance(ex, allowed_exceptions):
                    raise PersistenceError(error=ex)
                else:
                    raise
        return reraises_if_not
    return decorator
