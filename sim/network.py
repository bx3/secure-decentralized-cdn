from config import *

class Network:
    def __init__(self, num_node):
        self.network = {}
        for i in range(num_node):
            self.network[i] = [] # tagged message queue (delivery_round, msg)
    
    def get_msgs(self, u, curr_r):
        messages = []
        future_msgs = []
        for r, msg in self.network[u]:
            if r <= curr_r:
                messages.append(msg)
            else:
                future_msgs.append((r,msg))
        self.network[u] = future_msgs
        return messages

    # tagged msg, when is delivered
    def deliver_msgs(self, msgs, curr_r):
        for msg in msgs:
            mtype, src, dst, adv = msg
            tagged_msg = (curr_r, msg)
            self.network[dst].append(tagged_msg)
            assert(len(self.network[dst]) < NETWORK_QUEUE_LIM)
        
