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
            s_socket.connect(("127.0.0.1", id * 1234))
            if DEBUG:
                print(f"[DEBUG C-{ID}] Sending to C-{id}: {msg}")
            s_socket.sendall(f"ID={ID} - {msg}".encode())
    except (ConnectionRefusedError, ConnectionResetError):
        if DEBUG:
            print(f"[DEBUG C-{ID}] Could not send message to C-{id}")
        return "NOT FOUND"
    
def listen(p):
    global ID
    c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    c_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    c_socket.bind(('', ID * 1234))
    c_socket.listen(5)
    c_socket.settimeout(1.0)

    if DEBUG:
        print(f"[DEBUG C-{ID}] Listening on port {ID*1234}")

    while True:
        try:
            conn, addr = c_socket.accept()
            msg = conn.recv(1024).decode().strip()

            time.sleep(3) # simulated network delay

            match = re.search(r'ID=(\d+) - (.*)', msg)
            client_id = int(match.group(1))
            req = match.group(2)

            if DEBUG:
                print(f"[DEBUG C-{ID}] Received from C-{client_id}: {req}")

            if not p.dead:
                if req.startswith(f"DEBUG - "):
                    reply_msg = req[len(f"DEBUG - "):]
                    send_request(client_id, reply_msg)
                else:
                    pass

            conn.close()
        except socket.timeout:
            continue

class Peer:
    def __init__(self):
        self.blockchain = BlockChain()

        table = {}
        for i in range(1,6):
            table[i] = 100

        self.account_table = table
        self.dead = False

    def fix(self):
        self.dead = False

def main():
    p = Peer()

    threading.Thread(target=listen, args=(p,), daemon=True).start()

    while True:
        cmd = input()
        if p.dead and cmd != "fixProcess": print("This process is dead."); continue
        match cmd:
            case "failProcess":
                p.dead = True

            case "fixProcess":
                if p.dead: p.fix()
                else: print("This process is alive")

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
                    send_request(int(args[0]), "DEBUG - " + args[1])
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