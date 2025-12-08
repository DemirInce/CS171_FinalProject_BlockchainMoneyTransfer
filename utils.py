from blockchain import Block, BlockChain
import os
import json

def ensure_dir(path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

def read_json(path):
    if not os.path.isfile(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def write_json(path, data):
    ensure_dir(path)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    
def handle_file(path, values, new_block):
    data = read_json(path) or {}

    data.setdefault("variables", {})
    data.setdefault("blockchain", [])

    for k, v in values.items():
        data["variables"][k] = v

    if new_block is not None:
        block_dict = dict_from_block(new_block)
        data["blockchain"].append(block_dict)

    write_json(path, data)

def load_file(path):
    data = read_json(path) or {}
    if not data:
        print("File Not Found or empty")
        return None, None, None

    variables = data.get("variables", {})

    account_table = {int(k): int(v) for k, v in variables.get("account_table", {}).items()} or {}
    promised_ballot = tuple(variables.get("promised_ballot", (0, 0)))

    blocks = data.get("blockchain", [])
    blockchain = build_blockchain_from_list(blocks) if blocks else BlockChain()

    return account_table, promised_ballot, blockchain

def build_blockchain_from_list(blocks):
    blockchain = BlockChain()
    prev_block = None
    for block in blocks:
        new_block = Block.reconstruct(
                        tx=tuple(block["transaction"]),
                        nonce=block["nonce"],
                        hash_value=block["hash_value"],
                        prev=prev_block,
                        hash_pointer=block["hash_pointer"]
                    )
        prev_block = new_block
        blockchain.append(new_block)
    return blockchain

def dict_from_block(block):
    block_dict = {
                "transaction": list(block.transaction) if isinstance(block.transaction, (tuple, list)) else block.transaction,
                "nonce": block.nonce,
                "hash_value": block.hash_value,
                "hash_pointer": block.hash_pointer,
            }
    return block_dict

def overwrite_file(path, account_table, promised_ballot, blockchain):
    data = {
        "variables": {
            "account_table": {str(k): v for k, v in account_table.items()},
            "promised_ballot": list(promised_ballot)
        },
        "blockchain": [dict_from_block(b) for b in blockchain]
    }
    write_json(path, data)
