import hashlib
import random
import string

def sha256(data):
    return hashlib.sha256(data.encode()).hexdigest()

def generate_hash(transaction):
    while True:
        nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        h = sha256(str(transaction) + nonce)
        if h[-1] in '01234':
            return nonce, h
class Block:
    def __init__(self, value, previous=None):
        self.transaction = value

        self.nonce, self.hash_value = generate_hash(value)

        self.next = None
        self.prev = previous

        if previous:
            prev_data = str(previous.transaction) + previous.nonce + previous.hash_value
            self.hash_pointer = sha256(prev_data)
        else:
            self.hash_pointer = None
        
    def __repr__(self):
            return (f"Block(Tx={self.transaction}, "
                    f"Nonce={self.nonce}, "
                    f"Hash={self.hash_value[:10]}..., "
                    f"PrevHash={self.hash_pointer[:10] if self.hash_pointer else None}...)")
            
class BlockChain:
    def __init__(self):
        self.len = 0
        self.head = None
        self.tail = None

    def new_block(self, value):
        if self.len == 0:
            new_block = Block(value)
        else:
            new_block = Block(value, self.tail)
        return new_block       

    def append(self, block):
        if self.len == 0:
            self.head = self.tail = block
        else:
            self.tail.next = block
            self.tail = block

        self.len += 1

    def get_tail(self):
        return self.tail
    
    def __getitem__(self, n):
        if n < 0:
            n += self.len
        if n < 0 or n >= self.len:
            raise IndexError
        block = self.head
        for _ in range(n):
            block = block.next
        return block

    def __repr__(self):
        s = ""
        block = self.head
        for i in range(self.len):
            s = s + repr(block) + ('' if  i == self.len-1 else '\n')
            block = block.next 
        return s 
    
def main():
    bc = BlockChain()
    bc.append((1,2,10))
    bc.append((1,2,20))
    bc.append((2,1,10))

    print(bc.get_tail())

    print()

    print(bc[1])

    print()

    print(bc)

if __name__ == "__main__":
    main()



