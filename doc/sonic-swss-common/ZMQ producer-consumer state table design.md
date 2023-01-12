# ZMQ producer/consumer state table design

# Table of Contents
- [Table of Contents](#table-of-contents)
- [1 Functional Requirements](#1-functional-requirement)
  * [1.1 Supported operations](#11-supported-operations)
  * [1.2 ZMQ producer state table support async operation](#12-zmq-producer-state-table-support-async-operation)
  * [1.3 ZMQ consumer state table support async operation](#13-zmq-consumer-state-table-support-async-operation)(#2-configuration-and-management-requirements)
- [2 Design](#1-design)
  * [2.1 diagram](#21-diagram)
  * [2.1 flow chart](#21-flow-chart)
- [3 References](#references)
  * [ZMQ](#zmq)

# 1 Functional Requirement
## 1.1 Supported operations
 - Should support following operations.
   - Set
   - Delete
   - Batch set
   - Batch delete
## 1.2 ZMQ producer state table support async operation
 - Producer table will return immediately after send operation to ZMQ.
 - Producer table will retry when send not success.
 - Producer table will throw exception after retry failed.
## 1.3 ZMQ consumer state table support async operation
 - Consumer will start a receive thread and receive message from ZMQ.
 - When consumer table receive message from ZMQ, consumer table will:
    - De-serialize received message and append operation to following queue:
      - Received operation queue
      - Update redis database queue
    - Send notification to select to handle received operation.
    - Send notification to DB update thread for write received operation to database.
    - After send notification, continue receive next message from ZMQ.

# 2 Design
 - Diagram:
<img src="./zmq-diagram.png" style="zoom:100%;" />
 - Sequence:
<img src="./sequence.png" style="zoom:100%;" />
 - Call ZmqProducerStateTable API.
 - ZmqProducerStateTable will serialize operation and send to ZMQ.
   - Return when send success.
   - Retry when send failed.
   - Throw exception when retry failed.
 - ZmqConsumerStateTable Side:
   - m_mqPollThread:
   - Receive message from ZMQ.
   - De-serialize received message then:
     - Enqueue to m_receiveQueue
     - Enqueue to m_DbUpdateDataQueue
     - Notify select event
     - Notify m_dbUpdateThread
   - Continue receive next message.
   - m_dbUpdateThread:
   - Update data from m_DbUpdateDataQueue to Redis database.
 - Select will pop operations from m_receivedQueue with ZmqConsumerStateTable::pops().

# 3 References
 - ZMQ: https://zguide.zeromq.org/docs/