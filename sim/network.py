from config import *
import math
from messages import Message
from messages import MessageType

# x and y are coordinates
def get_dist(x, y):
    return math.sqrt(float((x[0]-y[0])**2 + (x[1]-y[1])**2))

class Network:
    def __init__(self, num_node):
        self.queues = {} # key is node id, value is msg queue
        self.id = -1 # special id reserved for network
        self.seqno = 0 # sequence number
        self.link_bandwidth = {}
        for i in range(num_node):
            self.queues[i] = [] # tagged message queue (delivery_round, msg)

    # TODO  
    def setup_link_bandwidth(self, graph):
        for i in graph.nodes:
            for j in graph.nodes:
                if i != j:
                    self.link_bandwidth[(i,j)] = BANDWIDTH
                    self.link_bandwidth[(j,i)] = BANDWIDTH
   
    # TODO optimize
    def get_msgs(self, u, curr_r):
        messages = []
        future_msgs = []
        for tagged_msg in self.queues[u]:
            r, msg = tagged_msg
            if r <= curr_r:
                messages.append(msg)
            else:
                future_msgs.append((r,msg))
        self.queues[u] = future_msgs
        return messages

    # tagged msg, when is delivered
    def deliver_msgs(self, msgs, curr_r):
        for msg in msgs:
            mtype, mid, src, dst, adv, length, payload = msg
            # TODO add delay to TRANS type msg
            self.enqueue_msg(msg, curr_r, dst)

    # TODO transmission and propogation delay
    def compute_delay(self, src, dst):
        pass
        # TODO add message delay
        # assert((src, dst) in self.link_bandwidth)
        # lb = self.link_bandwidth[(src, dst)]
        # target_r = curr_r + math.floor((length/lb)/MILLISEC_PER_ROUND)
        #return  target_r

    # every heartbeat msg contains unique seqno
    def gen_heartbeat_msg(self, dst):
        mid = (self.id, self.seqno)
        msg = Message(MessageType.HEARTBEAT, mid, self.id, dst, False, CTRL_MSG_LEN, None)
        self.seqno += 1
        return msg

    def enqueue_msg(self, msg, r, dst):
        tagged_msg = (r, msg)
        self.queues[dst].append(tagged_msg)
        assert(len(self.queues[dst]) < NETWORK_QUEUE_LIM)

    def deliver_heartbeats(self, curr_r):
        # TODO PUB only
        for u, _ in self.queues.items():
            heartbeat_msg = self.gen_heartbeat_msg(u)
            self.enqueue_msg(heartbeat_msg, curr_r, u)

    def add_node(self, i):
        assert( i not in self.queues)
        self.queues[i] = []
        # for j in graph.nodes:
            # self.link_bandwidth[(i,j)] = BANDWIDTH #TODO choose right bandwidth
            # self.link_bandwidth[(j,i)] = BANDWIDTH

    def remove_node(self, i):
        self.queues.pop(i, None)
        # rm_link_set = set()
        # for j in graph.nodes:
            # if (i, j) in self.link_bandwidth: 
                # rm_link_set.add((i,j))
            # elif (j, i) in self.link_bandwidth:
                # rm_link_set.add((j,i))
        # for l in rm_link_set:
            # del self.link_bandwidth[l]

    def reorder_msgs(self):
        pass

    def delay_msgs(self):
        pass

        
