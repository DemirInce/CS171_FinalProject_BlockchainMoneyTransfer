from blockchain import BlockChain

def init_table():
    table = {}
    for i in range(1,6):
        table[i] = 100
    return table

class Peer:
    def __init__(self):
        self.blockchain = BlockChain()
        self.account_table = init_table()

def main():
    p = Peer()
    print(p.account_table)

if __name__ == "__main__":
    main()
