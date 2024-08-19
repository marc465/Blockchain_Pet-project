import hashlib
import json
from time import time
from uuid import uuid4
from textwrap import dedent
from urllib.parse import urlparse

from flask import Flask, jsonify, request

#Add comment

class Blockchain ():
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.nodes = set()
        self.new_block(previous_hash=1, proof=100)

    def new_block (self, proof: int, previous_hash: int = None) -> dict:
        #Adds new block to the chain
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }
        self.transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender : str, recipient : str, amount : int):

        #Adds new transaction to list of transaction

        self.transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })
        return self.last_block['index'] + 1

    def register_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print('\n------------\n')

            if block['previous_hash'] != self.hash(last_block):
                return False
            
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
            
            last_block = block
            current_index += 1

        return True

    def resolve_conflict(self):
        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)

        for node in neighbours:
            response = request.get_data(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True
        
        return False

    @staticmethod
    def hash(block):
        #Hashes a Block
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]
    
    def proof_of_work(self, last_proof:int) -> int:
        """
        Simpliest Proof of Work algorithm. Return proof:int.
        
        Requaries:
          -  last_proof --> Previous proof
        """

        proof = 0
        while self.valid_proof(last_proof, proof) == False:
            proof += 1
        return proof
    
    @staticmethod
    def valid_proof(last_proof:int, proof:int) -> bool:

        """
        Validates a Proof. Return True or False.
        
        Requaries:
          -  last_proof --> Previous proof
          -  proof --> Current proof
        """

        return hashlib.sha256(f'{last_proof}{proof}'.encode()).hexdigest()[:4] == '0000'
    
app = Flask("__name__")

node_identifer = str(uuid4()).replace('-', '')

blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']

    proof = blockchain.proof_of_work(last_proof=last_proof)
    blockchain.new_transaction(sender='0', recipient=node_identifer, amount=1)

    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof=proof, previous_hash=previous_hash)

    response = {
        'message': 'New Block added',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }

    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount']

    if not all(k in values for k in required):
        return "Missing Value", 400
    
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction is added to Block. Index: {index}'}
    return response

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'length': blockchain.chain.__len__(),
        'chain': blockchain.chain
    }

    return jsonify(response), 200

@app.route('/nodes/register', methods = ['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return 'Error: Please suply a valid list of nodes', 400
    
    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodeshave been added',
        'total_nodes': list(blockchain.nodes)
    }
    return jsonify(response), 201

@app.route('/node/resolve', methods = ['GET'])
def resolve():
    replaced = blockchain.resolve_conflict()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'chain': blockchain.chain
            }
    
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
            }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
