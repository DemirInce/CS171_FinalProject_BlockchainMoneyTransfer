from peer import Peer
import argparse
import re

def main(id, debug, ip):
    p = Peer(id, debug, ip)

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
                p.print_blockchain()

            case "printBalance":
                p.print_table()

            case _:
                pattern = r'(\w+)\((.*?)\)'
                parse = re.match(pattern, cmd)
                args = [arg.strip() for arg in parse.group(2).split(',')]

                if parse and parse.group(1) == "moneyTransfer":
                    p.moneyTransfer(args[0], args[1], args[2])
                elif parse and parse.group(1) == "debugMessage" and debug:
                    p.send(int(args[0]), "DEBUG - " + args[1])
                else:
                    print("Unknown Command")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client")
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--debug", type=bool, required=False, default=False)
    parser.add_argument("--ip", type=str, required=False, default="127.0.0.1")

    args = parser.parse_args()

    main(args.id, args.debug, args.ip)