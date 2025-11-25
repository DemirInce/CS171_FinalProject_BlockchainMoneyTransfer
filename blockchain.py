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

    @classmethod
    def reconstruct(cls, tx, nonce, hash_value, prev, hash_pointer):
        obj = cls.__new__(cls)
        obj.transaction = tx
        obj.nonce = nonce
        obj.hash_value = hash_value
        obj.next = None
        obj.prev = prev
        obj.hash_pointer = hash_pointer
        return obj  
    
    def verify(self, prev_block=None):
        expected_hash = sha256(str(self.transaction) + self.nonce)
        if self.hash_value != expected_hash:
            return False

        if prev_block:
            prev_data = str(prev_block.transaction) + prev_block.nonce + prev_block.hash_value
            expected_pointer = sha256(prev_data)
            if self.hash_pointer != expected_pointer:
                return False
        elif self.hash_pointer is not None:
            return False
        
        return True
        
    def __repr__(self):
            return (f"Block(Tx={self.transaction}, "
                    f"Nonce={self.nonce}, "
                    f"Hash={self.hash_value}, "
                    f"PrevHash={self.hash_pointer if self.hash_pointer else None})")
            
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
    
    def verify(self):
        current = self.head
        prev = None
        index = 0
        while current:
            if not current.verify(prev):
                return False
            prev = current
            current = current.next
            index += 1
        return True
    
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
    
    def __iter__(self):
        current = self.head
        while current:
            yield current
            current = current.next
    
def main():
    bc = BlockChain()

    b1 = bc.new_block((1,2,10))
    bc.append(b1)
    b2 = bc.new_block((1,2,20))
    bc.append(b2)
    b3 = bc.new_block((1,2,30))
    bc.append(b3)


    print(bc.get_tail())

    print()

    print(bc[1])

    print()

    print(bc)

    print(bc.get_tail().verify(bc.get_tail().prev))
    print(bc.verify())

if __name__ == "__main__":
    main()



