from peer import Peer
import argparse
import re

alias_table = {
    "fail": "failprocess",
    "fix": "fixprocess",
    "mt": "moneytransfer",
    "bal": "printbalance",
    "blocks": "printblockchain",
    "debug": "debugmessage"
}

def main(id, debug, load):
    p = Peer(id, debug, load)

    while True:
        cmd = input().lower()
        cmd = alias_table.get(cmd, cmd)
        if p.dead and cmd != "fixprocess": 
            print("This process is dead.")
            continue
        match cmd:
            case "failprocess":
                p.dead = True

            case "fixprocess":
                if p.dead: 
                    p.fix()
                else: 
                    print("This process is alive")

            case "printblockchain":
                p.print_blockchain()

            case "printbalance":
                p.print_table()

            case _:
                pattern = r'(\w+)\((.*?)\)'
                parse = re.match(pattern, cmd)
                if parse:
                    cmd_root = alias_table.get(parse.group(1), parse.group(1))
                    args = [arg.strip() for arg in parse.group(2).split(',')]
                    if cmd_root == "moneytransfer":
                        p.moneyTransfer(args[0], args[1], args[2])
                        continue
                    elif cmd_root == "debugmessage" and debug:
                        p.send(int(args[0]), {"type": "DEBUG", "from": p.id, "text": args[1]})
                        continue
                print("Unknown Command")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client")
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--load", type=bool, required=False, default=False)
    parser.add_argument("--debug", type=str, required=False, default='None')
    args = parser.parse_args()

    debug = args.debug.lower()
    debug_num = 0
    match debug:
        case 'none':
            debug_num = 0
        case 'full':
            debug_num = 1
        case 'basic':
            debug_num = 2
        case _:
            debug_num = 0

    main(args.id, debug_num, args.load)
