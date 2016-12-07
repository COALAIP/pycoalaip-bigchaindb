from os import environ

from pytest import fixture


@fixture
def alice_signing_key():
    return 'CT6nWhSyE7dF2znpx3vwXuceSrmeMy9ChBfi9U92HMSP'


@fixture
def alice_verifying_key():
    return 'G7J7bXF8cqSrjrxUKwcF8tCriEKC5CgyPHmtGwUi4BK3'


@fixture
def alice_keypair(alice_signing_key, alice_verifying_key):
    return {
        'signing_key': alice_signing_key,
        'verifying_key': alice_verifying_key
    }


@fixture
def bob_signing_key():
    return '4S1dzx3PSdMAfs59aBkQefPASizTs728HnhLNpYZWCad'


@fixture
def bob_verifying_key():
    return '2dBVUoATxEzEqRdsi64AFsJnn2ywLCwnbNwW7K9BuVuS'


@fixture
def bob_keypair(bob_signing_key, bob_verifying_key):
    return {
        'signing_key': bob_signing_key,
        'verifying_key': bob_verifying_key
    }


@fixture
def bdb_host():
    return environ.get('BDB_HOST', 'localhost')


@fixture
def bdb_port():
    return environ.get('BDB_PORT', '9984')


@fixture
def bdb_node(bdb_host, bdb_port):
    return 'http://{host}:{port}/api/v1'.format(host=bdb_host, port=bdb_port)


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
        owners_before=alice_keypair['verifying_key'],
        # TODO: Where to put this "normalization"?
        asset={'data': manifestation_model_jsonld})
    fulfilled_tx = bdb_driver.transactions.fulfill(
        tx, private_keys=alice_keypair['signing_key'])
    bdb_driver.transactions.send(fulfilled_tx)
    return fulfilled_tx


@fixture
def persisted_manifestation(bdb_driver, created_manifestation):
    from tests.utils import bdb_transaction_test, poll_result
    created_id = created_manifestation['id']

    # Poll BigchainDB until the created manifestation becomes valid (and
    # 'persisted')
    poll_result(
        lambda: bdb_driver.transactions.status(created_id),
        lambda result: bdb_transaction_test)

    return created_manifestation
