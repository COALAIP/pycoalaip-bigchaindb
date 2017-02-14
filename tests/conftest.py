from os import environ

from pytest import fixture


@fixture
def alice_keypair():
    from bigchaindb_driver.crypto import generate_keypair
    return generate_keypair()._asdict()


@fixture
def bob_keypair():
    from bigchaindb_driver.crypto import generate_keypair
    return generate_keypair()._asdict()


@fixture
def carly_keypair():
    from bigchaindb_driver.crypto import generate_keypair
    return generate_keypair()._asdict()


@fixture
def bdb_host():
    return environ.get('BDB_HOST', 'localhost')


@fixture
def bdb_port():
    return environ.get('BDB_PORT', '9984')


@fixture
def bdb_node(bdb_host, bdb_port):
    return 'http://{host}:{port}'.format(host=bdb_host, port=bdb_port)


@fixture
def plugin(bdb_node):
    from coalaip_bigchaindb import Plugin
    return Plugin(bdb_node)


@fixture
def bdb_driver(bdb_node):
    from bigchaindb_driver import BigchainDB
    return BigchainDB(bdb_node)


@fixture
def manifestation_model_jsonld():
    return {
        '@context': 'http://schema.org/',
        '@type': 'CreativeWork',
        'name': 'Manifestation Title',
        'creator': 'https://ipdb.foundation/api/transactions/12346789',
    }


@fixture
def manifestation_model_json():
    return {
        'type': 'CreativeWork',
        'name': 'Manifestation Title',
        'creator': 'https://ipdb.foundation/api/transactions/12346789',
    }


@fixture
def rights_assignment_model_jsonld():
    return {
        '@context': 'http://schema.org/',
        '@type': 'RightsTransferAction',
        'transferContract': 'https://ipdb.s3.amazonaws.com/1234567890.pdf'
    }


@fixture
def rights_assignment_model_json():
    return {
        'type': 'RightsTransferAction',
        'transferContract': 'https://ipdb.s3.amazonaws.com/1234567890.pdf'
    }


@fixture
def created_manifestation(bdb_driver, manifestation_model_jsonld,
                          alice_keypair):
    tx = bdb_driver.transactions.prepare(
        operation='CREATE',
        signers=alice_keypair['public_key'],
        asset={'data': manifestation_model_jsonld})
    fulfilled_tx = bdb_driver.transactions.fulfill(
        tx, private_keys=alice_keypair['private_key'])
    bdb_driver.transactions.send(fulfilled_tx)
    return fulfilled_tx


@fixture
def created_manifestation_id(created_manifestation):
    return created_manifestation['id']


@fixture
def persisted_manifestation(bdb_driver, created_manifestation):
    from tests.utils import poll_bdb_transaction_valid
    tx_id = created_manifestation['id']

    # Poll BigchainDB until the created manifestation becomes valid (and
    # 'persisted')
    poll_bdb_transaction_valid(bdb_driver, tx_id)

    return created_manifestation


@fixture
def transferred_manifestation_tx(bdb_driver, persisted_manifestation,
                                 alice_keypair, bob_keypair,
                                 rights_assignment_model_json):
    from tests.utils import poll_bdb_transaction_valid
    input_tx = persisted_manifestation
    asset_id = input_tx['id']
    input_tx_output = input_tx['outputs'][0]

    transfer_tx = bdb_driver.transactions.prepare(
        operation='TRANSFER',
        recipients=bob_keypair['public_key'],
        asset={'id': asset_id},
        metadata=rights_assignment_model_json,
        inputs={
            'fulfillment': input_tx_output['condition']['details'],
            'fulfills': {
                'output': 0,
                'txid': input_tx['id'],
            },
            'owners_before': input_tx_output['public_keys'],
        },
    )

    fulfilled_transfer_tx = bdb_driver.transactions.fulfill(
        transfer_tx, private_keys=alice_keypair['private_key'])
    bdb_driver.transactions.send(fulfilled_transfer_tx)

    # Poll BigchainDB until the transfer becomes valid (and 'persisted')
    poll_bdb_transaction_valid(bdb_driver, fulfilled_transfer_tx['id'])

    return fulfilled_transfer_tx
