from pytest import raises


def test_make_transfer_transaction(bdb_driver, alice_keypair, bob_keypair,
                                   created_manifestation):
    from coalaip_bigchaindb.utils import make_transfer_tx
    mock_metadata = {'mock': 'mock'}
    transfer_tx = make_transfer_tx(bdb_driver, input_tx=created_manifestation,
                                   recipients=bob_keypair['public_key'],
                                   metadata=mock_metadata)
    transfer_tx = bdb_driver.transactions.fulfill(
        transfer_tx, private_keys=alice_keypair['private_key'])

    assert transfer_tx['asset']['id'] == created_manifestation['id']
    assert transfer_tx['metadata'] == mock_metadata
    assert transfer_tx['inputs'][0]['fulfills']['txid'] == created_manifestation['id']
    assert transfer_tx['inputs'][0]['owners_before'][0] == alice_keypair['public_key']
    assert transfer_tx['outputs'][0]['public_keys'][0] == bob_keypair['public_key']


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


def test_order_transactions(bdb_driver, alice_keypair, bob_keypair):
    import random
    from coalaip_bigchaindb.utils import make_transfer_tx, order_transactions
    create_tx = bdb_driver.transactions.prepare(
        operation='CREATE',
        signers=alice_keypair['public_key'])
    transfer_to_bob_tx = make_transfer_tx(bdb_driver, input_tx=create_tx,
                                          recipients=bob_keypair['public_key'])
    transfer_back_to_alice_tx = make_transfer_tx(
        bdb_driver, input_tx=transfer_to_bob_tx, recipients=alice_keypair['public_key'])

    correct_order = [create_tx, transfer_to_bob_tx, transfer_back_to_alice_tx]
    for _ in range(0, 100):
        assert correct_order == order_transactions(
            random.sample(correct_order, len(correct_order)))


def test_order_transactions_is_correct_without_create(
        bdb_driver, alice_keypair, bob_keypair):
    import random
    from coalaip_bigchaindb.utils import make_transfer_tx, order_transactions
    create_tx = bdb_driver.transactions.prepare(
        operation='CREATE',
        signers=alice_keypair['public_key'])
    transfer_to_bob_tx = make_transfer_tx(bdb_driver, input_tx=create_tx,
                                          recipients=bob_keypair['public_key'])
    transfer_back_to_alice_tx = make_transfer_tx(
        bdb_driver, input_tx=transfer_to_bob_tx, recipients=alice_keypair['public_key'])
    transfer_back_to_bob_tx = make_transfer_tx(
        bdb_driver, input_tx=transfer_back_to_alice_tx, recipients=bob_keypair['public_key'])

    correct_order = [transfer_to_bob_tx, transfer_back_to_alice_tx, transfer_back_to_bob_tx]
    for _ in range(0, 100):
        assert correct_order == order_transactions(
            random.sample(correct_order, len(correct_order)))


def test_order_empty_transations():
    from coalaip_bigchaindb.utils import order_transactions
    ordered_tx = order_transactions([])
    assert ordered_tx == []


def test_order_transactions_fails_with_multiple_endings(
        bdb_driver, alice_keypair, bob_keypair, carly_keypair):
    from coalaip_bigchaindb.utils import make_transfer_tx, order_transactions
    create_tx = bdb_driver.transactions.prepare(
        operation='CREATE',
        signers=alice_keypair['public_key'])
    transfer_to_bob_tx = make_transfer_tx(bdb_driver, input_tx=create_tx,
                                          recipients=bob_keypair['public_key'])
    transfer_to_carly_tx = make_transfer_tx(
        bdb_driver, input_tx=create_tx, recipients=carly_keypair['public_key'])

    with raises(ValueError):
        # Transfer to both bob and carly should result in a multiple endings
        # error
        order_transactions([create_tx, transfer_to_bob_tx, transfer_to_carly_tx])


def test_order_transactions_fails_with_cyclic_tx(
        bdb_driver, alice_keypair, bob_keypair, carly_keypair):
    from coalaip_bigchaindb.utils import make_transfer_tx, order_transactions
    create_tx = bdb_driver.transactions.prepare(
        operation='CREATE',
        signers=alice_keypair['public_key'])
    transfer_to_bob_tx = make_transfer_tx(bdb_driver, input_tx=create_tx,
                                          recipients=bob_keypair['public_key'])
    transfer_to_carly_tx = make_transfer_tx(
        bdb_driver, input_tx=transfer_to_bob_tx, recipients=carly_keypair['public_key'])
    transfer_to_alice_tx = make_transfer_tx(
        bdb_driver, input_tx=transfer_to_carly_tx, recipients=alice_keypair['public_key'])

    # Modify transfer to bob tx so that it links back to the transfer to alice.
    # This should create a
    #   bob_transfer <- carly_transfer <- alice_transfer <- bob_transfer
    # dependency cycle.
    transfer_to_bob_tx['inputs'][0]['fulfills']['txid'] = transfer_to_alice_tx['id']

    with raises(ValueError):
        order_transactions([
            transfer_to_bob_tx,
            transfer_to_carly_tx,
            transfer_to_alice_tx,
        ])


def test_order_transactions_fails_with_multiple_starts(
        bdb_driver, alice_keypair, bob_keypair, carly_keypair):
    from coalaip_bigchaindb.utils import make_transfer_tx, order_transactions
    create_tx_alice = bdb_driver.transactions.prepare(
        operation='CREATE',
        signers=alice_keypair['public_key'])
    create_tx_bob = bdb_driver.transactions.prepare(
        operation='CREATE',
        signers=bob_keypair['public_key'])
    transfer_to_carly_tx = make_transfer_tx(
        bdb_driver, input_tx=create_tx_alice,
        recipients=carly_keypair['public_key'])

    with raises(ValueError):
        # Multiple CREATEs should result in an error with multiple tx not
        # fulfilling a prior tx
        order_transactions([
            create_tx_alice,
            create_tx_bob,
            transfer_to_carly_tx,
        ])


def test_order_transactions_fails_with_missing_tx(bdb_driver, alice_keypair,
                                                  bob_keypair, carly_keypair):
    from coalaip_bigchaindb.utils import make_transfer_tx, order_transactions
    create_tx = bdb_driver.transactions.prepare(
        operation='CREATE',
        signers=alice_keypair['public_key'])
    transfer_to_bob_tx = make_transfer_tx(bdb_driver, input_tx=create_tx,
                                          recipients=bob_keypair['public_key'])
    transfer_to_carly_tx = make_transfer_tx(
        bdb_driver, input_tx=transfer_to_bob_tx, recipients=carly_keypair['public_key'])
    transfer_to_alice_tx = make_transfer_tx(
        bdb_driver, input_tx=transfer_to_carly_tx, recipients=alice_keypair['public_key'])

    with raises(ValueError):
        # Missing transfer to carly (that the transfer to alice is based on)
        # should result in an error with an unfound tx
        order_transactions([
            create_tx,
            transfer_to_bob_tx,
            transfer_to_alice_tx,
        ])
