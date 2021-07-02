from collections import defaultdict
import itertools
import sys
import random

def get_subsets(meshes, num_keep):
    valid_peers = sorted(meshes)
    composes = []
    for subset in itertools.combinations(valid_peers, num_keep):
        composes.append(subset)
    return composes

class Adaptor:
    def __init__(self, node_id, topics, heartbeat, desired_num_conn, desired_num_keep, log_file):
        self.id = node_id
        self.topics = list(topics)
        self.heartbeat = heartbeat
        self.meshes = set() # key is node id, values is topics
        self.rel_table = {} # table is 
        self.min_times = {} # key is tid, value is min_time
        self.abs_table = {} # table is 
        self.topic_msgs = defaultdict(list)
        self.num_conn = desired_num_conn
        self.num_keep = desired_num_keep
        self.MISS = 10000
        self.log_file = log_file

    def log(self, comment):
        with open(self.log_file, 'a') as w:
            w.write(comment + '\n')
    def log_comments(self, curr_r, meshes, subset_scores):
        comment_mesh = sorted(list(meshes))
        comment_title = "Epoch {r:<5}. node {node_id:<5}. meshes {meshes} \n".format(r=curr_r, node_id=self.id, meshes=comment_mesh)
        comment_subset = ''
        for subset, scores in subset_scores.items():
            comment = str(subset) + ": "
            for score in scores:
                comment += str(score) + " "
            comment_subset += "\t\t" +comment + '\n'
        self.log(comment_title + comment_subset)

    # udpate at heartbeat time
    def update(self, curr_r, out_meshes, in_meshes, topic_peers):
        # meshes = list(set(self.meshes))

        # meshes = list(set(out_meshes + in_meshes))

        table_mesh = set()
        for tid, node_list in self.rel_table.items():
            for n, t in node_list.items():
                table_mesh.add(n)

        meshes = list(table_mesh)
        
        # the node does not receive any info
        if len(meshes) == 0 :
            return None, None

        num_topic = len(self.topics)

        if len(meshes) >= self.num_keep:
            subsets = get_subsets(meshes, self.num_keep)
            # print('id',self.id, 'r', curr_r, 'm', meshes, subsets)

            # get all scores 
            subset_scores = defaultdict(list) # key is subset, value is a list of scores for all topics
            # if self.id == 1:
                # print('numsebset', len(subsets), subsets)

            for subset in subsets:
                for topic in self.topics:
                    score = self.get_topic_score(topic, subset)
                    subset_scores[subset].append(score)

            # get best subset
            best_score = None
            best_subset_pool = [] 

            self.log_comments(curr_r, meshes, subset_scores)

            for subset, scores in subset_scores.items():
                score = sum(scores)/len(scores)
                if best_score is None:
                    best_score = score
                    best_subset_pool = [subset]
                elif score == best_score:
                    best_subset_pool.append(subset)
                elif score < best_score:
                    best_score = score
                    best_subset_pool = [subset]

            best_subset = random.choice(best_subset_pool)
            # weight scores by deciding which to take more rand
            scores = subset_scores[best_subset]
            
            # print(self.id, "scores", scores)
            topic_score = [(self.topics[i], scores[i]) for i in range(num_topic)]
            sorted_topic_score = sorted(topic_score, key=lambda x: x[1], reverse=True)

            rand_peers = []
            for k in range(self.num_conn - self.num_keep):
                topic_idx = k % num_topic
                topic = sorted_topic_score[topic_idx][0]
                cands = topic_peers[topic].copy()
                cands = list(set(cands).difference(set(list(best_subset) + rand_peers)))
                rand_peer = random.choice(cands)
                rand_peers.append(rand_peer)

            # print(self.id, "at round", curr_r, 'update adaptor desired num conn', self.num_conn)
            return best_subset, rand_peers
        else:
            self.log("Epoch {r:<5}. node {node_id:<5}. meshes {meshes}. Insufficient mesh. Table mesh {table_mesh} \n".format(r=curr_r, node_id=self.id, meshes=meshes, table_mesh=table_mesh))
            rand_peers = []
            for k in range(self.num_conn - len(meshes)):
                topic_idx = k % num_topic
                topic = self.topics[topic_idx] 
                cands = topic_peers[topic].copy()
                cands = list(set(cands).difference(set(meshes + rand_peers)))
                rand_peer = random.choice(cands)
                rand_peers.append(rand_peer)
            return meshes, rand_peers

    # get min for each msg first, then compute 90 percentile delay for the mins
    def get_topic_score(self, topic, subset):
        tids = self.topic_msgs[topic]
        msg_min = []
        for tid in tids:
            node_time = self.rel_table[tid]
            min_list = []
            for n in subset:
                if n in node_time:
                    min_list.append(node_time[n])
                else:
                    min_list.append(self.MISS)
            msg_min.append(min(min_list))

        sorted_lat = sorted(msg_min)
        score = None
        if len(sorted_lat) >= 10:
            score = sorted_lat[int(round(len(sorted_lat)*9.0/10.0)) - 1]
        else:
            score = sorted_lat[int(len(sorted_lat)*9.0/10.0)]
        return score

    def reset(self):
        self.meshes = set() # key is node id, values is topics
        self.rel_table = {} # table is 
        self.min_times = {} # key is tid, value is min_time
        self.abs_table = {} # table is 
        self.topic_msgs = defaultdict(list)
    
    # append time data to  create a row if not a
    def add_time(self, msg, recv_r):
        mtype, _, src, dst, _, _, payload, topic, send_r = msg
        creator, seqno =  payload
        if creator == self.id:
            return 

        self.topic_msgs[topic].append(payload)
        self.meshes.add(src)
        dur = recv_r - send_r # abs time
        if payload not in self.rel_table:
            self.rel_table[payload] = {src: 0}
            self.min_times[payload] = recv_r
            self.abs_table[payload] = dur
        else:
            self.rel_table[payload][src] = recv_r - self.min_times[payload]
            self.abs_table[payload] = dur

