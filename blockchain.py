class Block:
    def __init__(self, value):
        self.transaction= value

        self.next = None
        self.prev = None

class BlockChain:
    def __init__(self):
        self.len = 0
        self.head = None
        self.tail = None

    def append(self, value):
        if self.len == 0:
            self.head = self.tail = Block(value)
        else:
            self.tail.next = Block(value)
            self.tail.next.prev = self.tail
            self.tail = self.tail.next

        self.len += 1

    def get_tail(self):
        return self.tail.transaction
    
    def get(self, n):
        if n >= self.len: raise IndexError
        block = self.head
        for _ in range(n):
            block = block.next
        return block.transaction
    
    def pop(self):
        self.tail = self.tail.prev
        self.len -= 1

    def remove(self, n):
        if n >= self.len: raise IndexError
        block = self.head
        for _ in range(n):
            block = block.next
        block.prev.next = block.next   
        self.len -= 1

    def print(self):
        block = self.head
        for i in range(self.len):
            if i == self.len-1:
                print(block.transaction)
            else:
                print(block.transaction, end=", ")
            block = block.next  
    
def main():
    bc = BlockChain()
    bc.append((1,2,10))
    bc.append((1,2,20))
    bc.append((2,1,10))
    print(bc.len)

    for i in range(bc.len):
        print(i)
        print(bc.get(i))
    print(bc.get_tail())

    print()

    bc.remove(1)
    bc.print()
    bc.pop()
    bc.print()

if __name__ == "__main__":
    main()



