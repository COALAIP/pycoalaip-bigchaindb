#!/usr/bin/env python

from pytest import mark, raises
from tests.utils import bdb_transaction_test, poll_result


def test_plugin_type_is_bigchaindb(plugin):
    assert plugin.type == 'BigchainDB'


def test_init_connects_to_driver(plugin):
    from bigchaindb_driver import BigchainDB
    assert isinstance(plugin.driver, BigchainDB)


def test_generate_user(plugin):
    user = plugin.generate_user()
    assert isinstance(user['verifying_key'], str)
    assert isinstance(user['signing_key'], str)


@mark.parametrize('model_name', [
    'manifestation_model_jsonld',
    'manifestation_model_json'
])
def test_save_model(plugin, bdb_driver, model_name, alice_keypair, request):
    model_data = request.getfixturevalue(model_name)
    tx_id = plugin.save(model_data, user=alice_keypair)

    # Poll BigchainDB for the result
    tx = poll_result(
        lambda: bdb_driver.transactions.retrieve(tx_id),
        bdb_transaction_test)

    tx_payload = tx['transaction']['asset']['data']
    tx_new_owners = tx['transaction']['conditions'][0]['owners_after']
    assert tx['id'] == tx_id
    assert tx_payload == model_data
    assert tx_new_owners[0] == alice_keypair['verifying_key']


def test_save_raises_entity_creation_error_on_creation_error(
        monkeypatch, plugin, manifestation_model_json, alice_keypair):
    from bigchaindb_driver.exceptions import BigchaindbException
    from coalaip.exceptions import EntityCreationError

    def mock_driver_error(*args, **kwargs):
        raise BigchaindbException()
    monkeypatch.setattr(plugin.driver.transactions, 'prepare',
                        mock_driver_error)

    with raises(EntityCreationError):
        plugin.save(manifestation_model_json, user=alice_keypair)


def test_save_raises_entity_creation_error_on_missing_key(monkeypatch, plugin,
                                                          manifestation_model_json,
                                                          alice_keypair):
    from bigchaindb_driver.exceptions import MissingSigningKeyError
    from coalaip.exceptions import EntityCreationError

    def mock_driver_error(*args, **kwargs):
        raise MissingSigningKeyError()
    monkeypatch.setattr(plugin.driver.transactions, 'fulfill',
                        mock_driver_error)

    with raises(EntityCreationError):
        plugin.save(manifestation_model_json, user=alice_keypair)


def test_save_raises_persistence_error_on_error(monkeypatch, plugin,
                                                manifestation_model_json,
                                                alice_keypair):
    """If bigchaindb-driver returns an error not caught in
    pycoalaip-bigchaindb, convert it into a
    `~coalaip.exceptions.PersistenceError`.
    """
    from coalaip.exceptions import PersistenceError

    def mock_driver_error(*args, **kwargs):
        raise Exception()
    monkeypatch.setattr(plugin.driver.transactions, 'prepare',
                        mock_driver_error)

    with raises(PersistenceError):
        plugin.save(manifestation_model_json, user=alice_keypair)


def test_save_raises_entity_creation_error_on_transport_error(
        monkeypatch, plugin, manifestation_model_json, alice_keypair):
    from bigchaindb_driver.exceptions import TransportError
    from coalaip.exceptions import EntityCreationError

    def mock_driver_error(*args, **kwargs):
        raise TransportError()
    monkeypatch.setattr(plugin.driver.transactions, 'send',
                        mock_driver_error)

    with raises(EntityCreationError):
        plugin.save(manifestation_model_json, user=alice_keypair)


def test_save_raises_entity_creation_error_on_connection_error(
        monkeypatch, plugin, manifestation_model_json, alice_keypair):
    from bigchaindb_driver.exceptions import ConnectionError
    from coalaip.exceptions import EntityCreationError

    def mock_driver_error(*args, **kwargs):
        raise ConnectionError()
    monkeypatch.setattr(plugin.driver.transactions, 'send',
                        mock_driver_error)

    with raises(EntityCreationError):
        plugin.save(manifestation_model_json, user=alice_keypair)


