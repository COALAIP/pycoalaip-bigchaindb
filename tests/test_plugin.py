#!/usr/bin/env python

from pytest import mark, raises
from tests.utils import (
    make_transfer_tx,
    poll_bdb_transaction,
    poll_bdb_transaction_valid,
    poll_result,
)


def test_plugin_type_is_bigchaindb(plugin):
    assert plugin.type == 'BigchainDB'


def test_init_connects_to_driver(plugin):
    from bigchaindb_driver import BigchainDB
    assert isinstance(plugin.driver, BigchainDB)


def test_generate_user(plugin):
    user = plugin.generate_user()
    assert isinstance(user['public_key'], str)
    assert isinstance(user['private_key'], str)


def test_get_history(plugin, bdb_driver, alice_keypair, bob_keypair,
                     persisted_manifestation):
    # Transfer to Bob
    transfer_to_bob_tx = make_transfer_tx(bdb_driver,
                                          input_tx=persisted_manifestation,
                                          recipients=bob_keypair['public_key'])
    transfer_to_bob_tx = bdb_driver.transactions.fulfill(
        transfer_to_bob_tx, private_keys=alice_keypair['private_key'])
    bdb_driver.transactions.send(transfer_to_bob_tx)

    poll_bdb_transaction_valid(bdb_driver, transfer_to_bob_tx['id'])

    # Transfer back to Alice
    transfer_back_to_alice_tx = make_transfer_tx(bdb_driver,
                                                 input_tx=transfer_to_bob_tx,
                                                 recipients=alice_keypair['public_key'])
    transfer_back_to_alice_tx = bdb_driver.transactions.fulfill(
        transfer_back_to_alice_tx, private_keys=bob_keypair['private_key'])
    bdb_driver.transactions.send(transfer_back_to_alice_tx)

    poll_bdb_transaction_valid(bdb_driver, transfer_back_to_alice_tx['id'])

    # Test that we get all these transactions back
    # Note that the CREATE transaction's id is the id of the entity
    try:
        history = plugin.get_history(persisted_manifestation['id'])
    except Exception as ex:
        print(ex)
        raise

    assert len(history) == 3
    assert history[0]['user']['public_key'] == alice_keypair['public_key']
    assert history[0]['event_id'] == persisted_manifestation['id']
    assert history[1]['user']['public_key'] == bob_keypair['public_key']
    assert history[1]['event_id'] == transfer_to_bob_tx['id']
    assert history[2]['user']['public_key'] == alice_keypair['public_key']
    assert history[2]['event_id'] == transfer_back_to_alice_tx['id']


def test_get_status(plugin, created_manifestation_id):
    # Poll BigchainDB for the initial status
    poll_result(
        lambda: plugin.get_status(created_manifestation_id),
        lambda result: result['status'] in (
            'valid', 'invalid', 'undecided', 'backlog'))

    # Poll BigchainDB until the transaction validates; will fail test if the
    # transaction's status doesn't become valid by the end of the timeout
    # period.
    poll_result(
        lambda: plugin.get_status(created_manifestation_id),
        lambda result: result['status'] == 'valid')


@mark.parametrize('model_name', [
    'manifestation_model_jsonld',
    'manifestation_model_json'
])
def test_save_model(plugin, bdb_driver, model_name, alice_keypair, request):
    model_data = request.getfixturevalue(model_name)
    tx_id = plugin.save(model_data, user=alice_keypair)

    # Poll BigchainDB for the result
    tx = poll_bdb_transaction(bdb_driver, tx_id)

    tx_payload = tx['asset']['data']
    tx_new_owners = tx['outputs'][0]['public_keys']
    assert tx['id'] == tx_id
    assert tx_payload == model_data
    assert tx_new_owners[0] == alice_keypair['public_key']


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
    from bigchaindb_driver.exceptions import MissingPrivateKeyError
    from coalaip.exceptions import EntityCreationError

    def mock_driver_error(*args, **kwargs):
        raise MissingPrivateKeyError()
    monkeypatch.setattr(plugin.driver.transactions, 'fulfill',
                        mock_driver_error)

    with raises(EntityCreationError):
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


def test_load_model(plugin, persisted_manifestation):
    tx_id = persisted_manifestation['id']
    loaded_transaction = plugin.load(tx_id)
    assert loaded_transaction == persisted_manifestation['asset']['data']


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
    transfer_tx = poll_bdb_transaction(bdb_driver, transfer_tx_id)

    transfer_tx_fulfillments = transfer_tx['inputs']
    transfer_tx_conditions = transfer_tx['outputs']
    transfer_tx_prev_owners = transfer_tx_fulfillments[0]['owners_before']
    transfer_tx_new_owners = transfer_tx_conditions[0]['public_keys']
    assert transfer_tx['id'] == tx_id
    assert transfer_tx_prev_owners[0] == alice_keypair['public_key']
    assert transfer_tx_new_owners[0] == bob_keypair['public_key']


###############################
# Generic NotFoundError tests #
###############################

@mark.parametrize('func_name,driver_tx_func_name', [
    ('get_history', 'get'),
    ('get_status', 'status'),
    ('load', 'retrieve')
])
def test_generic_plugin_func_on_id_raises_not_found_error_on_not_found(
        monkeypatch, plugin, created_manifestation_id, func_name,
        driver_tx_func_name):
    from bigchaindb_driver.exceptions import NotFoundError
    from coalaip.exceptions import EntityNotFoundError
    plugin_func = getattr(plugin, func_name)

    def mock_driver_not_found_error(*args, **kwargs):
        raise NotFoundError()
    monkeypatch.setattr(plugin.driver.transactions, driver_tx_func_name,
                        mock_driver_not_found_error)

    with raises(EntityNotFoundError):
        plugin_func(created_manifestation_id)


##################################
# Generic PersistenceError tests #
##################################

@mark.parametrize('func_name,driver_tx_func_name', [
    ('get_history', 'get'),
    ('get_status', 'status'),
    ('load', 'retrieve')
])
def test_generic_plugin_func_on_id_raises_persistence_error_on_error(
        monkeypatch, plugin, created_manifestation_id, func_name,
        driver_tx_func_name):
    from coalaip.exceptions import PersistenceError
    plugin_func = getattr(plugin, func_name)

    def mock_driver_not_found_error(*args, **kwargs):
        raise Exception()
    monkeypatch.setattr(plugin.driver.transactions, driver_tx_func_name,
                        mock_driver_not_found_error)

    with raises(PersistenceError):
        plugin_func(created_manifestation_id)


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
