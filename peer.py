from blockchain import BlockChain
from blockchain import Block
from enum import Enum
import threading
import queue
import socket
import time
import json

#class State(Enum):
#    IDLE = 0                # == WAIT_FOR_PREPARE or New Transaction
#    WAIT_FOR_PROMISE = 1    # == SENT_PREPRARE
#    SENT_PROMISE = 2        # == WAIT_FOR_ACCEPT (after majority promises)
#    WAIT_FOR_ACCEPTED = 3   # == SENT_ACCEPT (waiting for majority accepted))
#    SENT_ACCEPTED = 4       # == WAIT_FOR_DECIDE (after majority accepted)

# I realized we never actually do anything with the states - D

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

        self.highest_accepted_num = -1
        self.highest_accepted_val = None

    def print_blockchain(self):
        with self.lock:
            print(self.blockchain)

    def print_table(self):
        with self.lock:
            print(self.account_table)
    
    def fix(self):
        self.dead = False
        if self.debug:
            print(f"[DEBUG C-{self.id}] Process fixed.")
    
    def send(self, target_id, msg):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_socket:
                s_socket.connect((self.ip, target_id * 1234))
                if self.debug:
                    print(f"[DEBUG C-{self.id}] Sending to C-{target_id}: {msg}")
                payload = json.dumps(msg).encode()
                s_socket.sendall(payload)
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Could not send message to C-{target_id}, Error: {e}")

    def send_prepare(self):
        self.ballot_Num += 1
        self.current_depth = self.blockchain.len + 1
        self.promise_count = 0
        self.highest_accepted_num = -1
        self.highest_accepted_val = None

        msg = {
            "type": "Prepare",
            "ballot": self.ballot_Num,
            "from": self.id,
            "depth": self.current_depth
        }

        for i in range(1,6):
            if i != self.id:
                self.send(i, msg)

    def handle_prepare(self, req):
        ballot = req["ballot"]
        proposer_id = req["from"]
        depth = req["depth"]

        local_depth = self.blockchain.len + 1
        if depth < local_depth:
            return
        
        if ballot < self.accept_Num:
            return
        
        self.accept_Num = ballot

        reply_msg = {
            "type": "Promise",
            "ballot": ballot,
            "from": self.id,
            "depth": depth,
            "accepted_ballot": self.accept_Num,
            "accepted_tx": self.accept_Val.transaction if self.accept_Val else None,
            "accepted_nonce": self.accept_Val.nonce if self.accept_Val else None,
            "accepted_hash": self.accept_Val.hash_value if self.accept_Val else None,
            "accepted_hash_pointer": self.accept_Val.hash_pointer if self.accept_Val else None
        }

        self.send(proposer_id, reply_msg)    

    def handle_promise(self, req):
        promised_id = req["from"]
        self.promised_peers.add(promised_id)
        if len(self.promised_peers) == 2: # 2 acceptor + 1 proposer = 3 majority of 5
            self.send_accept()

    def send_accept(self):
        block = self.proposed_block
        msg = {
            "type": "Accept",
            "ballot": self.ballot_Num,
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

    def handle_accept(self, req): 
        # Placeholder, implement proper accept checks TODO

        ballot = req["ballot"]
        proposer_id = req["from"]

        reply_msg = {
            "type": "Accepted",
            "ballot": ballot,
            "from": self.id,
        }

        self.send(proposer_id, reply_msg)


    def handle_accepted(self, req):
        accepted_id = req["from"]
        self.accepted_peers.add(accepted_id)
        if len(self.accepted_peers) == 2: # 2 acceptor + 1 proposer = 3 majority of 5
            self.send_decision()

    def send_decision(self):
        if self.decision_sent: return
        self.decision_sent = True

        block = self.proposed_block
        msg = {
            "type": "Decision",
            "from": self.id,
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

    def handle_decision(self, req):
        new_block = Block.reconstruct(tx = req["tx"],
                                      nonce=req["nonce"], 
                                      hash_value=req["hash_value"], 
                                      prev=self.blockchain.get_tail(),
                                      hash_pointer=req["hash_pointer"])
        self.implement_decision(new_block)

    def implement_decision(self, new_block):
        transaction = new_block.transaction
        with self.lock:
            self.blockchain.append(new_block)
            self.account_table[int(transaction[0])] -= int(transaction[2])
            self.account_table[int(transaction[1])] += int(transaction[2])

    def moneyTransfer(self, from_id, to_id, amount):
        if self.debug:
            print(f"[DEBUG C-{self.id}] Transfer from C-{from_id}, to C-{to_id}, amount={amount}")
        self.proposed_block = self.blockchain.new_block((from_id, to_id, amount))
        self.decision_sent = False
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
                msg = conn.recv(1024).decode().strip()

                req = json.loads(msg)
                client_id = req.get('from', None)

                if self.debug:
                    print(f"[DEBUG C-{self.id}] Received request from C-{client_id}: {req}")

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
            print(f"[DEBUG C-{self.id}] Handling request: {req}") 

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
# type: "Promise", ballot: ballot_Num, from: proposer_id, depth: depth, accepted_ballot: , accepted_tx: , accepted_nonce: , accepted_hash: , accepted_hash_pointer:
# type: "Prepare", ballot: ballot_Num, from: proposer_id, depth: depth
# type: "Accept", ballot: ballot_Num, from: proposer_id, tx: , nonce: , hash_value: , hash_pointer: 
# type: "Accepted", ballot: ballot_Num, from: accepter_id
# type: "Decision", tx: , nonce: , hash_value: , hash_pointer:

# TODO: Issues acording to ChatGPT:
# - Ballot numbers are not validated in handle_accept, so outdated proposals can overwrite newer ones.
# - romised/accepted peer tracking is global instead of per ballot and never reset correctly.
# - Accepted values are not persisted, so crash recovery breaks safety.
# - Highest accepted value from promises is ignored, violating Paxos safety.
# - Depth/chaining is not fully validated, so block ordering can diverge.
# - No rejection/NACK mechanism for lower ballot messages.
# - Multiple concurrent proposers will break the protocol due to missing conflict handling.
