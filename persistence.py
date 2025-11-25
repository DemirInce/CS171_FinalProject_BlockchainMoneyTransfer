"""
Blockchain persistence to disk with block state tracking (tentative/decided)
"""
import json
import os
from pathlib import Path

class BlockRecord:
    """Represents a block record on disk with metadata"""
    def __init__(self, tx, nonce, hash_value, hash_pointer, state="tentative", depth=None):
        self.transaction = tx
        self.nonce = nonce
        self.hash_value = hash_value
        self.hash_pointer = hash_pointer
        self.state = state  # "tentative" or "decided"
        self.depth = depth  # block position in chain
    
    def to_dict(self):
        return {
            "transaction": self.transaction,
            "nonce": self.nonce,
            "hash_value": self.hash_value,
            "hash_pointer": self.hash_pointer,
            "state": self.state,
            "depth": self.depth
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            tx=data["transaction"],
            nonce=data["nonce"],
            hash_value=data["hash_value"],
            hash_pointer=data["hash_pointer"],
            state=data.get("state", "tentative"),
            depth=data.get("depth")
        )


class BlockchainPersistence:
    """Handles persistent storage of blockchain blocks and account state"""
    
    def __init__(self, peer_id, debug=False):
        self.peer_id = peer_id
        self.debug = debug
        self.blockchain_file = f"peer_{peer_id}_blockchain.jsonl"
        self.accounts_file = f"peer_{peer_id}_accounts.json"
    
    def write_block(self, block, state="tentative", depth=None):
        """
        Write a block to disk with its state.
        Appends block as a new line in JSONL format.
        Accepts either Block object or dict with tx, nonce, hash_value, hash_pointer.
        """
        try:
            # Handle both Block objects and dicts
            if isinstance(block, dict):
                tx = block.get("tx")
                nonce = block.get("nonce")
                hash_value = block.get("hash_value")
                hash_pointer = block.get("hash_pointer")
            else:
                # Block object
                tx = block.transaction
                nonce = block.nonce
                hash_value = block.hash_value
                hash_pointer = block.hash_pointer
            
            record = BlockRecord(
                tx=tx,
                nonce=nonce,
                hash_value=hash_value,
                hash_pointer=hash_pointer,
                state=state,
                depth=depth
            )
            
            # Append to blockchain file in JSONL format
            with open(self.blockchain_file, 'a') as f:
                f.write(json.dumps(record.to_dict()) + '\n')
            
            if self.debug:
                print(f"[DEBUG C-{self.peer_id}] Wrote block {tx} to disk (state={state}, depth={depth})")
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.peer_id}] Error writing block to disk: {e}")
    
    def mark_block_decided(self, depth):
        """
        Mark a block as decided by updating its state in the blockchain file.
        Rewrites the entire file with updated state.
        """
        try:
            blocks = []
            if os.path.exists(self.blockchain_file):
                with open(self.blockchain_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            if data.get("depth") == depth:
                                data["state"] = "decided"
                            blocks.append(data)
            
            # Rewrite file with updated blocks
            with open(self.blockchain_file, 'w') as f:
                for block_data in blocks:
                    f.write(json.dumps(block_data) + '\n')
            
            if self.debug:
                print(f"[DEBUG C-{self.peer_id}] Marked block at depth {depth} as decided")
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.peer_id}] Error marking block as decided: {e}")
    
    def load_blockchain(self):
        """
        Load blockchain from disk and reconstruct BlockChain object.
        Only includes decided blocks; tentative blocks are skipped.
        Returns a BlockChain object ready to use.
        """
        from blockchain import BlockChain, Block
        
        blockchain = BlockChain()
        try:
            if os.path.exists(self.blockchain_file):
                blocks = []
                with open(self.blockchain_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            blocks.append(data)
                
                # Only add decided blocks to the blockchain, in order by depth
                decided_blocks = [b for b in blocks if b.get("state") == "decided"]
                decided_blocks.sort(key=lambda x: x.get("depth", 0))
                
                for block_data in decided_blocks:
                    prev_block = blockchain.get_tail()
                    block = Block.reconstruct(
                        tx=block_data["transaction"],
                        nonce=block_data["nonce"],
                        hash_value=block_data["hash_value"],
                        prev=prev_block,
                        hash_pointer=block_data["hash_pointer"]
                    )
                    blockchain.append(block)
                
                if self.debug:
                    decided_count = len(decided_blocks)
                    print(f"[DEBUG C-{self.peer_id}] Loaded {blockchain.len} decided blocks from disk (total blocks on disk: {len(blocks)})")
            else:
                if self.debug:
                    print(f"[DEBUG C-{self.peer_id}] No blockchain file found, starting fresh")
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.peer_id}] Error loading blockchain: {e}")
        
        return blockchain
    
    def save_accounts(self, account_table):
        """Save account balances to disk (JSON format)"""
        try:
            # Convert keys to strings for JSON serialization
            account_dict = {str(k): v for k, v in account_table.items()}
            
            with open(self.accounts_file, 'w') as f:
                json.dump(account_dict, f, indent=2)
            
            if self.debug:
                print(f"[DEBUG C-{self.peer_id}] Persisted account table to disk")
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.peer_id}] Error saving accounts: {e}")
    
    def load_accounts(self):
        """Load account balances from disk"""
        try:
            if os.path.exists(self.accounts_file):
                with open(self.accounts_file, 'r') as f:
                    accounts_str = json.load(f)
                    # Convert keys back to integers
                    accounts = {int(k): v for k, v in accounts_str.items()}
                    if self.debug:
                        print(f"[DEBUG C-{self.peer_id}] Loaded account table from disk")
                    return accounts
            else:
                if self.debug:
                    print(f"[DEBUG C-{self.peer_id}] No accounts file found, using defaults")
                return {i: 100 for i in range(1, 6)}
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.peer_id}] Error loading accounts: {e}")
            return {i: 100 for i in range(1, 6)}
    
    def get_last_decided_block(self):
        """Get the last block marked as 'decided' from disk"""
        try:
            if os.path.exists(self.blockchain_file):
                with open(self.blockchain_file, 'r') as f:
                    blocks = [json.loads(line) for line in f if line.strip()]
                    
                    # Find last decided block (sort by depth)
                    decided_blocks = [b for b in blocks if b.get("state") == "decided"]
                    if decided_blocks:
                        decided_blocks.sort(key=lambda x: x.get("depth", 0))
                        return BlockRecord.from_dict(decided_blocks[-1])
            return None
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.peer_id}] Error getting last decided block: {e}")
            return None
    
    def clear_tentative_blocks(self):
        """Remove all tentative blocks from disk (useful after crash recovery)"""
        try:
            if os.path.exists(self.blockchain_file):
                blocks = []
                with open(self.blockchain_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            # Only keep decided blocks
                            if data.get("state") == "decided":
                                blocks.append(data)
                
                # Rewrite file with only decided blocks
                with open(self.blockchain_file, 'w') as f:
                    for block_data in blocks:
                        f.write(json.dumps(block_data) + '\n')
                
                if self.debug:
                    print(f"[DEBUG C-{self.peer_id}] Cleared tentative blocks from disk")
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.peer_id}] Error clearing tentative blocks: {e}")