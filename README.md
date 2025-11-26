# CS171 Final Project: Distributed Blockchain Money Transfer

## Overview
Fault-tolerant decentralized system that implements Paxos to create a peer-to-peer money exchange backed by blockchain encryption.

## How to run
- Start five peers with ids=1, 2, 3, 4, 5  
- Example shown below: Full debug (prints debugging), not loading previous state
```
# Terminal 1 
python3 client.py --id 1 --load False --debug full

# Terminal 2
python3 client.py --id 2 --load False --debug full

...

# Terminal 5
python3 client.py --id 2 --load False --debug full
```
### Sample workflow
```
>> printBalance
{1: 100, 2: 100, 3: 100, 4: 100, 5: 100}

>> moneyTransfer(1,2,10)
Done.

>> printBalance
{1: 90, 2: 110, 3: 100, 4: 100, 5: 100}

>> printBlockchain
Block(Tx=(1, 2, 10), Nonce=My4oLp2Q, Hash=3bd955b1be731db12c3f27782314157878c05ae1c1198c2d959df66499b53ee2, PrevHash=None)

```

## Commands

1. `moneyTransfer(debit node, credit node, amount)`
     
   Transfers amount of money from debit node to credit node.

3. `failProcess`
   
   Kills the process to which the input is provided.

4. `fixProcess`
   
   Restarts the process after it has failed.

5. `printBlockchain`
     
   Prints the copy of blockchain on that node.

7. `printBalance`
    
   Prints the balance of all 5 accounts on that node.

9. `debugMessage(client id, message)`
      
   Sends a debug message to the specified client which echoes it.  

## Features

### **Debug Output Options**  
- None: Only interface output  
- Basic: Debug outputs with only event types  
- Full: Debug outputs with full events  
Usage: `--debug None / Basic / Full, (default=None)`  

### **Load From File**  
- False: Starts a fresh peer.  
- True: Loads peer state from it's saved backup.  
Usage: `--load False / True, (default=False)`

### **Failure Recovery**  

A peer that has been put into a dead state using the `failProcess` command will not reply to incoming messages.  
When a user enters `FixProcess` on the terminal, the peer will query all other peers for the required data to bring itself up to date.  
The peer will adopt the reply with the longest blockchain depth.  

### **On The Fly Recovery**  

If a peer receives an 'Accept' message from an elected proposer with a higher depth than its own, it'll initate recovery from that proposer.  
Once the peer brings itself up to date with the proposer, it'll resume the Paxos process.  

### **Cryptographic Verification**  

All blocks that are appended onto a peer's blockchain, and all full blockchains that are adopted during recovery, are cryptographically verified.  

## Communication Protocol

1. **Fire and Forget Send**  
   Messages are sent without waiting for a reply.

2. **Listener Thread**  
   Listener Deamon Thread listens for incoming messages.

3. **FIFO Worker**  
   Worker Thread handles requests enqueued by the Listener Thread in FIFO order.
