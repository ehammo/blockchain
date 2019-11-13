import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
import traceback

import requests
from flask import Flask, jsonify, request


class Blockchain:
    def __init__(self, node_identifier):
        # How should the blockchain be saved outside the memory? A big json? Should we import it here?
        # We should also save our neighboors so we can update our blockchain. In fact, that may be even more useful
        self.current_transactions = []
        self.chain = []
        self.nodes = set()
        self.node_identifier = node_identifier
        # Create the genesis block
        self.new_block(previous_hash='1', proof=100)


    def is_address_valid(self, address):
        parsed_url = urlparse(address)
        if parsed_url.netloc:
          url = parsed_url.netloc
          print(f'netloc {url}')
       # TODO: Accepts an URL without scheme like '192.168.0.5:5000'.
       # This elif was accepting stuff like http//0.0.0.0:5555
       # elif parsed_url.path:
        #  url = parsed_url.path
        #  print(f'path {url}')
        else:
          print("invalid")
          raise ValueError(f'Invalid URL- {parsed_url.path}')
        return url



    # todo: should we search for neighbours? should neighboors ping us?
    def register_node(self, address):
        """
        Add a new node to the list of nodes

        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """
        try:
          url = is_address_valid(address)
          print(f'trying to get http://{url}/id')
          response = requests.get(f'http://{url}/id')
          new_node_id = response.json()['id']
          if (self.node_identifier == new_node_id):
            raise ValueError(f'A node cant be his own neighboor - {url}')
          else:
            self.nodes.add(url)
        except ValueError as e:
          raise e
        except requests.exceptions.RequestException as e:
          raise ValueError(f'Dead node - {url}')
        except Exception as e:
          traceback.print_exc()
          raise ValueError(f'Unexpected error while adding {url}')

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid

        :param chain: A blockchain
        :return: True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            last_block_hash = self.hash(last_block)
            if block['previous_hash'] != last_block_hash:
                return False
            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False

            last_block = block
            current_index += 1

        return True

    # todo: what do we do with a pending transaction of our old blockchain? We shouldnt discard it.
    def resolve_conflicts(self):
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.

        :return: True if our chain was replaced, False if not
        """
        print("resolving conflicts")
        neighbours = self.nodes.copy()
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)
        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            print(f'Checking chain of neighbours {node}')
            try:
              response = requests.get(f'http://{node}/chain')
              print("Got chain")
              if response.status_code == 200:
                  length = response.json()['length']
                  chain = response.json()['chain']

                  # Check if the length is longer and the chain is valid
                  print("is chain valid?")
                  if length > max_length and self.valid_chain(chain) and length == len(chain):
                      max_length = length
                      new_chain = chain
            except:
              print(f'Unresponsive node {node}')
              print("removing from sub subscribers list")
              self.nodes.discard(node) 
              pass

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash):
        """
        Create a new Block in the Blockchain

        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block

        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        :param block: Block
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_block):
        """
        Simple Proof of Work Algorithm:

         - Find a number p' such that hash(pp') contains leading 4 zeroes
         - Where p is the previous proof, and p' is the new proof
         
        :param last_block: <dict> last Block
        :return: <int>
        """

        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validates the Proof

        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str> The hash of the Previous Block
        :return: <bool> True if correct, False if not.

        """

        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


# Instantiate the Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain(node_identifier)

@app.route('/id', methods=['GET'])
def get_node_identifier():
  response = {
    'id': node_identifier,
  }
  return jsonify(response), 200

# TODO: mining should come after trying to create a transaction not before
# maybe we should ask the neighboors who wants to mine a pending transaction

@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    print(request)
    values = request.get_json()
    if values is None:
      response = {'message': f'Body should be a json'}
      return jsonify(response), 501
    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    counter = 0
    error_messages = set()
    for node in nodes:
      try:
        blockchain.register_node(node)
        counter = counter + 1
      except Exception as e:
        error_messages.add(e)
        pass
    if(counter > 0):
      response = {
          'message': 'New nodes have been added',
          'total_nodes': list(blockchain.nodes),
      }
      return jsonify(response), 201
    else:
      response = {
          'message': f'No nodes have been added {error_messages}',
          'total_nodes': list(blockchain.nodes),
      }
      return jsonify(response), 200

@app.route('/nodes', methods=['GET'])
def get_nodes():
  response = {
        'total_nodes': list(blockchain.nodes),
  }
  return jsonify(response), 200

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)
