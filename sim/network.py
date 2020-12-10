from config import *
from collections import namedtuple
import math
import sys
from messages import Message
from messages import MessageType
from generate_network import parse_nodes 
from generate_network import NetBandwidth

NetworkState = namedtuple('NetworkState', ['links', 'uplinks', 'downlinks'])
LinkSnapshot = namedtuple('LinkSnapshot', ['num_msg', 'num_trans', 'finished_trans', 'up_remains', 'down_remains'])

# direcdtion sensitive
# assume network has infinite buffer volume
class LinkState:
    def __init__(self, up_bd, down_bd, msg):
        self.up_limit = up_bd
        self.down_limit = down_bd
        self.up_remain = msg.length 
        self.down_remain = 0
        self.msgs = [msg]
        self.byte_transferred = msg.length # link statistics
        self.curr_msg_byte_transferred = 0 # count if curr msg finishes
        self.finished_trans = 0
        self.frozen = 0 # count down to be active

    def get_link_snapshot(self):
        return LinkSnapshot(
            self.get_num_msg(),
            self.get_num_trans(),
            self.finished_trans,
            self.up_remain,
            self.down_remain
            )

    def set_froze_count(self, count):
        self.frozen = count


    def get_num_msg(self):
        return len(self.msgs)

    def get_num_trans(self):
        n = 0
        for msg in self.msgs:
            if msg.mType == MessageType.TRANS:
                n += 1
        return n

    def feed_msg(self, msg):
        self.up_remain += msg.length
        self.msgs.append(msg)

    def is_complete(self):
        if self.up_remain <= 0 and self.down_remain <= 0 and len(self.msgs) == 0:
            return True
        else:
            return False

    # use separate functions(up, down), implicitly assume there is no inter network routing delay
    # between up and down
    def update_up(self, up_bd):
        if self.frozen > 0:
            self.frozen -= 1
            return 0

        uploaded_byte = up_bd * SEC_PER_ROUND
        if self.up_remain >= uploaded_byte:
            self.up_remain -= uploaded_byte
            self.down_remain += uploaded_byte
        else:
            self.down_remain += self.up_remain
            uploaded_byte = self.up_remain
            self.up_remain = 0
        return uploaded_byte

    def update_down(self, down_bd):
        completed = []
        downloaded_byte = down_bd * SEC_PER_ROUND
        if self.down_remain <= downloaded_byte:
            downloaded_byte = self.down_remain 

        self.down_remain -= downloaded_byte

        self.byte_transferred += downloaded_byte
        self.curr_msg_byte_transferred += downloaded_byte
        # pop all completed msgs, self.curr_msg_byte_transferred may not be 0 at the end, i.e. some bandwidth is not used 
        while (len(self.msgs) > 0 and 
                round(self.curr_msg_byte_transferred, 5) >= self.msgs[0].length):
            self.curr_msg_byte_transferred -= self.msgs[0].length 
            msg = self.msgs.pop(0)
            if msg.mType == MessageType.TRANS:
                self.finished_trans += 1
            completed.append(msg)

        return completed

    # NOT USED, SEPARATED INTO up and down, old comment up_bd, down_bd are used in current round
    def update(self, up_bd, down_bd):
        if self.frozen > 0:
            self.frozen -= 1
            return [] 

        completed = []
        uploaded_byte = up_bd * SEC_PER_ROUND
        downloaded_byte = down_bd * SEC_PER_ROUND

        self.up_remain -= uploaded_byte
        self.down_remain += uploaded_byte
        self.down_remain -= downloaded_byte

        self.byte_transferred += downloaded_byte
        self.curr_msg_byte_transferred += downloaded_byte
        # pop all completed msgs, self.curr_msg_byte_transferred may not be 0 at the end, i.e. some bandwidth is not used 
        while len(self.msgs) > 0 and self.curr_msg_byte_transferred > self.msgs[0].length:
            self.curr_msg_byte_transferred -= self.msgs[0].length 
            msg = self.msgs.pop(0)
            if msg.mType == MessageType.TRANS:
                self.finished_trans += 1
            completed.append(msg)
        return completed

