from graph import *
from network import Network
from messages import *
from config import *
from graph import State

class Snapshot:
    def __init__(self):
        self.round = 0
        self.nodes = {} # key:node id value: node state
        self.network = {} # message queue in for each node



class Experiment:
    def __init__(self, heartbeat):
        self.snapshots = []
        self.network = Network(N_PUB+N_LURK+N_SYBIL)
        self.graph = Graph(N_PUB, N_LURK, N_SYBIL)
        # init nodes and bandwidth
        self.graph.preset_rand_honest_peers()
        self.network.setup_link_bandwidth(self.graph)
        self.heartbeat_period = heartbeat

    # # # # # # # # 
    #  main loop  #
    # # # # # # # # 
    def start(self, epoch):
        for r in range(epoch):
            # periodically gen hearbeat
            
            # network store messages from honest nodes
            self.push_honest_msgs(r)
            # start attack
            self.act_adversarirs(r)
            # all node retrieve msgs 
            self.all_nodes_handle_msgs(r)    
            # take snapshot
            self.take_snapshot(r)

    # three heartbeat
    def schedule_heartbeat(r):
        if r!=0 and r%self.heartbeat_period==0:
            self.network.gen_heartbeat()
        elif r!=1 and r%self.heartbeat_period==1:
            self.network.gen_heartbeat()
        elif r!=2 and r%self.heartbeat_period==2:
            self.network.gen_heartbeat()

    # honest nodes push msg to network
    def push_honest_msgs(self, curr_r):
        # TODO honest nodes
        for _, node in self.graph.nodes.items():
            msgs = node.send_msgs() 
            self.network.deliver_msgs(msgs, curr_r)

    def act_adversarirs(self, r):
        # examine network in curr round r
        pass
        # chosen attack strategy to generate new messgae and arrange network 
        adv_msgs = []
        self.network.deliver_msgs(adv_msgs, r)
        # maybe rearrange message order
        pass

    def all_nodes_handle_msgs(self, curr_r):
        # node process messages
        for u, node in self.graph.nodes.items():
            msgs = self.network.get_msgs(u, curr_r)
            node.process_msgs(msgs)
        # node take new action
        # gossipsub.node_action(graph)

    def take_snapshot(self, r):
        snapshot = Snapshot()
        snapshot.round = r
        # get all node states
        for u, node in self.graph.nodes.items():
            snapshot.nodes[u] = node.get_states()
        # get network 
        snapshot.network = self.network.queues.copy()
        self.snapshots.append(snapshot)

    # TODO we will need to save snapshot and do analysis separately when experiment becomes large
    def analyze_snapshot(self):
        pass
    # Get the degree of each node
    # degree = []
    # for u in graph.nodes:
        # degree.append(len(graph.nodes[u].conn))
    # degrees.append(degree)
    # Get the number of component
    # components.append(count_components(graph))


# def count_components(graph):
    # sets = {}
    # for u in graph.nodes:
      # sets[u] = DisjointSet()
    # for u in graph.nodes:
        # for vtx in graph.nodes[u].conn:
            # sets[u].union(sets[vtx])
    # return len(set(x.find() for x in sets.values()))

# class DisjointSet(object):
    # def __init__(self):
        # self.parent = None

    # def find(self):
        # if self.parent is None: return self
        # return self.parent.find()

    # def union(self, other):
        # them = other.find()
        # us = self.find()
        # if them != us:
            # us.parent = them
# analyze stat ... generate figure
# print the final states
# for u in graph.nodes:
#     print(graph.nodes[u].conn)

# degree changes
# degrees_mean = []
# degrees_max = []
# degrees_min = []
# for i in range(epoch):
    # degree = degrees[i]
    # degrees_mean.append(sum(degree) / len(degree))
    # degrees_max.append(max(degree))
    # degrees_min.append(min(degree))

# # plot
# fig, axs = plt.subplots(2)

# axs[0].plot(degrees_mean, 'b', degrees_max, 'r', degrees_min, 'g')
# axs[0].set(ylabel='node degree')
# max_patch = mpatches.Patch(color='red', label='max')
# min_patch = mpatches.Patch(color='green', label='min')
# mean_patch = mpatches.Patch(color='blue', label='mean')
# axs[0].legend(handles=[max_patch,min_patch,mean_patch])

# # number of connectted component
# x_points = [ i for i in range(epoch)]
# axs[1].set_yscale('log')
# axs[1].scatter(x_points, components)
# axs[1].set(ylabel='# components', xlabel='round')

# plt.show()

