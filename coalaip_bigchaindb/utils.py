from functools import wraps
from coalaip.exceptions import PersistenceError


def make_transfer_tx(bdb_driver, *, input_tx, recipients, metadata=None):
    if input_tx['operation'] == 'CREATE':
        input_asset_id = input_tx['id']
    else:
        input_asset_id = input_tx['asset']['id']

    input_tx_output = input_tx['outputs'][0]

    return bdb_driver.transactions.prepare(
        operation='TRANSFER',
        recipients=recipients,
        asset={'id': input_asset_id},
        metadata=metadata,
        inputs={
            'fulfillment': input_tx_output['condition']['details'],
            'fulfills': {
                'output': 0,
                'txid': input_tx['id'],
            },
            'owners_before': input_tx_output['public_keys']
        })


def reraise_as_persistence_error_if_not(*allowed_exceptions):
    """Decorator: Reraises any exception from the wrapped function
    by wrapping it around a :exc:`coalaip.PersistenceError` unless it's
    one of the given :attr:`allowed_exceptions`.

    Args:
        *allowed_exceptions (:exc:`Exception`): Exceptions to not
            reraise with :exc:`coalaip.PersistenceError`
    """
    def decorator(func):
        @wraps(func)
        def reraises_if_not(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as ex:
                if not isinstance(ex, allowed_exceptions):
                    raise PersistenceError(error=ex) from ex
                else:
                    raise
        return reraises_if_not
    return decorator


def order_transactions(transactions):
    """Given a list of unordered transactions, order and return them in
    a new list.

    Assumes that the given transactions never have more than one input
    and output (and therefore, as well, that there is never any
    transaction that divides assets); this allows us to represent the
    ordered transactions as a list rather than a branching graph.

    Args:
        transactions (list): Unordered list of transactions

    Returns:
        list: Ordered list of transactions, beginning from the first
        available transaction.

    Raises:
        :exc:`ValueError`: If the given list of transactions include two
            or more disjoint chains (i.e. not linkable into a single
            chain).
    """
    if not transactions:
        return []

    # Find the end tx:
    #   Go through the transactions and find the transaction whose id is not
    #   listed as a dependency of any other transaction
    end_tx = None
    input_dependencies = {tx['inputs'][0]['fulfills']['txid']
                          for tx in transactions
                          if tx['inputs'][0]['fulfills']}
    for tx in transactions:
        if tx['id'] not in input_dependencies:
            if end_tx:
                raise ValueError(
                    ('More than one transaction (ids include `{}` and `{}`) '
                     'was found to have no other transactions depend upon it '
                     'when attempting to order a list of transactions. This '
                     'means that the given list either contains a transaction '
                     'chain that is not flat or that some transactions are '
                     'missing from the list.'.format(end_tx['id'], tx['id'])))
            end_tx = tx

    if not end_tx:
        raise ValueError(('Could not find an end transaction when attempting '
                          'to order a list of transactions. This most likely '
                          'means the given list contains a cycle somewhere.'))

    # Create the ordered list of transactions, going backwards from the end
    ordered_tx = [None] * len(transactions)
    txs_by_id = {tx['id']: tx for tx in transactions}
    for ii in reversed(range(0, len(transactions))):
        ordered_tx[ii] = end_tx

        # If we're at the start of the tx chain, there is no next tx to find
        if ii is not 0:
            end_tx = txs_by_id[end_tx['inputs'][0]['fulfills']['txid']]

    return ordered_tx
