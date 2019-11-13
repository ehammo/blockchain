import hashlib
import json
from unittest import TestCase

from blockchain import Blockchain


class BlockchainTestCase(TestCase):

    def setUp(self):
        self.blockchain = Blockchain('http://192.168.1.1:5000')

    def create_block(self, proof=123, previous_hash='abc'):
        self.blockchain.new_block(proof, previous_hash)

    def create_transaction(self, sender='a', recipient='b', amount=1):
        self.blockchain.new_transaction(
            sender=sender,
            recipient=recipient,
            amount=amount
        )


class TestRegisterNodes(BlockchainTestCase):

    def test_valid_nodes(self):
        try:
            self.blockchain.is_address_valid('http://192.168.0.1:5000')
            assert True
        except:
            assert False            

    def test_malformed_nodes(self):
        try:
            self.blockchain.is_address_valid('http://192.168.0.2:5000')
            assert False
        except:
            assert True

    #In today's logic it would be necessary to mock the activity of these nodes, since only active nodes may enter the blockchain
    #def test_idempotency(self):
    #    try:
    #	    self.blockchain.is_address_valid('http://192.168.0.3:5000')
    #	    self.blockchain.is_address_valid('http://192.168.0.3:5000')
    #        assert True
    #    except:
    #        assert False


    def test_do_not_add_yourself(self):
        try:
            self.blockchain.is_address_valid('http://192.168.1.1:5000')
            assert False
        except:
            assert True



class TestBlocksAndTransactions(BlockchainTestCase):

    def test_block_creation(self):
        self.create_block()

        latest_block = self.blockchain.last_block

        # The genesis block is create at initialization, so the length should be 2
        assert len(self.blockchain.chain) == 2
        assert latest_block['index'] == 2
        assert latest_block['timestamp'] is not None
        assert latest_block['proof'] == 123
        assert latest_block['previous_hash'] == 'abc'

    def test_create_transaction(self):
        self.create_transaction()

        transaction = self.blockchain.current_transactions[-1]

        assert transaction
        assert transaction['sender'] == 'a'
        assert transaction['recipient'] == 'b'
        assert transaction['amount'] == 1

    def test_block_resets_transactions(self):
        self.create_transaction()

        initial_length = len(self.blockchain.current_transactions)

        self.create_block()

        current_length = len(self.blockchain.current_transactions)

        assert initial_length == 1
        assert current_length == 0

    def test_return_last_block(self):
        self.create_block()

        created_block = self.blockchain.last_block

        assert len(self.blockchain.chain) == 2
        assert created_block is self.blockchain.chain[-1]


class TestHashingAndProofs(BlockchainTestCase):

    def test_hash_is_correct(self):
        self.create_block()

        new_block = self.blockchain.last_block
        new_block_json = json.dumps(self.blockchain.last_block, sort_keys=True).encode()
        new_hash = hashlib.sha256(new_block_json).hexdigest()

        assert len(new_hash) == 64
        assert new_hash == self.blockchain.hash(new_block)
