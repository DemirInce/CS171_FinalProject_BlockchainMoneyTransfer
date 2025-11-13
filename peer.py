from blockchain import BlockChain
import re

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

    p.blockchain.append((1,2,20))
    p.blockchain.append((2,1,10))

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
                else:
                    print("Unknown Command")

if __name__ == "__main__":
    main()
