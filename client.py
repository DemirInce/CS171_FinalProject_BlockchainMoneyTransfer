from peer import Peer
import re
import argparse

def main(id, debug):
    p = Peer(id, debug)

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

                if parse and parse.group(1) == "moneyTransfer":
                    args = [arg.strip() for arg in parse.group(2).split(',')]
                    print("Arguments:", args)
                elif parse and parse.group(1) == "debugMessage" and debug:
                    args = [arg.strip() for arg in parse.group(2).split(',')]
                    p.send(int(args[0]), "DEBUG - " + args[1])
                else:
                    print("Unknown Command")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client")
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--debug", type=bool, required=False, default=False)
    args = parser.parse_args()

    main(args.id, args.debug)