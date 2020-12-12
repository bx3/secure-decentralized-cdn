#!/usr/bin/env python
from config import *
import random
from collections import namedtuple
from messages import *
from scores import PeerScoreCounter
from graph import *
import sys

class Sybil(Node):
    def __init__(self, role, u, interval, peers, heartbeat_period):
        super().__init__(role, u, interval, peers, heartbeat_period)

    def adv_process_msgs(self, r, target, favor_list, attack):
        #  self.schedule_heartbeat(r)
        self.run_scores_background(r)
        self.round_trans_ids.clear()

        while len(self.in_msgs) > 0:
            msg = self.in_msgs.pop(0)
            mtype, _, src, dst, _, _, _ = msg
            if mtype == MessageType.HEARTBEAT:
                continue

            assert self.id == dst
            if mtype == MessageType.GRAFT:
                self.proc_GRAFT(msg, r)
            elif mtype == MessageType.PRUNE:
                self.proc_PRUNE(msg)
            elif mtype == MessageType.LEAVE:
                self.proc_LEAVE(msg) 
            elif mtype == MessageType.IHAVE:
                self.proc_IHAVE(msg) 
            elif mtype == MessageType.IWANT:
                self.proc_IWANT(msg) 
            elif mtype == MessageType.PX:
                self.proc_PX(msg)
            elif mtype == MessageType.HEARTBEAT:
                self.proc_Heartbeat(msg, r)
            elif mtype == MessageType.TRANS:
                self.adv_proc_TRANS(msg, r, target, favor_list, attack)
            else:
                self.scores[src].update_p4()
        
    def adv_proc_TRANS(self, msg, r, target, favor_list, attack):
        _, mid, src, _, _, _, trans_id = msg
        self.scores[src].add_msg_delivery()
        # if not seen msg before
        if mid not in self.msg_ids:
            self.msg_ids.add(mid)
            self.scores[src].update_p2()
            self.round_trans_ids.add(trans_id)
            # push it to other peers in mesh if not encountered
            if trans_id not in self.trans_set:
                # print(self.id, self.mesh)
                for peer in self.mesh:
                    if (attack == 'eclipse'):
                        if peer in favor_list:
                            msg = self.gen_msg(MessageType.TRANS, peer, TRANS_MSG_LEN, trans_id)
                            self.out_msgs.append(msg)
                        elif peer != src and peer < 50:
                            # print("send long msg to peer", peer)
                            msg = self.gen_msg(MessageType.TRANS, peer, TRANS_MSG_LEN*100, trans_id)
                            self.out_msgs.append(msg)
                    else:
                        if peer != src:
                            msg = self.gen_msg(MessageType.TRANS, peer, TRANS_MSG_LEN, trans_id)
                            self.out_msgs.append(msg)
                self.trans_set.add(trans_id)