class Controller:
    def __init__(self):
        self.links = {} # key is node pair, value is state
        self.msg_uplink = {} # key is node id, value is a set of dst that uses this up link
        self.msg_downlink = {} # same as above

    def feed_link(self, msg, up_bd_lim, down_bd_lim):
        mtype, mid, src, dst, adv, length, payload = msg
        pair = (src, dst)
        if pair not in self.links:
            self.links[pair] = LinkState(up_bd_lim, down_bd_lim, msg)
            self.mark_msg_to_link(src, dst)
        else:
            link = self.links[pair]
            link.feed_msg(msg)

    # assign bandwidth for up down , with equal bandwidth per node
    def assign_bandwidth_equal(self, link, pair):
        src, dst = pair
        num_up_msg = len(self.msg_uplink[src])
        up_bd_per_node = float(link.up_limit) / num_up_msg
        num_down_msg = len(self.msg_downlink[dst])
        down_bd_per_node = float(link.down_limit) / num_up_msg
        return up_bd_per_node, down_bd_per_node

    # get bandwidth for this link depending on 
    def assign_up_bandwidth_prop(self, my_link, my_pair, uplink_share):
        my_src, my_dst = my_pair
        local_uplink_share = {}
        up_total = 0
        #print(my_link.up_remain, my_link.down_remain)
        for dst in self.msg_uplink[my_src]:
            pair = (my_src, dst)
            link = self.links[pair]
            up_total += link.up_remain
            local_uplink_share[(my_src, dst)] = link.up_remain

        # in the case when upload is down, i.e. up_remain = 0, but down_remain > 0
        for pair, up_bd in local_uplink_share.items():
            up_ratio = 1.0/len(self.msg_uplink[my_src])
            if up_total != 0:
                up_ratio = up_bd/up_total
            if pair not in uplink_share:
                uplink_share[pair] = up_ratio
            else:
                assert(uplink_share[pair] == up_ratio)

        
        my_up_bd = uplink_share[my_pair] * my_link.up_limit 
        return my_up_bd

    def assign_down_bandwidth_prop(self, my_link, my_pair, downlink_share):
        my_src, my_dst = my_pair
        local_downlink_share = {}
        down_total = 0
        for src in self.msg_downlink[my_dst]:
            pair = (src, my_dst)
            link = self.links[pair]
            down_total += link.down_remain
            local_downlink_share[(src, my_dst)] = link.down_remain

        for pair, down_bd in local_downlink_share.items():
            down_ratio = down_bd/down_total
            if pair not in downlink_share:
                downlink_share[pair] = down_ratio
            else:
                assert(downlink_share[pair] == down_ratio)

        my_down_bd = downlink_share[my_pair] * my_link.down_limit 
        return my_down_bd

    


    # drain links in one round
    def drain_links(self):
        completed = {} # msg
        # network deliver message
        if NETWORK_ASSIGN == "EQUAL":
            for pair, link in self.links.items():
                src, dst = pair
                # Equal share
                up_bd, down_bd = self.assign_bandwidth_equal(link, pair)
                msgs = link.update(up_bd, down_bd)
                if dst in completed:
                    completed[dst] += msgs
                else:
                    completed[dst] = msgs

        if NETWORK_ASSIGN == "PROP": 
            uplink_share = {}
            downlink_share = {}
            # assign bd for every up link 
            for pair, link in self.links.items():
                up_bd = self.assign_up_bandwidth_prop(link, pair, uplink_share)


            for pair, link in self.links.items():
                up_bd = uplink_share[pair] * link.up_limit
                link.update_up(up_bd)

            for pair, link in self.links.items():
                down_bd = self.assign_down_bandwidth_prop(link, pair, downlink_share)
                assert(down_bd > 0)


            for pair, link in self.links.items():
                src, dst = pair
                down_bd = downlink_share[pair] * link.down_limit
                assert(down_bd > 0)
                msgs = link.update_down(down_bd)
                
                if dst in completed:
                    completed[dst] += msgs
                else:
                    completed[dst] = msgs
        return completed

    # after link finishes 
    def clean_links(self):
        link_to_remove = set()
        for pair, link in self.links.items():
            if link.is_complete():
                link_to_remove.add(pair)

        for pair in link_to_remove:
            src, dst = pair
            self.remove_link(src, dst)

    # for calculating shared bandwidth
    def mark_msg_to_link(self, src, dst):
        if src not in self.msg_uplink:
            self.msg_uplink[src] = set()
            self.msg_uplink[src].add(dst)
        else:
            self.msg_uplink[src].add(dst)

        if dst not in self.msg_downlink:
            self.msg_downlink[dst] = set()
            self.msg_downlink[dst].add(src)
        else:
            self.msg_downlink[dst].add(src)

    def remove_link(self, src, dst):
        if src not in self.msg_uplink:
            print('Error. uplink not found')
            sys.exit(0)
        else:
            self.msg_uplink[src].remove(dst)

        if dst not in self.msg_downlink:
            print('Error. uplink not found')
            sys.exit(0)
        else:
            self.msg_downlink[dst].remove(src)

        pair = (src, dst)
        self.links.pop(pair, None)


