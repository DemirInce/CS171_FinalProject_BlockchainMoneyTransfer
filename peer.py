from blockchain import BlockChain

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