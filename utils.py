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
        block_dict = {
            "transaction": list(new_block.transaction) if isinstance(new_block.transaction, (tuple, list)) else new_block.transaction,
            "nonce": new_block.nonce,
            "hash_value": new_block.hash_value,
            "hash_pointer": new_block.hash_pointer,
        }
        data["blockchain"].append(block_dict)

    write_json(path, data)

def load_file(path):
    data = read_json(path) or {}
    if data == {}: 
        print("File Not Found")
        return

    account_table = {int(k): int(v) for k,v in data["variables"]["account_table"].items()}
    promised_ballot = tuple(data["variables"]["promised_ballot"])
    blocks = data["blockchain"]

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

    return account_table, promised_ballot, blockchain