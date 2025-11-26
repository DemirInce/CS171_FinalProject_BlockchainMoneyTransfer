# CS171_FinalProject_BlockchainMoneyTransfer

## Commands

1. **moneyTransfer(debit node, credit node, amount)**  
   Transfers amount of money from debit node to credit node.

2. **failProcess**  
   Kills the process to which the input is provided.

3. **fixProcess**  
   Restarts the process after it has failed.

4. **printBlockchain**  
   Prints the copy of blockchain on that node.

5. **printBalance**  
   Prints the balance of all 5 accounts on that node.

6. **debugMessage(client id, message)**  
   Sends a debug message to the specified client which echoes it.  

## Features

**Debug Output Options**  
- None: Only interface output.  
- Basic: Debug outputs with only event types  
- Full: Debug outputs with full events  
Usage: --debug None / Basic / Full, Defaults to None  

**Load From File**  
- False: Starts a fresh peer.  
- True: Loads peer state from it's saved backup.  
Usage: --load False / True, Defaults to False  

**Failure Recovery**  
A peer that has been put into the dead state using the failProcess command will not reply to incoming messages.  
When user enters FixProcess, the peer will querry all others for the required data to bring itself up to date.  
The peer will choose the reply with the longest blockchain depth to adopt.  

**On The Fly Recovery**
If a peer recieves an accept message from an elected proposer with a higher depth than its own, it'll initate recovery from that proposer.  
Once the peer brings itself up to date with the proposer, it'll resume the Paxos process.

**Cryptographic Verification**
All blocks that are appended into a peer's blockchain, and all full blockchains that are adopted during recovery, are cryptographically verified.

## Communication Protocol

1. **Fire and Forget Send**  
   Messages are sent without waiting for a reply.

2. **Listener Thread**  
   Listener Deamon Thread listens for incoming messages.

3. **FIFO Worker**  
   Worker Thread handles requests enqueued by the Listener Thread in FIFO order.