class Network:
    def __init__(self, setup_json):
        # self.queues = {} # key is node id, value is queues of tagged msg
        self.id = -1 # special id reserved for network
        self.seqno = 0 # sequence number for msgs derived from network i.e. heartbeat
        self.controller = Controller()
        self.netband = {}
        self.load_network(setup_json)

    # used by adversary to delay message
    def break_link(self, pair, frozen_round):
        if pair in self.controller.links:
            link = self.controller.links[arrow]
            link.set_froze_count(frozen_round)

    def load_network(self, setup_json):
        nodes = parse_nodes(setup_json)
        for u in nodes:
            u_id = u['id']
            if u_id not in self.netband:
                # self.queues[u_id] = [] 
                self.netband[u_id] = NetBandwidth(u["upB"], u["downB"])
            else:
                print('Error. Duplicate id in setup json')
                sys.exit(0)

    def is_uplink_congested(self, u):
        if u not in self.controller.msg_uplink:
            return False

        num_msg = len(self.controller.msg_uplink[u])
        if num_msg > UPLINK_CONGEST_THRESH:
            # print('Warning. node', u, 'Hit UPLINK_CONGEST_THRESH with num msg', num_msg)
            return True
        return False
   
    # def get_msgs(self, u, curr_r):
        # links = self.controller.get_dst_links(u)
        # for link in links:
            # if link.is_complete:
                # self.controller.remove_link_num_msg(link.src, link.dst)
        # messages = []
        # future_msgs = []
        # for tagged_msg in self.queues[u]:
            # r, msg = tagged_msg
            # if r <= curr_r:
                # messages.append(msg)
            # else:
                # future_msgs.append((r,msg))
        # self.queues[u] = future_msgs
        # return messages

    # tagged msg, when is delivered
    def push_msgs(self, msgs, curr_r):
        for msg in msgs:
            _, _, src, dst, _, length, _ = msg
            self.controller.feed_link(msg, self.netband[src].up_bd, self.netband[dst].down_bd)
            # r = self.get_delay_to_msg(src, dst, length, curr_r)
            # self.enqueue_msg(msg, r, dst)

    # return dict with key be dst, value is delivered msgs
    def update(self):
        msgs = self.controller.drain_links()
        self.controller.clean_links()
        return msgs

    # TODO transmission and propogation delay
    # def get_delay_to_msg(self, src, dst, length, curr_r):
        # up_bd = self.netband[src].up_bd
        # down_bd = self.netband[dst].down_bd
        # trans_bd = min(up_bd, down_bd)
        # trans_delay = float(length) / trans_bd * 1000 / MILLISEC_PER_ROUND # in round
        # # print("delayed msg", math.floor(trans_delay))
        # arrive_r = curr_r + math.floor(trans_delay)
        # return arrive_r

    # every heartbeat msg contains unique seqno
    def gen_heartbeat_msg(self, dst):
        mid = (self.id, self.seqno)
        msg = Message(MessageType.HEARTBEAT, mid, self.id, dst, False, CTRL_MSG_LEN, None)
        self.seqno += 1
        return msg

    def take_snapshot(self):
        links_shot = {}
        for arr, link in self.controller.links.items():
            links_shot[arr] = link.get_link_snapshot()

        state = NetworkState(
            links_shot,
            self.controller.msg_uplink.copy(),
            self.controller.msg_downlink.copy()
            )
        return state

    # def enqueue_msg(self, msg, r, dst):
        # tagged_msg = (r, msg)
        # self.queues[dst].append(tagged_msg)
        # assert(len(self.queues[dst]) < NETWORK_QUEUE_LIM)

    # def deliver_heartbeats(self, curr_r):
        # # TODO PUB only
        # for u, _ in self.queues.items():
            # heartbeat_msg = self.gen_heartbeat_msg(u)
            # self.enqueue_msg(heartbeat_msg, curr_r, u)

    # def add_node(self, i, up_bd, down_bd):
        # assert( i not in self.queues)
        # self.queues[i] = []

    # def remove_node(self, i):
        # self.queues.pop(i, None)
        # self.netband.pop(i, None)

    def reorder_msgs(self):
        pass

    def delay_msgs(self):
        pass

    

# x and y are coordinates
def get_dist(x, y):
    return math.sqrt(float((x[0]-y[0])**2 + (x[1]-y[1])**2))
