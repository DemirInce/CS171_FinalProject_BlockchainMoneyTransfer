from blockchain import BlockChain
from blockchain import Block
from persistence import BlockchainPersistence
from enum import Enum
import threading
import queue
import socket
import time
import json

class Peer:
    def __init__(self, id, debug=False, ip="127.0.0.1"):
        self.id = id
        self.debug = debug
        self.ip = ip
        self.blockchain = BlockChain()
        self.account_table = {i: 100 for i in range(1,6)}
        self.dead = False

        self.request_queue = queue.Queue()
        self.lock = threading.Lock()

        threading.Thread(target=self._listener_thread, daemon=True).start()
        for _ in range(4):
            threading.Thread(target=self._worker_thread, daemon=True).start()

        self.proposed_block = None
        self.ballot_Num = 0
        self.accept_Val = None
        self.accept_Num = 0
        self.current_depth = 0

        self.promised_peers = set()
        self.accepted_peers = set()

        self.highest_accepted_num = None
        self.highest_accepted_val = None
        self.decision_sent = False

        # Initialize persistence layer
        self.persistence = BlockchainPersistence(self.id, self.debug)
        self.load_state()

    def load_state(self):
        """Load persisted blockchain and account state from disk"""
        try:
            # Load blockchain from JSONL file
            self.blockchain = self.persistence.load_blockchain()
            if self.debug:
                print(f"[DEBUG C-{self.id}] Loaded blockchain with {self.blockchain.len} blocks")
            
            # Load account table from JSON file
            accounts = self.persistence.load_accounts()
            if accounts:
                self.account_table = accounts
            if self.debug:
                print(f"[DEBUG C-{self.id}] Loaded account table: {self.account_table}")
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Error loading state: {e}")
            # Fall back to defaults if loading fails
            self.blockchain = BlockChain()
            self.account_table = {i: 100 for i in range(1, 6)}

    def print_blockchain(self):
        with self.lock:
            print(self.blockchain)

    def print_table(self):
        with self.lock:
            print(self.account_table)
    
    def fix(self):
        self.dead = False
        # Reload state from disk after recovery
        self.load_state()
        if self.debug:
            print(f"[DEBUG C-{self.id}] Process fixed and state reloaded. Current depth: {self.blockchain.len}")
        
        # Request blockchain sync from a random peer
        self.request_blockchain_sync()
    
    def request_blockchain_sync(self):
        """Request blockchain from other peers to catch up after recovery"""
        import random
        peers = [i for i in range(1, 6) if i != self.id]
        target = random.choice(peers)
        
        msg = {
            "type": "SyncRequest",
            "from": self.id,
            "current_depth": self.blockchain.len
        }
        self.send(target, msg)
        if self.debug:
            print(f"[DEBUG C-{self.id}] Requesting blockchain sync from C-{target} (my depth: {self.blockchain.len})")
    
    def handle_sync_request(self, req):
        """Handle blockchain sync request from a peer"""
        requester_id = req["from"]
        requester_depth = req["current_depth"]
        my_depth = self.blockchain.len
        
        if self.debug:
            print(f"[DEBUG C-{self.id}] Received sync request from C-{requester_id} (their depth: {requester_depth}, my depth: {my_depth})")
        
        if my_depth > requester_depth:
            # Send missing blocks
            blocks_to_send = []
            for i in range(requester_depth, my_depth):
                block = self.blockchain[i]
                blocks_to_send.append({
                    "tx": block.transaction,
                    "nonce": block.nonce,
                    "hash_value": block.hash_value,
                    "hash_pointer": block.hash_pointer,
                    "depth": i + 1
                })
            
            reply = {
                "type": "SyncResponse",
                "from": self.id,
                "blocks": blocks_to_send,
                "total_depth": my_depth
            }
            self.send(requester_id, reply)
            if self.debug:
                print(f"[DEBUG C-{self.id}] Sending {len(blocks_to_send)} blocks to C-{requester_id}")
    
    def handle_sync_response(self, req):
        """Handle blockchain sync response from a peer"""
        sender_id = req["from"]
        blocks = req["blocks"]
        total_depth = req["total_depth"]
        
        if self.debug:
            print(f"[DEBUG C-{self.id}] Received {len(blocks)} blocks from C-{sender_id}")
        
        with self.lock:
            for block_data in blocks:
                depth = block_data["depth"]
                
                # Reconstruct block
                new_block = Block.reconstruct(
                    tx=block_data["tx"],
                    nonce=block_data["nonce"],
                    hash_value=block_data["hash_value"],
                    prev=self.blockchain.get_tail(),
                    hash_pointer=block_data["hash_pointer"]
                )
                
                # Apply to blockchain and accounts
                self.blockchain.append(new_block)
                transaction = new_block.transaction
                self.account_table[int(transaction[0])] -= int(transaction[2])
                self.account_table[int(transaction[1])] += int(transaction[2])
                
                # Write to disk as decided
                try:
                    self.persistence.write_block(block_data, state="decided", depth=depth)
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG C-{self.id}] Error writing synced block: {e}")
            
            # Save updated account table
            try:
                self.persistence.save_accounts(self.account_table)
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG C-{self.id}] Error saving accounts after sync: {e}")
        
        if self.debug:
            print(f"[DEBUG C-{self.id}] Blockchain synced. New depth: {self.blockchain.len}")
    
    def send(self, target_id, msg):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_socket:
                s_socket.connect((self.ip, target_id * 1234))
                if self.debug:
                    print(f"[DEBUG C-{self.id}] Sending to C-{target_id}: {msg['type']}")
                payload = json.dumps(msg).encode()
                s_socket.sendall(payload)
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Could not send message to C-{target_id}, Error: {e}")

    def send_prepare(self):
        promised = getattr(self, "promised_ballot", (0, 0))
        self.ballot_Num = max(self.ballot_Num, promised[0]) + 1  
        self.ballot = (self.ballot_Num, self.id)       

        self.current_depth = self.blockchain.len + 1
        self.promised_peers = set()
        self.accepted_peers = set()
        self.decision_sent = False

        self.highest_accepted_num = None
        self.highest_accepted_val = None
        
        # Track peer depths for recovery
        self.peer_depths = {}

        msg = {
            "type": "Prepare",
            "ballot": self.ballot,
            "from": self.id,
            "depth": self.current_depth
        }

        for i in range(1, 6):
            if i != self.id:
                self.send(i, msg)

    def handle_prepare(self, req):
        ballot = tuple(req["ballot"])
        proposer_id = req["from"]
        depth = req["depth"]

        local_depth = self.blockchain.len
        
        # Detection: If incoming depth is far behind, proposer needs to catch up
        if depth < local_depth:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Prepare from C-{proposer_id} has stale depth {depth} < my depth {local_depth}")
            # Send sync info to help them catch up
            self.send_catchup_info(proposer_id, depth, local_depth)
            return
        
        # Normal case: depth is current or ahead
        if depth <= local_depth:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring Prepare from C-{proposer_id} with depth {depth} <= local depth {local_depth}")
            return

        promised = getattr(self, "promised_ballot", (0, 0))
        if ballot < promised:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring Prepare from C-{proposer_id} with ballot {ballot} < promised {promised}")
            return

        self.promised_ballot = ballot

        accepted_ballot = self.highest_accepted_num 
        accepted_val = self.highest_accepted_val

        reply_msg = {
            "type": "Promise",
            "ballot": ballot,
            "from": self.id,
            "depth": depth,
            "current_depth": self.blockchain.len,  # Include my current depth
            "accepted_ballot": accepted_ballot,
            "accepted_tx": accepted_val.transaction if accepted_val else None,
            "accepted_nonce": accepted_val.nonce if accepted_val else None,
            "accepted_hash": accepted_val.hash_value if accepted_val else None,
            "accepted_hash_pointer": accepted_val.hash_pointer if accepted_val else None
        }

        self.send(proposer_id, reply_msg)
    
    def send_catchup_info(self, peer_id, their_depth, my_depth):
        """Inform peer they are behind and send catch-up blocks"""
        if self.debug:
            print(f"[DEBUG C-{self.id}] Helping C-{peer_id} catch up from depth {their_depth} to {my_depth}")
        
        # Send missing blocks
        blocks_to_send = []
        for i in range(their_depth, my_depth):
            block = self.blockchain[i]
            blocks_to_send.append({
                "tx": block.transaction,
                "nonce": block.nonce,
                "hash_value": block.hash_value,
                "hash_pointer": block.hash_pointer,
                "depth": i + 1
            })
        
        msg = {
            "type": "CatchUp",
            "from": self.id,
            "blocks": blocks_to_send,
            "total_depth": my_depth
        }
        self.send(peer_id, msg)
    
    def handle_catchup(self, req):
        """Handle catch-up information from peer"""
        sender_id = req["from"]
        blocks = req["blocks"]
        total_depth = req["total_depth"]
        
        if self.debug:
            print(f"[DEBUG C-{self.id}] Receiving catch-up info from C-{sender_id}: {len(blocks)} blocks")
        
        with self.lock:
            for block_data in blocks:
                depth = block_data["depth"]
                
                # Only add if we don't already have this block
                if depth > self.blockchain.len:
                    new_block = Block.reconstruct(
                        tx=block_data["tx"],
                        nonce=block_data["nonce"],
                        hash_value=block_data["hash_value"],
                        prev=self.blockchain.get_tail(),
                        hash_pointer=block_data["hash_pointer"]
                    )
                    
                    self.blockchain.append(new_block)
                    transaction = new_block.transaction
                    self.account_table[int(transaction[0])] -= int(transaction[2])
                    self.account_table[int(transaction[1])] += int(transaction[2])
                    
                    # Write to disk
                    try:
                        self.persistence.write_block(block_data, state="decided", depth=depth)
                    except Exception as e:
                        if self.debug:
                            print(f"[DEBUG C-{self.id}] Error writing catch-up block: {e}")
            
            # Save accounts
            try:
                self.persistence.save_accounts(self.account_table)
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG C-{self.id}] Error saving accounts: {e}")
        
        if self.debug:
            print(f"[DEBUG C-{self.id}] Caught up to depth {self.blockchain.len}")

    def handle_promise(self, req):
        promised_id = req["from"]
        ballot = tuple(req["ballot"])
        peer_depth = req.get("current_depth", self.current_depth - 1)

        if ballot != getattr(self, "ballot", None):
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring Promise from C-{promised_id} with ballot {ballot} != current ballot {getattr(self,'ballot',None)}")
            return

        self.promised_peers.add(promised_id)
        
        # Track peer depth
        self.peer_depths[promised_id] = peer_depth
        
        # Check if peer is behind
        if peer_depth < self.blockchain.len:
            if self.debug:
                print(f"[DEBUG C-{self.id}] C-{promised_id} is behind (depth {peer_depth} vs my {self.blockchain.len})")
            self.send_catchup_info(promised_id, peer_depth, self.blockchain.len)
        
        # Check if I'm behind
        elif peer_depth > self.blockchain.len:
            if self.debug:
                print(f"[DEBUG C-{self.id}] I am behind C-{promised_id} (my depth {self.blockchain.len} vs their {peer_depth})")
            # Request catch-up
            msg = {
                "type": "SyncRequest",
                "from": self.id,
                "current_depth": self.blockchain.len
            }
            self.send(promised_id, msg)

        accepted_ballot_raw = req.get("accepted_ballot", None)
        accepted_tx = req.get("accepted_tx", None)

        accepted_ballot = None
        if accepted_ballot_raw is not None:
            if isinstance(accepted_ballot_raw, list):
                accepted_ballot = tuple(accepted_ballot_raw)
            else:
                accepted_ballot = accepted_ballot_raw

        if accepted_ballot is not None and accepted_tx is not None:
            if (self.highest_accepted_num is None) or (accepted_ballot > self.highest_accepted_num):
                self.highest_accepted_num = accepted_ballot
                self.highest_accepted_val = Block.reconstruct(
                    tx=req["accepted_tx"],
                    nonce=req["accepted_nonce"],
                    hash_value=req["accepted_hash"],
                    prev=self.blockchain.get_tail(),
                    hash_pointer=req["accepted_hash_pointer"]
                )
                if self.proposed_block is None:
                    self.proposed_block = self.highest_accepted_val

        if len(self.promised_peers) == 2:
            self.send_accept()

    def send_accept(self):
        block = self.proposed_block
        msg = {
            "type": "Accept",
            "ballot": self.ballot,
            "from": self.id,
            "depth": self.current_depth,
            "leader_depth": self.blockchain.len,  # Include leader's blockchain depth
            "tx": block.transaction,
            "nonce": block.nonce,
            "hash_value": block.hash_value,
            "hash_pointer": block.hash_pointer
        }
        for i in range(1,6):
            if i != self.id:
                self.send(i, msg)

    def handle_accept(self, req):
        ballot = tuple(req["ballot"])
        proposer_id = req["from"]
        depth = req["depth"]
        leader_depth = req.get("leader_depth", depth - 1)

        if depth <= self.blockchain.len:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring Accept from C-{proposer_id} with depth {depth} <= local depth {self.blockchain.len}")
            return
        
        # Check if leader is behind
        if leader_depth < self.blockchain.len:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Leader C-{proposer_id} is behind (depth {leader_depth} vs my {self.blockchain.len})")
            self.send_catchup_info(proposer_id, leader_depth, self.blockchain.len)

        promised = getattr(self, "promised_ballot", (0,0))
        if ballot < promised:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring Accept from C-{proposer_id} with ballot {ballot} < promised {promised}")
            return

        self.promised_ballot = ballot
        self.highest_accepted_num = ballot
        self.highest_accepted_val = Block.reconstruct(tx = req["tx"],
                                                      nonce=req["nonce"],
                                                      hash_value=req["hash_value"],
                                                      prev=self.blockchain.get_tail(),
                                                      hash_pointer=req["hash_pointer"])
        self.accept_Val = self.highest_accepted_val

        # Write block as tentative when accepting (per spec)
        try:
            block_dict = {
                "tx": req["tx"],
                "nonce": req["nonce"],
                "hash_value": req["hash_value"],
                "hash_pointer": req["hash_pointer"]
            }
            self.persistence.write_block(block_dict, state="tentative", depth=depth)
            if self.debug:
                print(f"[DEBUG C-{self.id}] Wrote tentative block at depth {depth}")
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Error writing tentative block: {e}")

        reply_msg = {
            "type": "Accepted",
            "ballot": ballot,
            "from": self.id,
            "current_depth": self.blockchain.len  # Include my depth
        }

        self.send(proposer_id, reply_msg)

    def handle_accepted(self, req):
        accepted_id = req["from"]
        ballot = tuple(req["ballot"])
        peer_depth = req.get("current_depth", self.current_depth - 1)

        if ballot != getattr(self, "ballot", None):
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring Accepted from C-{accepted_id} with ballot {ballot} != current ballot {getattr(self,'ballot',None)}")
            return

        self.accepted_peers.add(accepted_id)
        
        # Check if peer is behind
        if peer_depth < self.blockchain.len:
            if self.debug:
                print(f"[DEBUG C-{self.id}] C-{accepted_id} is behind after accepting")
            self.send_catchup_info(accepted_id, peer_depth, self.blockchain.len)

        if len(self.accepted_peers) == 2:
            self.send_decision()

    def send_decision(self):
        with self.lock:
            if self.decision_sent:
                return
            self.decision_sent = True

        block = self.proposed_block

        # Leader writes block as decided immediately (agreement reached)
        if block is not None:
            try:
                block_dict = {
                    "tx": block.transaction,
                    "nonce": block.nonce,
                    "hash_value": block.hash_value,
                    "hash_pointer": block.hash_pointer
                }
                self.persistence.write_block(block_dict, state="decided", depth=self.current_depth)
                if self.debug:
                    print(f"[DEBUG C-{self.id}] Leader wrote decided block at depth {self.current_depth}")
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG C-{self.id}] Error writing decided block: {e}")

        msg = {
            "type": "Decision",
            "from": self.id,
            "depth": self.current_depth,
            "tx": block.transaction,
            "nonce": block.nonce,
            "hash_value": block.hash_value,
            "hash_pointer": block.hash_pointer
        }
        for i in range(1,6):
            if i != self.id:
                self.send(i, msg)

        # Apply to in-memory structures (don't write to disk again)
        self.apply_decision_to_memory(block)
        
        # Reset Paxos state for next round
        self.promised_peers = set()
        self.accepted_peers = set()

    def handle_decision(self, req):
        depth = req.get("depth", self.blockchain.len + 1)
        
        # Detection: If decision depth is ahead of us, we're behind
        if depth > self.blockchain.len + 1:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Decision depth {depth} > my depth {self.blockchain.len + 1}, I'm behind!")
            # Request sync
            self.request_blockchain_sync()
            return

        if depth < self.blockchain.len + 1:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring Decision with depth {depth} < local depth {self.blockchain.len + 1}")
            return

        new_block = Block.reconstruct(tx = req["tx"],
                                      nonce=req["nonce"],
                                      hash_value=req["hash_value"],
                                      prev=self.blockchain.get_tail(),
                                      hash_pointer=req["hash_pointer"])
        
        # Mark the tentative block as decided
        try:
            self.persistence.mark_block_decided(depth)
            if self.debug:
                print(f"[DEBUG C-{self.id}] Marked block at depth {depth} as decided")
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Error marking block decided: {e}")
        
        # Apply to in-memory structures
        self.apply_decision_to_memory(new_block)

    def apply_decision_to_memory(self, new_block):
        """Apply decision to in-memory blockchain and account table without disk writes"""
        transaction = new_block.transaction
        with self.lock:
            self.blockchain.append(new_block)
            self.account_table[int(transaction[0])] -= int(transaction[2])
            self.account_table[int(transaction[1])] += int(transaction[2])
        
        if self.debug:
            print(f"[DEBUG C-{self.id}] Applied transaction {transaction} to blockchain (depth={self.blockchain.len})")
            print(f"[DEBUG C-{self.id}] Updated account table: {self.account_table}")
        
        # Save updated account table to disk
        try:
            self.persistence.save_accounts(self.account_table)
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Error saving accounts: {e}")

    def moneyTransfer(self, from_id, to_id, amount):
        from_id = int(from_id)
        to_id = int(to_id)
        amount = int(amount)

        if from_id not in self.account_table or to_id not in self.account_table:
            print("Invalid account ID")
            return
        
        if amount <= 0:
            print("Amount must be positive")
            return
        
        with self.lock:
            current_balance = self.account_table.get(from_id, 0)
            if current_balance < amount:
                print(f"Insufficient balance in account {from_id}. Current balance: {current_balance}, amount needed: {amount}")
                return
            
        if self.debug:
            print(f"[DEBUG C-{self.id}] Transfer from C-{from_id}, to C-{to_id}, amount={amount}")

        self.proposed_block = self.blockchain.new_block((from_id, to_id, amount))
        self.send_prepare()

    def _listener_thread(self):
        c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        c_socket.bind((self.ip, self.id * 1234))
        c_socket.listen(5)
        c_socket.settimeout(1.0)

        if self.debug:
            print(f"[DEBUG C-{self.id}] Listening on port {self.id*1234}")

        while True:
            try:
                conn, addr = c_socket.accept()
                msg = conn.recv(4096).decode().strip()  # Increased buffer for block data

                req = json.loads(msg)
                client_id = req.get('from', None)

                if self.debug:
                    print(f"[DEBUG C-{self.id}] Received {req['type']} from C-{client_id}")

                if not self.dead:
                    self.request_queue.put(req)
                elif self.debug:
                    print(f"[DEBUG C-{self.id}] Process dead, ignoring")

                conn.close()
            except socket.timeout:
                continue

    def _worker_thread(self):
        while True:
            req = self.request_queue.get()
            time.sleep(3)  # Simulated network delay
            self.handle_request(req)
            self.request_queue.task_done()

    def handle_request(self, req):
        msg_type = req.get("type", None)
        if msg_type is None:
            return
        if self.debug:
            print(f"[DEBUG C-{self.id}] Handling {msg_type}") 

        match msg_type:
            case "Prepare":
                self.handle_prepare(req)
            case "Promise":
                self.handle_promise(req)
            case "Accept":
                self.handle_accept(req)
            case "Accepted":
                self.handle_accepted(req)
            case "Decision":
                self.handle_decision(req)
            case "SyncRequest":
                self.handle_sync_request(req)
            case "SyncResponse":
                self.handle_sync_response(req)
            case "CatchUp":
                self.handle_catchup(req)
            case "DEBUG":
                print(f"[DEBUG C-{self.id}] Debug Message from C-{req['from']}: {req['text']}")   
                debug_reply = {
                    "type": "DEBUG REPLY",
                    "from": self.id,
                    "text": req['text']
                }  
                self.send(int(req['from']), debug_reply)  
            case "DEBUG REPLY":    
                print(f"[DEBUG C-{self.id}] Debug Reply Message from C-{req['from']}: {req['text']}")