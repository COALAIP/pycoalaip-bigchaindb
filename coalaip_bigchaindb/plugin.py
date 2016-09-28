from bigchaindb_driver import BigchainDB
from bigchaindb_driver.crypto import generate_keypair
from bigchaindb_driver.exceptions import DriverException, NotFoundError
from coalaip.exceptions import EntityCreationError, EntityNotFoundError
from coalaip.plugin import AbstractPlugin


class Plugin(AbstractPlugin):
    """BigchainDB ledger plugin for `COALA IP's Python reference
    implementation <https://github.com/bigchaindb/pycoalaip>`_.

    Plugs in a BigchainDB instance as the persistence layer for COALA IP
    related actions.
    """

    def __init__(self, *nodes):
        """Initialize a :class:`~.Plugin` instance and connect to one or
        more BigchainDB nodes.

        Args:
            *nodes (str): One or more URLs of BigchainDB nodes to
                connect to as the persistence layer
        """

        self.driver = BigchainDB(*nodes)

    @property
    def type(self):
        """str: the type of this plugin (``'BigchainDB'``)"""
        return 'BigchainDB'

    def generate_user(self):
        """Create a new verifying/signing keypair for use with
        BigchainDB.

        Returns:
            dict: A dict containing a new user's verifying and signing
            keys::

                {
                    'verifying_key': (str),
                    'signing_key': (str),
                }
        """

        return generate_keypair()._asdict()

    def get_status(self, persist_id):
        """Get the status of an COALA IP entity on BigchainDB.

        Args:
            persist_id (str): Id of the creation transaction for the
                entity on the connected BigchainDB instance

        Returns:
            str: the status of the entity; one of::

                'valid': the transaction has been written in a validated block
                'invalid': the block the transaction was in was voted invalid
                'undecided': the block the transaction is in is still undecided
                'backlog': the transaction is still in the backlog

        Raises:
            :exc:`coalaip.exceptions.EntityNotFoundError`: If no
                transaction whose 'uuid' matches 'persist_id' could be
                found in the connected BigchainDB instance
        """

        try:
            return self.driver.transactions.status(persist_id)
        except NotFoundError:
            raise EntityNotFoundError()

    def save(self, entity_data, *, user):
        """Create and assign a new entity with the given data to the
        given user's verifying key on BigchainDB.

        Args:
            entity_data (dict): A dict holding the entity's data that
                will be saved in a new asset's asset definition
            user (dict, keyword): The user to assign the created entity
                to on BigchainDB. A dict containing::

                    {
                        'verifying_key': (str),
                        'signing_key': (str),
                    }

                where 'verifying_key' and 'signing_key' are the user's
                respective verifying and signing keys.

        Returns:
            str: Id of the creation transaction for the new entity

        Raises:
            :exc:`coalaip.exceptions.EntityCreationError`: If the
                creation transaction fails
        """

        try:
            tx_json = self.driver.transactions.create(
                    entity_data,
                    verifying_key=user['verifying_key'],
                    signing_key=user['signing_key'])
        except DriverException as ex:
            raise EntityCreationError(ex)

        return tx_json['id']

    def load(self, persist_id):
        """Load the data of the entity associated with the
        :attr:`persist_id` from BigchainDB.

        Args:
            persist_id (str): Id of the creation transaction for the
                entity on the connected BigchainDB instance

        Returns:
            dict: The persisted data of the entity

        Raises:
            :exc:`coalaip.exceptions.EntityNotFoundError`: If no
                transaction whose 'uuid' matches 'persist_id' could be
                found in the connected BigchainDB instance
        """

        try:
            tx_json = self.driver.transactions.retrieve(persist_id)
        except NotFoundError as ex:
            raise EntityNotFoundError()

        return tx_json['transaction']['data']['payload']

    def transfer(self, persist_id, transfer_payload, *, from_user, to_user):
        """Transfer the entity whose creation transaction matches
        :attr:`persist_id` from the current owner (:attr:`from_user`) to
        a new owner (:attr:`to_user`).

        Args:
            persist_id (str): Id of the creation transaction for the
                entity on the connected BigchainDB instance
            transfer_payload (dict): A dict holding the transfer's
                payload
            from_user (dict, keyword): A dict holding the current
                owner's verifying key and signing key (see
                :meth:`generate_user`)
            to_user (dict, keyword): A dict holding the new owner's
                verifying key and signing key (see
                :meth:`generate_user`)

        Returns:
            str: Id of the transaction transferring the entity from
            :attr:`from_user` to :attr:`to_user`
        """

        raise NotImplementedError('transfer() has not been implemented yet')
