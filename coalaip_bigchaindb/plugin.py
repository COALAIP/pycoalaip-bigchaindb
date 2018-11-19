from bigchaindb_driver import BigchainDB
from bigchaindb_driver.transport import Transport
from bigchaindb_driver.crypto import generate_keypair
from bigchaindb_driver.exceptions import (
    BigchaindbException,
    NotFoundError,
    MissingPrivateKeyError,
    TransportError,
    ConnectionError,
)
from coalaip.exceptions import (
    EntityCreationError,
    EntityNotFoundError,
    EntityTransferError,
)
from coalaip.plugin import AbstractPlugin
from coalaip_bigchaindb.utils import (
    make_transfer_tx,
    order_transactions,
    reraise_as_persistence_error_if_not,
)


class Plugin(AbstractPlugin):
    """BigchainDB ledger plugin for `COALA IP's Python reference
    implementation <https://github.com/bigchaindb/pycoalaip>`_.

    Plugs in a BigchainDB instance as the persistence layer for COALA IP
    related actions.
    """

    def __init__(self, *nodes, transport_class=Transport, headers=None, timeout=20):
        """Initialize a :class:`~.Plugin` instance and connect to one or
        more BigchainDB nodes.

        Args:
            *nodes (list of (str or dict)): BigchainDB nodes to connect to.
                Currently, the full URL must be given. In the absence of any
                node, the default(``'http://localhost:9984'``) will be used.
                If node is passed as a dict, `endpoint` is a required key;
                `headers` is an optional `dict` of headers.
            transport_class: Optional transport class to use.
                Defaults to :class:`~bigchaindb_driver.transport.Transport`.
            headers (dict): Optional headers that will be passed with
                each request. To pass headers only on a per-request
                basis, you can pass the headers to the method of choice
                (e.g. :meth:`BigchainDB().transactions.send_commit()
                <.TransactionsEndpoint.send_commit>`).
            timeout (int): Optional timeout in seconds that will be passed
                to each request.
        """
        self.driver = BigchainDB(*nodes, transport_class=transport_class, headers=headers, timeout=timeout)

    @property
    def type(self):
        """str: the type of this plugin (``'BigchainDB'``)"""
        return 'BigchainDB'

    def generate_user(self, seed=None):
        """Create a new public/private keypair for use with
        BigchainDB.

        Args:
        seed (bytes): 32-byte seed for deterministic generation.
                      Defaults to `None`.

        Returns:
            dict: A dict containing a new user's public and private
            keys::

                {
                    'public_key': (str),
                    'private_key': (str),
                }
        """

        return generate_keypair(seed)._asdict()

    def is_same_user(self, user_a, user_b):
        """Check if :attr:`user_a` represents the same user as
        :attr:`user_b` on BigchainDB by comparing their public keys.
        """

        return user_a['public_key'] == user_b['public_key']

    @reraise_as_persistence_error_if_not(EntityNotFoundError)
    def get_history(self, persist_id):
        """Get the transaction history of an COALA IP entity on
        BigchainDB.

        Args:
            persist_id (str): Asset id of the entity on the connected
                BigchainDB instance

        Returns:
            list of dict: The ownership history of the entity, sorted
            starting from the beginning of the entity's history
            (i.e. creation). Each dict is of the form::

                {
                    'user': A dict holding only the user's public key
                            (the private key is omitted as None).
                    'event_id': The transaction id for the ownership event
                }

        Raises:
            :exc:`coalaip.EntityNotFoundError`: If no asset whose id
                matches :attr:`persist_id` could be found in the
                connected BigchainDB instance
            :exc:`~.PersistenceError`: If any other unhandled error
                from the BigchainDB driver occurred.
        """

        try:
            transactions = self.driver.transactions.get(asset_id=persist_id)
        except NotFoundError:
            raise EntityNotFoundError()

        # Assume that each transaction will only ever have one owner
        # (and therefore one output as well)
        history = [{
            'user': {
                'public_key': tx['outputs'][0]['public_keys'][0],
                'private_key': None
            },
            'event_id': tx['id'],
        } for tx in order_transactions(transactions)]

        return history

    @reraise_as_persistence_error_if_not(EntityNotFoundError)
    def get_status(self, persist_id):
        """Get the status of an COALA IP entity on BigchainDB.

        Args:
            persist_id (str): Asset id of the entity on the connected
                BigchainDB instance

        Returns:
            str: the status of the entity; one of::

                'valid': the transaction has been written in a validated block

        Raises:
            :exc:`coalaip.EntityNotFoundError`: If no transaction whose
                'uuid' matches :attr:`persist_id` could be found in the
                connected BigchainDB instance. This could be because the
                transaction is still processing.
            :exc:`~.PersistenceError`: If any other unhandled error
                from the BigchainDB driver occurred.
        """

        if self.driver.blocks.get(txid=persist_id):
            return 'valid'
        else:
            raise EntityNotFoundError()

    @reraise_as_persistence_error_if_not(EntityCreationError)
    def save(self, entity_data, *, user):
        """Create and assign a new entity with the given data to the
        given user's public key on BigchainDB.

        Args:
            entity_data (dict): A dict holding the entity's data that
                will be saved in a new asset's asset definition
            user (dict, keyword): The user to assign the created entity
                to on BigchainDB. A dict containing::

                    {
                        'public_key': (str),
                        'private_key': (str),
                    }

                where 'public_key' and 'private_key' are the user's
                respective public and private keys.

        Returns:
            str: Asset id of the new entity

        Raises:
            :exc:`coalaip.EntityCreationError`: If the creation
                transaction fails
            :exc:`~.PersistenceError`: If any other unhandled error
                from the BigchainDB driver occurred.
        """

        try:
            tx = self.driver.transactions.prepare(
                operation='CREATE',
                signers=user['public_key'],
                asset={'data': entity_data})
        except BigchaindbException as ex:
            raise EntityCreationError(error=ex) from ex
        try:
            fulfilled_tx = self.driver.transactions.fulfill(
                tx, private_keys=user['private_key'])
        except MissingPrivateKeyError as ex:
            raise EntityCreationError(error=ex) from ex
        try:
            self.driver.transactions.send_commit(fulfilled_tx)
        except (TransportError, ConnectionError) as ex:
            raise EntityCreationError(error=ex) from ex

        return fulfilled_tx['id']

    @reraise_as_persistence_error_if_not(EntityNotFoundError)
    def load(self, persist_id):
        """Load the data of the entity associated with the
        :attr:`persist_id` from BigchainDB.

        Args:
            persist_id (str): Asset id of the entity being loaded on the
                connected BigchainDB instance

        Returns:
            dict: The persisted data of the entity

        Raises:
            :exc:`coalaip.EntityNotFoundError`: If no asset whose id
            matches :attr:`persist_id` could be found in the connected
            BigchainDB instance
            :exc:`~.PersistenceError`: If any other unhandled error
                from the BigchainDB driver occurred.
        """

        try:
            tx_json = self.driver.transactions.retrieve(persist_id)
        except NotFoundError:
            raise EntityNotFoundError()

        if tx_json['operation'] == 'CREATE':
            return tx_json['asset']['data']
        else:
            return tx_json['metadata']

    @reraise_as_persistence_error_if_not(EntityNotFoundError,
                                         EntityTransferError)
    def transfer(self, persist_id, transfer_payload=None, *, from_user,
                 to_user):
        """Transfer the entity matching the given :attr:`persist_id`
        from the current owner (:attr:`from_user`) to a new owner
        (:attr:`to_user`).

        Args:
            persist_id (str): Asset id of the entity on the connected
                BigchainDB instance
            transfer_payload (dict, optional): A dict holding the
                transfer's payload
            from_user (dict, keyword): A dict holding the current
                owner's public key and private key (see
                :meth:`generate_user`)
            to_user (dict, keyword): A dict holding the new owner's
                public key and private key (see
                :meth:`generate_user`)

        Returns:
            str: Id of the transaction transferring the entity from
            :attr:`from_user` to :attr:`to_user`

        Raises:
            :exc:`coalaip.EntityNotFoundError`: If no asset whose id
                matches :attr:`persist_id` could be found in the
                connected BigchainDB instance
            :exc:`coalaip.EntityTransferError`: If the transfer
                transaction fails
            :exc:`~.PersistenceError`: If any other unhandled error
                from the BigchainDB driver occurred.
        """

        try:
            ordered_tx = order_transactions(
                self.driver.transactions.get(asset_id=persist_id))
            last_tx = ordered_tx[-1]
        except NotFoundError:
            raise EntityNotFoundError()

        try:
            transfer_tx = make_transfer_tx(self.driver, input_tx=last_tx,
                                           recipients=to_user['public_key'],
                                           metadata=transfer_payload)
        except BigchaindbException as ex:
            raise EntityTransferError(error=ex) from ex

        try:
            fulfilled_tx = self.driver.transactions.fulfill(
                transfer_tx, private_keys=from_user['private_key'])
        except MissingPrivateKeyError as ex:
            raise EntityTransferError(error=ex) from ex

        try:
            transfer_json = self.driver.transactions.send_commit(fulfilled_tx)
        except (TransportError, ConnectionError) as ex:
            raise EntityTransferError(error=ex) from ex

        return transfer_json['id']
