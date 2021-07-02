import matplotlib.pyplot as plt
from collections import namedtuple
from itertools import combinations


class PlotNodes:
    def __init__(self, nodes_info_from_json):
        self.nodes_info_from_json = nodes_info_from_json
        self.topic_to_subscribing_nodes = dict()  # key=continent, value=set of node ids
        self.node_id_w_its_coordinate = dict()  # key = node id, value = its coordinate

    # sets topics' subscribing nodes and nodes' coordinates
    def group_nodes(self, node_id_label="id", node_topic_label="continent",
                    node_lat_label="latitude", node_long_label="longitude"):
        Coordinates = namedtuple('Coordinates', ['latitude', 'longitude'])

        for node_info in self.nodes_info_from_json:
            node_coordinate = Coordinates(node_info[node_lat_label], node_info[node_long_label])
            node_id = int(node_info[node_id_label])
            self.node_id_w_its_coordinate[node_id] = node_coordinate

            topics_list = node_info[node_topic_label]
            if isinstance(topics_list, str):  # if only 1 topic that's a str, then put it in a list
                topics_list = [topics_list]

            for topic in topics_list:
                if topic not in self.topic_to_subscribing_nodes:
                    self.topic_to_subscribing_nodes[topic] = {
                        node_id}  # add topic key and initializes a set w/ node's id
                else:
                    self.topic_to_subscribing_nodes[topic].add(node_id)  # add node id to respective topic's set

    def plot_scatter_plot(self):
        plotted_topics_labels = []  # used to get legend of topic combinations' intersections that were plotted
        for combo_len in range(1, len(self.topic_to_subscribing_nodes) + 1):
            # find all combos of topics based on current combo length
            combos_of_topics = combinations(self.topic_to_subscribing_nodes.keys(), combo_len)

            # find each topic combination's intersected/common nodes, then plot them
            for combo in combos_of_topics:

                # gets topics' subscribed nodes (in sets) and add them in list_of_sets
                list_of_sets = []
                topics_label = ""
                for topic in combo:
                    set_of_node_ids = self.topic_to_subscribing_nodes[topic]
                    list_of_sets.append(set_of_node_ids)
                    topics_label = " ".join([topics_label, topic])

                # gets intersected/common topic nodes in current topic combination
                common_node_ids = set.intersection(*list_of_sets)

                # if there are intersected/common nodes, then plot nodes' coordinates
                if len(common_node_ids) > 0:
                    # create a scatter plot of similarities between these set of nodes from combo of topics
                    latitudes = []
                    longitudes = []
                    for node_id in common_node_ids:
                        node_coordinate = self.node_id_w_its_coordinate[node_id]
                        latitudes.append(node_coordinate.latitude)
                        longitudes.append(node_coordinate.longitude)

                    plt.scatter(longitudes, latitudes)
                    plotted_topics_labels.append(topics_label)

        plt.legend(plotted_topics_labels, loc='center left', bbox_to_anchor=(1, 0.5))
        plt.xlabel("longitude")
        plt.ylabel("latitude")
        plt.show()
