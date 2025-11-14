from blockchain import BlockChain
import threading
import queue
import socket
import time
import ast
import re

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
        threading.Thread(target=self._worker_thread, daemon=True).start()

    def print_blockchain(self):
        with self.lock:
            print(self.blockchain)

    def print_table(self):
        with self.lock:
            print(self.account_table)

    def moneyTransfer(self, from_id, to_id, amount): # TODO
        if self.debug:
            print(f"[DEBUG C-{self.id}] Transfer from C-{from_id}, to C-{to_id}, amount={amount}")

    def send(self, target_id, msg):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_socket:
                s_socket.connect((self.ip, target_id * 1234))
                if self.debug:
                    print(f"[DEBUG C-{self.id}] Sending to C-{target_id}: {msg}")
                s_socket.sendall(f"ID={self.id} - {msg}".encode())
        except Exception as e:
            if self.debug:
                print(f"[DEBUG C-{self.id}] Could not send message to C-{target_id}, Error: {e}")

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
                time.sleep(3)  # Simulated network delay

                match = re.search(r'ID=(\d+) - (.*)', msg)
                client_id = int(match.group(1))
                req = match.group(2)

                if self.debug:
                    print(f"[DEBUG C-{self.id}] Received request from C-{client_id}: {req}")

                if not self.dead:
                    self.request_queue.put((client_id, req))

                conn.close()
            except socket.timeout:
                continue

    def _worker_thread(self):
        while True:
            client_id, req = self.request_queue.get()
            self.handle_request(client_id, req)
            self.request_queue.task_done()

    def handle_request(self, client_id, req):
        if req.startswith("DEBUG - "):
            reply_msg = req[len("DEBUG - "):]
            self.send(client_id, reply_msg)
        else:
            try:
                req_tupple = ast.literal_eval(req)
                if self.debug:
                    print(f"[DEBUG C-{self.id}] Handling request: {req_tupple}")               
            except:
                pass
