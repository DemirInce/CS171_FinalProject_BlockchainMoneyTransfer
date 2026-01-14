from blockchain import Block, BlockChain
from utils import *
import threading
import queue
import socket
import time
import json

class Peer:
    def __init__(self, id, debug=0, load=False):

        self.id = id
        self.debug = debug
        self.ip = "127.0.0.1"
        self.dead = False

        if load:
            at, pb, bc = load_file(f"./data/c_{self.id}.json")
            self.account_table = {int(k): v for k, v in at.items()} if isinstance(at, dict) else at
            self.promised_ballot = tuple(pb) if pb is not None else (0,0)
            self.blockchain = bc
        else:
            self.blockchain = BlockChain()
            self.account_table = {i: 100 for i in range(1,6)}
            self.promised_ballot = (0,0)    

            filepath = f"./data/c_{self.id}.json"
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                json.dump({"variables": {}, "blockchain": []}, f, indent=2)
            if self.debug:
                print(f"[DEBUG C-{self.id}] Reset state file {filepath} to empty")

        self.request_queue = queue.Queue()
        self.lock = threading.Lock()

        threading.Thread(target=self._listener_thread, daemon=True).start()
        for _ in range(4):
            threading.Thread(target=self._worker_thread, daemon=True).start()

        self.ballot_Num = 0
        self.current_depth = 0          
        self.proposed_ballot = (0,0)

        self.promised_peers = set()
        self.accepted_peers = set()

        self.highest_accepted_num = None
        self.highest_accepted_val = None
        self.decision_sent = False

        self.recovery_event = threading.Event()

    def print_blockchain(self):
        with self.lock:
            print(self.blockchain)

    def print_table(self):
        with self.lock:
            print(self.account_table)
    
    def fix(self):
        if self.debug:
            print(f"[DEBUG C-{self.id}] Fixing process.")
        msg = {"type": "Recovery", "from": self.id}
        for i in range(1,6):
            if i != self.id:
                self.send(i, msg)
        self.dead = False
    
    def send(self, target_id, msg):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_socket:
                s_socket.connect((self.ip, target_id * 1234))
                if self.debug == 1:
                    print(f"[DEBUG C-{self.id}] Sending to C-{target_id}: {msg}")
                elif self.debug == 2:
                    print(f"[DEBUG C-{self.id}] Sending to C-{target_id}, Type: {msg["type"]}")
                data = json.dumps(msg).encode()
                length = len(data).to_bytes(4, "big")
                s_socket.sendall(length + data)
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Could not send message to C-{target_id}, Error: {e}")

    def send_prepare(self):
        promised = getattr(self, "promised_ballot", (0,0))
        self.ballot_Num = max(self.ballot_Num, promised[0]) + 1
        self.ballot = (self.ballot_Num, self.id)

        self.current_depth = self.blockchain.len + 1

        with self.lock:
            self.promised_peers = set()
            self.accepted_peers = set()
            self.decision_sent = False
            self.highest_accepted_num = None
            self.highest_accepted_val = None

            if not hasattr(self, "proposed_block") or self.proposed_block is None:
                if self.debug:
                    print(f"[DEBUG C-{self.id}] Warning: sending Prepare with no proposed_block")

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
        if depth < local_depth + 1:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring 'Prepare' from C-{proposer_id} with depth {depth} <= local depth {local_depth}")
            return

        promised = getattr(self, "promised_ballot", (0,0))
        if ballot < promised:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring 'Prepare' from C-{proposer_id} with ballot {ballot} < promised {promised}")
            return

        with self.lock:
            self.promised_ballot = ballot

        reply_msg = {
            "type": "Promise",
            "ballot": ballot,
            "from": self.id,
            "depth": depth,
            "accepted_ballot": self.highest_accepted_num,
            "accepted_tx": self.highest_accepted_val.transaction if self.highest_accepted_val else None,
            "accepted_nonce": self.highest_accepted_val.nonce if self.highest_accepted_val else None,
            "accepted_hash": self.highest_accepted_val.hash_value if self.highest_accepted_val else None,
            "accepted_hash_pointer": self.highest_accepted_val.hash_pointer if self.highest_accepted_val else None
        }

        self.send(proposer_id, reply_msg)

    def handle_promise(self, req):
        promised_id = req["from"]
        ballot = tuple(req["ballot"])

        if ballot != getattr(self, "ballot", None):
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring 'Promise' from C-{promised_id} with ballot {ballot} != current ballot {getattr(self, 'ballot', None)}")
            return

        accepted_ballot_raw = req.get("accepted_ballot", None)
        accepted_tx = req.get("accepted_tx", None)
        accepted_nonce = req.get("accepted_nonce", None)
        accepted_hash = req.get("accepted_hash", None)
        accepted_hash_pointer = req.get("accepted_hash_pointer", None)

        accepted_ballot = None
        if accepted_ballot_raw is not None:
            if isinstance(accepted_ballot_raw, list):
                accepted_ballot = tuple(accepted_ballot_raw)
            else:
                accepted_ballot = accepted_ballot_raw

        with self.lock:
            self.promised_peers.add(promised_id)

            if accepted_ballot is not None and accepted_tx is not None:
                if (self.highest_accepted_num is None) or (accepted_ballot > self.highest_accepted_num):
                    if self.debug:
                        print(f"[DEBUG C-{self.id}] Adopting previous value reported by C-{promised_id} with accepted_ballot={accepted_ballot}")
                    try:
                        adopted = Block.reconstruct(
                            tx=accepted_tx,
                            nonce=accepted_nonce,
                            hash_value=accepted_hash,
                            prev=self.blockchain.get_tail(),  
                            hash_pointer=accepted_hash_pointer
                        )
                        self.highest_accepted_num = accepted_ballot
                        self.highest_accepted_val = adopted
                    except Exception as e:
                        if self.debug:
                            print(f"[DEBUG C-{self.id}] Failed to reconstruct accepted block from C-{promised_id}: {e}")


            if len(self.promised_peers) == 2:
                if self.highest_accepted_val is not None:
                    self.proposed_block = self.highest_accepted_val
                send_accept_needed = True
            else:
                send_accept_needed = False

        if send_accept_needed:
            self.send_accept()

    def send_accept(self):
        with self.lock:
            block = self.proposed_block
            ballot = self.ballot
            depth = self.current_depth

        if block is None:
            if self.debug:
                print(f"[DEBUG C-{self.id}] send_accept called but no proposed_block set for ballot {ballot}")
            return

        msg = {
            "type": "Accept",
            "ballot": ballot,
            "from": self.id,
            "depth": depth,
            "tx": block.transaction,
            "nonce": block.nonce,
            "hash_value": block.hash_value,
            "hash_pointer": block.hash_pointer
        }
        for i in range(1, 6):
            if i != self.id:
                self.send(i, msg)

    def handle_accept(self, req):
        ballot = tuple(req["ballot"])
        proposer_id = req["from"]
        depth = req["depth"]

        if depth < self.blockchain.len + 1:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring 'Accept' from C-{proposer_id} with depth {depth} <= local depth {self.blockchain.len}")
            return
        elif depth > self.blockchain.len + 1:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Appears to be behind C-{proposer_id}")
            print("Recovering")
            msg = {"type": "Recovery", "from": self.id}
            self.recovery_event.clear()
            self.send(proposer_id, msg)
            self.recovery_event.wait()

        promised = getattr(self, "promised_ballot", (0,0))
        if ballot < promised:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring 'Accept' from C-{proposer_id} with ballot {ballot} < promised {promised}")
            return
        
        new_block = Block.reconstruct(
            tx=req["tx"],
            nonce=req["nonce"],
            hash_value=req["hash_value"],
            prev=req["hash_pointer"],
            hash_pointer=req["hash_pointer"]
        )
        
        if not new_block.verify(self.blockchain.get_tail()):
            if self.debug:
                print(f"[DEBUG C-{self.id}] Rejecting 'Accept' from C-{proposer_id}: Block verification failed")
            return

        with self.lock:
            self.promised_ballot = ballot
            self.highest_accepted_num = ballot
            self.highest_accepted_val = new_block

        reply_msg = {
            "type": "Accepted",
            "ballot": ballot,
            "from": self.id,
        }

        self.send(proposer_id, reply_msg)

    def handle_accepted(self, req):
        accepted_id = req["from"]
        ballot = tuple(req["ballot"])

        if ballot != getattr(self, "ballot", None):
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring 'Accepted' from C-{accepted_id} with ballot {ballot} != current ballot {getattr(self, 'ballot', None)}")
            return

        with self.lock:
            self.accepted_peers.add(accepted_id)

        if len(self.accepted_peers) == 2 and not self.decision_sent:
            self.send_decision()
        elif self.debug:
            if len(self.accepted_peers) < 2:
                print(f"[DEBUG C-{self.id}] Not enough peers have accepted yet. Count: {len(self.accepted_peers)}")
            else:
                print(f"[DEBUG C-{self.id}] Majority reached")

    def send_decision(self):
        with self.lock:
            if self.decision_sent:
                return
            self.decision_sent = True

        block = self.proposed_block

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

        self.implement_decision(block)
        self.promised_peers = set()
        self.accepted_peers = set()
        self.proposed_block = None

    def handle_decision(self, req):
        decider_id = req["from"]
        depth = req.get("depth", self.blockchain.len + 1)

        if depth < self.blockchain.len + 1:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Ignoring 'Decision' with depth {depth} < local depth {self.blockchain.len + 1}")
            return
        elif depth > self.blockchain.len + 1:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Appears to be behind C-{decider_id}")
            print("Recovering")
            msg = {"type": "Recovery", "from": self.id}
            self.recovery_event.clear()
            self.send(decider_id, msg)
            self.recovery_event.wait()

        new_block = Block.reconstruct(tx = req["tx"],
                                      nonce=req["nonce"],
                                      hash_value=req["hash_value"],
                                      prev=req["hash_pointer"],
                                      hash_pointer=req["hash_pointer"])
        
        if not new_block.verify(self.blockchain.get_tail()):
            if self.debug:
                print(f"[DEBUG C-{self.id}] Rejecting 'Decision' from C-{decider_id}: Block verification failed")
            return

        self.implement_decision(new_block)

    def implement_decision(self, new_block):
        transaction = new_block.transaction
        with self.lock:
            self.blockchain.append(new_block)
            self.account_table[int(transaction[0])] -= int(transaction[2])
            self.account_table[int(transaction[1])] += int(transaction[2])

        self.ballot = None
        self.highest_accepted_num = None
        self.highest_accepted_val = None         

        handle_file(f"./data/c_{self.id}.json", {"account_table": self.account_table, "promised_ballot": self.promised_ballot}, new_block)
        print("Done.")

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

    def handle_recovery(self, req):
        from_id = req["from"]
        blockchain_list = []
        for block in self.blockchain:
            blockchain_list.append(dict_from_block(block))
        msg = {
            "type": "Recovery Reply",
            "from": self.id,
            "blockchain": blockchain_list,
            "account_table": self.account_table,
            "promised_ballot": self.promised_ballot
        }
        self.send(from_id, msg)

    def recover(self, req):
        from_id = req["from"]
        self.recovery_event.clear()

        blockchain_list = req["blockchain"]
        with self.lock:
            if (len(blockchain_list) < self.blockchain.len) or (len(blockchain_list) == self.blockchain.len and from_id < self.id):
                self.recovery_event.set()
                return

        new_blockchain = build_blockchain_from_list(blockchain_list)
        if new_blockchain.verify() == False:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Received invalid blockchain from C-{from_id}")

        with self.lock:
            self.account_table = {int(k): v for k, v in req["account_table"].items()}
            self.blockchain = new_blockchain
            self.promised_ballot = max(getattr(self, "promised_ballot", (0,0)), tuple(req.get("promised_ballot", (0,0))))
            self.highest_accepted_num = None
            self.highest_accepted_val = None
            self.proposed_block = None

        overwrite_file(f"./data/c_{self.id}.json", self.account_table, self.promised_ballot, new_blockchain)
        self.recovery_event.set()
        print("Done.")


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

                length_bytes = conn.recv(4)
                length = int.from_bytes(length_bytes, "big")
                data = b""
                while len(data) < length:
                    data += conn.recv(length - len(data))

                req = json.loads(data.decode())
                client_id = req.get('from', None)

                if self.debug == 1:
                    print(f"[DEBUG C-{self.id}] Received request from C-{client_id}: {req}")
                elif self.debug == 2:
                    print(f"[DEBUG C-{self.id}] Received request from C-{client_id}, Type: {req["type"]}")

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
            time.sleep(3) # Simulated network delay
            self.handle_request(req)
            self.request_queue.task_done()

    def handle_request(self, req):
        msg_type = req.get("type", None)
        if msg_type is None:
            return
        if self.debug == 1:
            print(f"[DEBUG C-{self.id}] Handling request: {req}") 
        elif self.debug == 2:
            print(f"[DEBUG C-{self.id}] Handling request from C-{req["from"]}, Type: {req["type"]}") 

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
            case "Recovery":
                self.handle_recovery(req)
            case "Recovery Reply":
                self.recover(req) 
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
                 
# Paxos Message format:
# type: "Promise", ballot: ballot_Num, from: proposer_id, depth: depth, accepted_ballot: _, accepted_tx: _, accepted_nonce: _, accepted_hash: _, accepted_hash_pointer: _
# type: "Prepare", ballot: ballot_Num, from: proposer_id, depth: depth
# type: "Accept", ballot: ballot_Num, from: proposer_id, tx: _, nonce: _, hash_value: _, hash_pointer: _
# type: "Accepted", ballot: ballot_Num, from: accepter_id
# type: "Decision", tx: _, nonce: _, hash_value: _, hash_pointer: _

# type: "Recovery", from: id
# type: "Recovery Reply", from: id, bc: serialized_blockchain, at: account_table, pb: promised_ballot, han: highest_accepted_num, hav: highest_accepted_val