def test_get_status(plugin, created_manifestation):
    tx_id = created_manifestation['id']

    # Poll BigchainDB for the initial status
    poll_result(
        lambda: plugin.get_status(tx_id),
        lambda result: result['status'] in (
            'valid', 'invalid', 'undecided', 'backlog'))

    # Poll BigchainDB until the transaction validates; will fail test if the
    # transaction's status doesn't become valid by the end of the timeout
    # period.
    poll_result(
        lambda: plugin.get_status(tx_id),
        lambda result: result['status'] == 'valid')


def test_get_status_raises_not_found_error_on_not_found(monkeypatch, plugin,
                                                        created_manifestation):
    from bigchaindb_driver.exceptions import NotFoundError
    from coalaip.exceptions import EntityNotFoundError

    def mock_driver_not_found_error(*args, **kwargs):
        raise NotFoundError()
    monkeypatch.setattr(plugin.driver.transactions, 'status',
                        mock_driver_not_found_error)

    with raises(EntityNotFoundError):
        plugin.get_status(created_manifestation['id'])


def test_get_status_raises_persistence_error_on_error(monkeypatch, plugin,
                                                      created_manifestation):
    from coalaip.exceptions import PersistenceError

    def mock_driver_error(*args, **kwargs):
        raise Exception()
    monkeypatch.setattr(plugin.driver.transactions, 'status',
                        mock_driver_error)

    with raises(PersistenceError):
        plugin.get_status(created_manifestation['id'])


def test_load_model(plugin, persisted_manifestation):
    tx_id = persisted_manifestation['id']
    loaded_transaction = plugin.load(tx_id)
    assert loaded_transaction == persisted_manifestation['transaction']['asset']['data']


def test_load_model_raises_not_found_error_on_not_found(
        monkeypatch, plugin, created_manifestation):
    from bigchaindb_driver.exceptions import NotFoundError
    from coalaip.exceptions import EntityNotFoundError

    def mock_driver_not_found_error(*args, **kwargs):
        raise NotFoundError()
    monkeypatch.setattr(plugin.driver.transactions, 'retrieve',
                        mock_driver_not_found_error)

    with raises(EntityNotFoundError):
        plugin.load(created_manifestation['id'])


def test_load_model_raises_persistence_error_on_error(monkeypatch, plugin,
                                                      created_manifestation):
    from coalaip.exceptions import PersistenceError

    def mock_driver_error(*args, **kwargs):
        raise Exception()
    monkeypatch.setattr(plugin.driver.transactions, 'retrieve',
                        mock_driver_error)

    with raises(PersistenceError):
        plugin.load(created_manifestation['id'])


@mark.skip(reason='transfer() not implemented yet')
@mark.parametrize('model_name', [
    'rights_assignment_model_jsonld',
    'rights_assignment_model_json'
])
def test_transfer(plugin, bdb_driver, persisted_manifestation, model_name,
                  alice_keypair, bob_keypair, request):
    model_data = request.getfixturevalue(model_name)
    tx_id = persisted_manifestation['id']

    transfer_tx_id = plugin.transfer(tx_id, model_data,
                                     from_user=alice_keypair,
                                     to_user=bob_keypair)

    # Poll BigchainDB for the result
    transfer_tx = poll_result(
        lambda: bdb_driver.transactions.retrieve(transfer_tx_id),
        bdb_transaction_test)

    transfer_tx_fulfillments = transfer_tx['transaction']['fulfillments']
    transfer_tx_conditions = transfer_tx['transaction']['conditions']
    transfer_tx_prev_owners = transfer_tx_fulfillments[0]['owners_before']
    transfer_tx_new_owners = transfer_tx_conditions[0]['owners_after']
    assert transfer_tx['id'] == tx_id
    assert transfer_tx_prev_owners[0] == alice_keypair['verifying_key']
    assert transfer_tx_new_owners[0] == bob_keypair['verifying_key']
