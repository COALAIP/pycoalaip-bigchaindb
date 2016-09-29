from pytest import raises


def test_reraise_as_persistence_error():
    from coalaip.exceptions import PersistenceError
    from coalaip_bigchaindb.utils import reraise_as_persistence_error_if_not
    mock_type_error = TypeError()

    @reraise_as_persistence_error_if_not(ValueError)
    def raises_type_error():
        raise mock_type_error

    # Raises PersistenceError with the TypeError inside of it
    with raises(PersistenceError) as excinfo:
        raises_type_error()
    assert excinfo.value.error == mock_type_error


def test_reraise_as_persistence_error_raises_allowed():
    from coalaip_bigchaindb.utils import reraise_as_persistence_error_if_not
    mock_type_error = TypeError()

    @reraise_as_persistence_error_if_not(TypeError)
    def raises_type_error():
        raise mock_type_error

    # Raises the allowed TypeError
    with raises(TypeError) as excinfo:
        raises_type_error()
    assert excinfo.value == mock_type_error
