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

## Communication Protocol

1. **Fire and Forget Send**  
   Messages are sent without waiting for a reply.

2. **Listener Thread**  
   Listener Deamon Thread listens for incoming messages.

3. **FIFO Worker**  
   Worker Thread handles requests enqueued by the Listener Thread in FIFO order.

## Blockchain

- **Just Works**  
   Not much to say, it works as specified.
