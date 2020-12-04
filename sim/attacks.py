from config import NodeType
class Adversary:
    def __init__(self):
        self.state = None
        self.target = -1

    # attack codes, u is node, return messages
    def censorship_attack(selfgsraph, u):
        pass

    def find_eclipse_publisher_target(self, r, snapshots):
        node_avg_score = {}
        last_shot = snapshots[-1]
        nodes_shot = last_shot.nodes
        for u in range(len(nodes_shot)):
            node = nodes_shot[u]
            node_view_total = 0
            if node.role == NodeType.PUB:   
                for peer in node.mesh:
                    node_view_total += node.scores[peer]
                avg = float(node_view_total)/len(node.mesh)
                node_avg_score[u] = avg
        sorted_score = {k: v for k, v in sorted(node_avg_score.items(), key=lambda item: item[1])}
        sorted_list = list(sorted_score)
        # print(sorted_score)
        self.target = sorted_list[0]
        # print(self.target)

    def has_target(self):
        return self.target > -1

    def find_in_conns(self, r, snapshots, target):
        last_shot = snapshots[-1]
        nodes = last_shot.nodes
        node = nodes[target]
        outs = node.out_conn
        mesh = node.mesh
        return  set(mesh).difference(set(outs))

    def find_out_conns(self, r, snapshots, target):
        last_shot = snapshots[-1]
        nodes = last_shot.nodes
        node = nodes[target]
        return node.out_conn

    def find_weaker_out(self, r, snapshots, peer, target):
        pass

    def eclipse_target(self, r, snapshots):
        pass

