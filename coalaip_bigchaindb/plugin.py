from bigchaindb_driver import BigchainDB
from bigchaindb_driver.crypto import generate_keypair


# FIXME: maybe this should inherit from a base plugin class provided by pycoalaip?

class Plugin:
    """BigchainDB ledger plugin for COALA IP's Python reference
    implementation (LINK).

    Plugs in a BigchainDB instance as the persistence layer for COALA IP
    related actions.
    """

    def __init__(self, *nodes):
        """Initialize a :class:`~coalaip_bigchaindb.Plugin` instance
        and connect to one or more BigchainDB nodes.

        Args:
            *nodes (str): one or more URLs of BigchainDB nodes to
                connect to as the persistence layer
        """

        self.driver = BigchainDB(*nodes)

    def create_user(self):
        """Create a new verifying/signing keypair for use with BigchainDB

        Returns:
            tuple: a new verifying key ('verifying_key') and signing key
                ('signing_key') pair.
        """

        return generate_keypair()

    def get_status(self, persist_id):
        """Get the status of an COALA IP entity on BigchainDB

        Args:
            persist_id (str): the ID of the creation transaction for the
                entity on the connected BigchainDB instance

        Returns:
            Either:
                str: the status of the entiy; one of:
                    - 'valid': the transaction has been written in a
                               validated block
                    - 'invalid': the block the transaction was in was
                                 voted invalid
                    - 'undecided': the block the transaction is in is
                                   still undecided
                    - 'backlog': the transaction is still in the backlog
                None: if 'persist_id' is not a string or no transaction
                    whose 'uuid' matches 'persist_id' could be found in
                    the connected BigchainDB instance
        """

        # FIXME: how to do this return signature better

        # FIXME: maybe just do this in a try/catch block if the driver throws
        if not isinstance(persist_id, str):
            return None
        # FIXME: check API once implemented
        return self.driver.transactions.get_status(persist_id)

    def save(self, entity_data, *, user):
        """Create and assign a new entity with the given data to the
        given user's verifying key on BigchainDB

        Args:
            entity_data (dict): a dict holding the entity's data that
                will be saved in a new asset's asset definition
            user (tuple): a tuple containing:
                'verifying_key' (str): the user's verifying key on the
                    connected BigchainDB instance
                'signing_key' (str): the user's signing key on the
                    connected BigchainDB instance

        Returns:
            str: the id of the creation transaction for the new entity
        """

        # FIXME: how to do the dict arg better
        # FIXME: should I double check the user dict?
        # FIXME: handle error case
        tx_json = self.driver.transactions.create(
                entity_data,
                verifying_key=user.verifying_key,
                signing_key=user.signing_key)

        return tx_json['id']

    def transfer(self, persist_id, *, from_user, to_user):
        """Transfer the entity whose creation transaction matches
        'persist_id' from the current owner ('from_user') to a new owner
        ('to_user')

        Args:
            persist_id (str): the id of the creation transaction for the
                entity on the connected BigchainDB instance
            from_user (tuple): a tuple holding the current owner's
                verifying key ('verifying_key') and signing key
                ('signing_key')
            to_user (tuple): a tuple holding the new owner's verifying
                key ('verifying_key') and signing key ('signing_key')

        Returns:
            str: the id of the transaction transferring the entity from
                'from_user' to 'to_user'
        """

        raise NotImplementedError('transfer() has not been implemented yet')
