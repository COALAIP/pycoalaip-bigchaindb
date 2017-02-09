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
                    ('Two potential ending transactions (with  ids: `{}` and '
                     '`{}` were found when attempting to order a list of '
                     'transactions.'.format(end_tx['id'], tx['id'])))
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
            fulfilled_by = end_tx['inputs'][0]['fulfills']
            if not fulfilled_by:
                raise ValueError(
                    ('Found transaction with id `{}` that does not fulfill a '
                     'prior transaction before an attempt to order a list of '
                     'transactions was complete. There were most likely two '
                     'CREATE transactions given.'.format(end_tx['id'])))
            try:
                end_tx = txs_by_id[fulfilled_by['txid']]
            except KeyError:
                raise ValueError(
                    ('Could not find a transaction with with id `{input_tx}` '
                     '(that transaction `{tx}` depends upon) when attempting '
                     'to order a list of transatcions.'.format(
                         input_tx=end_tx['inputs'][0]['fulfills']['txid'],
                         tx=end_tx['id'])))

    return ordered_tx
