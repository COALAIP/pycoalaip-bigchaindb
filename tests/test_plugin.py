#!/usr/bin/env python

from time import sleep
from pytest import mark


def test_init_connects_to_driver(plugin):
    from bigchaindb_driver import BigchainDB
    assert isinstance(plugin.driver, BigchainDB)


def test_create_user(plugin):
    user = plugin.create_user()
    assert isinstance(user.verifying_key, str)
    assert isinstance(user.signing_key, str)


@mark.parametrize(
    'model_name',
    ('manifestation_model_jsonld', 'manifestation_model_json'))
def test_save_model_jsonld(plugin, bdb_driver, model_name, alice_keypair,
                           request):
    model_data = request.getfixturevalue(model_name)
    tx_id = plugin.save(model_data, user=alice_keypair)

    # Sleep to give BigchainDB some time to process the transaction
    sleep(5)

    tx = bdb_driver.transactions.retrieve(tx_id)
    tx_payload = tx['transaction']['data']['payload']
    tx_new_owners = tx['transaction']['conditions'][0]['owners_after']
    assert tx['id'] == tx_id
    assert tx_payload == model_data
    assert tx_new_owners[0] == alice_keypair.verifying_key


@mark.skip(reason='get_status() not implemented yet')
def test_get_model_status(plugin, persisted_manifestation):
    status = plugin.get_status(persisted_manifestation['id'])
    assert status in (None, 'valid', 'invalid', 'undecided', 'backlog')


@mark.skip(reason='transfer() not implemented yet')
@mark.parametrize(
    'model_name',
    ('rights_assignment_model_jsonld', 'rights_assignment_model_json'))
def test_transfer(plugin, bdb_driver, persisted_manifestation, model_name,
                  alice_keypair, bob_keypair, request):
    model_data = request.getfixturevalue(model_name)
    tx_id = persisted_manifestation['id']

    transfer_tx_id = plugin.transfer(tx_id, model_data,
                                     from_user=alice_keypair,
                                     to_user=bob_keypair)

    # Sleep to give BigchainDB some time to process the transaction
    sleep(5)

    transfer_tx = bdb_driver.transactions.retrieve(transfer_tx_id)
    transfer_tx_fulfillments = transfer_tx['transaction']['fulfillments']
    transfer_tx_conditions = transfer_tx['transaction']['conditions']
    transfer_tx_prev_owners = transfer_tx_fulfillments[0]['owners_before']
    transfer_tx_new_owners = transfer_tx_conditions[0]['owners_after']
    assert transfer_tx['id'] == tx_id
    assert transfer_tx_prev_owners[0] == alice_keypair.verifying_key
    assert transfer_tx_new_owners[0] == bob_keypair.verifying_key


# TODO: add error case tests
