from blockchain import BlockChain
import re
import argparse
import socket
import time
import threading

def send_request(id, msg):
    global ID
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_socket:
            s_socket.connect(("127.0.0.1", id*1234))
            if DEBUG:
                print(f"[DEBUG C-{ID}] Sending to {id*1234}: {msg}")
            s_socket.sendall(msg.encode())
            rply = s_socket.recv(1024).decode()

            time.sleep(3)
            
            if DEBUG:
                print(f"[DEBUG C-{ID}] Received from {id*1234}: {rply}")

            return rply
    except ConnectionRefusedError:
        return "NOT FOUND"
    except ConnectionResetError:
        if DEBUG:
            print(f"[DEBUG C-{ID}] Connection reset by peer {id}")
        return "NOT FOUND"
    
def listen():
    global ID
    c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    c_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    c_socket.bind(('', ID*1234))
    c_socket.listen(5)
    c_socket.settimeout(1.0)

    if DEBUG:
        print(f"[DEBUG C-{ID}] Client listening on port {ID*1234}")

    while True:
        try:
            conn, _ = c_socket.accept()
            req = conn.recv(1024).decode().strip()
            conn.sendall(req.encode())
            conn.close()
        except socket.timeout:
            continue

def init_table():
    table = {}
    for i in range(1,6):
        table[i] = 100
    return table

class Peer:
    def __init__(self):
        self.blockchain = BlockChain()
        self.account_table = init_table()
        self.dead = False

    def fix(self):
        self.dead = False

def main():
    p = Peer()

    threading.Thread(target=listen, daemon=True).start()

    while True:
        cmd = input()
        if p.dead and cmd != "fixProcess": print("This process is dead."); continue
        match cmd:
            case "failProcess":
                p.dead = True
            case "fixProcess":
                p.fix()
            case "printBlockchain":
                print(p.blockchain)
            case "printBalance":
                print(p.account_table)
            case _:
                pattern = r'(\w+)\((.*?)\)'
                parse = re.match(pattern, cmd)

                if parse and parse.group(1) == "moneyTransfer":
                    args = [arg.strip() for arg in parse.group(2).split(',')]
                    print("Arguments:", args)
                elif parse and parse.group(1) == "debugMessage" and DEBUG:
                    args = [arg.strip() for arg in parse.group(2).split(',')]
                    send_request(int(args[0]), args[1])
                else:
                    print("Unknown Command")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client")
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--debug", type=bool, required=False, default=False)
    args = parser.parse_args()

    global DEBUG, ID
    DEBUG = args.debug
    ID = args.id

    main()