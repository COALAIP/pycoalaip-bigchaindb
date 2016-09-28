from time import sleep

from pytest import fail


def poll_result(fn, result_test_fn, *, max_checks=5, interval=1):
    """Polling utility for cases where we need to wait for BigchainDB
    processing. After 'max_checks' attempts, will fail the test with the
    last result.

    Args:
        fn (func): polling function to invoke
        result_test_fn (func): test function to validate the result of
            the polling function; return true if the result is valid and
            can be returned
        max_checks (int): maximum poll attempts before failing test
        interval (num): interval between each poll attempt

    Returns:
        (any): the result of 'fn' if it passed validation
    """
    for _ in range(max_checks):
        try:
            result = fn()
        except Exception:
            # Just fail this polling instance and try again
            pass
        else:
            if result_test_fn(result):
                return result
        sleep(interval)

    fail("Polling result failed with result: '{}'".format(result))


def bdb_transaction_test(tx_result):
    return tx_result.get('status') != 404 and tx_result.get('id')
