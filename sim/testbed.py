#!/usr/bin/env python
import sys
import os
import datetime
from sim.experiment import Experiment
from sim.config import *
import sim.analyzer as analyzer
import sim.generate_network as gn
from sim.generate_network import *
import random
import math


if __name__ == '__main__':
    np.random.seed(31)
    random.seed(31)

    if len(sys.argv) < 2:
        print("require subcommand: run, gen-network\n")
        print("run json epoch[int]")
        print("gen-network num_pub_per_topic[int] num_lurk[int] num_sybil[int] is_cold_boot[y/n] init_peer_num[int] down_mean[float] down_std[float] up_mean[float] up_std[float] interval_sec[float] num_topic[int] area_length[int]")
        print("gen-network-real-data is_cold_boot[y/n] init_peer_num[int] down_mean[float] down_std[float] up_mean[float] up_std[float] interval_sec[float]  geocluster-data[str]")
        print("gen-spec num_topic[int] num_pub_per_topic[int] num_lurk[int] num_sybil[int]")
        print("demo json")
        print('example: ./testbed.py run topo/one_pub.json 100')
        print('example: ./testbed.py gen-network 4 96 0 n 20 1000000 0 1000000 0 0.1 2 20000> topo/two_topic_2_pub.json')
        print('example: ./testbed.py gen-network-special 4 96 0 n 20 1000000 0 1000000 0 0.1 2 20000 y > topo/two_topic_2_pub.json')
        print('example: ./testbed.py gen-network-real-data input/spec.json n 20 1000000 0 1000000 0 0.1 geocluster.json  > topo/real_data.json')
        print('example: ./testbed.py gen-spec 4 1 4 0 2')
        print('example: ./testbed.py demo topo/one_pub.json')
        sys.exit()

    cmd = sys.argv[1]
    if cmd == "gen-network":
        if len(sys.argv) < 12:
            print("require arguments")
            sys.exit(0)
        n_pub = int(sys.argv[2])
        n_lurk = int(sys.argv[3])
        n_sybil = int(sys.argv[4])
        is_cold_boot = sys.argv[5] == 'y'
        init_peer_num = int(sys.argv[6])
        down_mean = float(sys.argv[7])
        down_std = float(sys.argv[8])
        up_mean = float(sys.argv[9])
        up_std = float(sys.argv[10])
        prob = float(sys.argv[11])
        num_topic = int(sys.argv[12])
        area_length = int(sys.argv[13])
        gn.generate_network(
            is_cold_boot,
            init_peer_num,
            n_pub, n_lurk, n_sybil,
            down_mean, down_std,
            up_mean, up_std,
            prob,
            num_topic,
            area_length
            )
        node_attr_setter = SetStandardNodeAttributes(
                                    is_cold_boot,
                                    init_peer_num,
                                    n_pub, n_lurk, n_sybil,
                                    down_mean, down_std,
                                    up_mean, up_std,
                                    prob,
                                    num_topic,
                                    area_length)
        network_generator = StandardGenerateNetwork(node_attr_setter)
        network_generator.generate_network()

    elif cmd == "run":
        if len(sys.argv) < 3:
            print("require arguments")
            sys.exit(0)
        setup = sys.argv[2]
        epoch = int(sys.argv[3])

        summery = gn.parse_summery(setup)  # gets summery parameters in a list
        heartbeat = HEARTBEAT
        gossipsub = Experiment(setup, heartbeat)

        import time
        t1 = time.time()
        snapshots = gossipsub.start(epoch)
        t2 = time.time()
        print("gossipsub.start time: ", t2 - t1)
        # snapshots = gossipsub.start_with_multi_threading(epoch)
        # print("snapshots", snapshots)

        # analyzer.plot_eclipse_attack(snapshots, [1])
        topics = [gn.get_topic_type(t) for t in summery['TOPICS']]
        analyzer.plot_topics_latency(snapshots, topics)

        # analyzer.plot_topics_latency_cdfs(snapshots, topics, [(0, 1000), (0, 333), (333, 666), (666, 1000)])

        # analyze_network(snapshots)
        # analyze_snapshot(snapshots)
        # dump_graph(snapshots[50])
        # kdump_node(snapshots, 1)
        #  analyzer.dump_node(snapshots, 99)
    elif cmd == "demo":
        if len(sys.argv) < 2:
            print("require arguments")
            sys.exit(0)
        setup = sys.argv[2]
        heartbeat = HEARTBEAT  # in config.py, HEARTBEAT=.2 sec
        gossipsub = Experiment(setup, heartbeat)

        if not os.path.isdir('data'):
            os.mkdir('data')
        x = datetime.datetime.now()
        data_dir = 'data/'+x.strftime("%Y-%m-%d-%H-%M-%S")
        os.makedirs(data_dir)

        total_rounds = 0
        snapshots = []
        while True:
            rounds = input("Enter simulation rounds, such as '20'. Type 'exit' to exit: ")
            if rounds == 'exit':
                break

            attack = input("Enter the attack type, such as 'eclipse' or 'flash'. If not, enter 'n': ")
            if attack == 'n':
                snapshots = snapshots + gossipsub.start(int(rounds), start_round=total_rounds)
            else:
                target = None
                if attack != 'flash':
                    target = int(input("Enter the attack target: "))
                snapshots = snapshots + gossipsub.start(int(rounds), total_rounds, attack, target)
                if attack == 'eclipse':
                    analyzer.plot_eclipse_attack(snapshots, [target])

            total_rounds += int(rounds)

            print('Total simulation rounds: {}'.format(total_rounds))
            analyzer.visualize_network(snapshots[-1].all_nodes, draw_nodes='all')

            sub_nodes = [int(item) for item in input("Enter the nodes you want to zoom in with space as seperator, such as '0 13 67'. If not, just enter '-1': ").split()]
            if sub_nodes == [-1]:
                continue
            analyzer.visualize_network(snapshots[-1].all_nodes, draw_nodes=sub_nodes)
            for sub_node in sub_nodes:
                analyzer.dump_node(snapshots, sub_node, data_dir)
    elif cmd == "term":
        if len(sys.argv) < 2:
            print("require arguments")
            sys.exit(0)
        setup = sys.argv[2]
        heartbeat = HEARTBEAT
        gossipsub = Experiment(setup, heartbeat)

        if not os.path.isdir('data'):
            os.mkdir('data')
        x = datetime.datetime.now()
        data_dir = 'data/'+x.strftime("%Y-%m-%d-%H-%M-%S")
        os.makedirs(data_dir)

        total_rounds = 0
        snapshots = []
        history_targets = set()
        while True:
            rounds = HEARTBEAT/4  # input("Enter simulation rounds, such as '20'. Type 'exit' to exit: ")
            if rounds == 'exit':
                break

            targets_input = input("next targets: ")
            targets = [int(i) for i in targets_input.split()]
            for t in targets:
                history_targets.add(t)

            snapshots = snapshots + gossipsub.start(int(rounds), total_rounds, 'eclipse', targets)
            # analyzer.visualize_network(snapshots[-1].nodes, draw_nodes='all')
            total_rounds += int(rounds)

            # os.system('clear')
            if len(targets) > 0:
                analyzer.print_target_info(snapshots[-1], targets)
                analyzer.print_sybils(snapshots[-1], gossipsub.adversary)
            else:
                analyzer.print_target_info(snapshots[-1], history_targets)
                analyzer.print_sybils(snapshots[-1], gossipsub.adversary)

            # analyzer.print_sybil(91, snapshots[-1].sybils[91]) debug
            # analyzer.print_node(1, snapshots[-1].nodes[1], snapshots[-1].sybils, snapshots[-1].nodes)
    elif cmd == "plot":
        if len(sys.argv) < 7:
            print("require arguments: plot name[string] seed[int] targets[intList]")
            sys.exit(0)
        setup = sys.argv[2]
        filename = sys.argv[3]
        seed = int(sys.argv[4])
        random.seed(seed)
        targets_str = sys.argv[5:]
        targets =[int(i) for i in targets_str]

        heartbeat = HEARTBEAT
        gossipsub = Experiment(setup, heartbeat)

        if not os.path.isdir('data'):
            os.mkdir('data')

        dirname = 'data'
        filepath = dirname + '/' + filename

        total_rounds = 0
        snapshots = []
        eclipsed = set()
        eclipsed_num_hist = []
        eclipsed_ratio_hist = []
        epoch = 1  # int(HEARTBEAT /4 _
        is_first = True
        while len(eclipsed) < len(targets) and total_rounds<2000:
            new_shots = None
            if is_first:
                new_shots = gossipsub.start(epoch, total_rounds, 'eclipse', targets)
                is_first = False
            else:
                new_shots = gossipsub.start(epoch, total_rounds, 'eclipse', [])

            eclipsed_list = analyzer.get_eclipsed_target(new_shots, targets)
            eclipsed_ratio_list = analyzer.get_eclipsed_ratio(new_shots, targets)
            snapshots = snapshots + new_shots
            total_rounds += epoch
            eclipsed_num_hist += eclipsed_list
            eclipsed_ratio_hist += eclipsed_ratio_list
            eclipsed = eclipsed_num_hist[-1]
            analyzer.print_target_info(snapshots[-1], targets)
        if len(eclipsed) < len(targets):
            print("not eclipsed after 2000 rounds")

        # print(gossipsub.adversary.num_freeze_count)

        # analyzer.analyze_freezer(snapshots)

        # analyzer.write_eclipse_list(eclipsed_num_hist, filename, dirname)
        # analyzer.plot_summery(snapshots, eclipsed_num_hist, eclipsed_ratio_hist, filename, dirname, len(targets))
        # analyzer.plot_eclipse_ratio_list(eclipsed_ratio_hist, filename, dirname, len(targets))
        # analyzer.print_target_info(snapshots[-1], targets)
        # analyzer.print_sybils(snapshots[-1])
    elif cmd == "gen-network-real-data":
        if len(sys.argv) < 10:
            print("require arguments")
            sys.exit(0)
        specs_json = sys.argv[2]
        is_cold_boot = sys.argv[3] == 'y'
        init_peer_num = int(sys.argv[4])
        down_mean = float(sys.argv[5])
        down_std = float(sys.argv[6])
        up_mean = float(sys.argv[7])
        up_std = float(sys.argv[8])
        prob = float(sys.argv[9])
        geocluster_file = sys.argv[10]  # essential_bitnode_info.json

        gn.gen_real_data_network(
            is_cold_boot,
            init_peer_num,
            specs_json,
            down_mean, down_std,
            up_mean, up_std,
            prob,
            geocluster_file
            )

    elif cmd == 'gen-specs':
        if len(sys.argv) < 6:
            print("require arguments")
            sys.exit(0)

        n_topic = int(sys.argv[2])
        n_pub_per_topic = int(sys.argv[3])
        n_lurk_per_topic = int(sys.argv[4])
        n_sybil_per_topic = int(sys.argv[5])
        n_non_cluster = int(sys.argv[6])
        gn.gen_specs(n_topic, n_pub_per_topic, n_lurk_per_topic, n_sybil_per_topic, n_non_cluster)

    # patrick's code convert bitnodes.json to our json format
    elif cmd == "convert":
        proportion_pub = float(sys.argv[2])
        proportion_lurk = float(sys.argv[3])
        proportion_sybil = float(sys.argv[4])

        total = proportion_pub + proportion_lurk + proportion_sybil
        if not(proportion_pub >= 0 and proportion_lurk >= 0 and proportion_sybil >= 0):
            print("proportions of pub, lurk, and sybil nodes need to be POSITIVE NUMBERS!!!")
            sys.exit(0)
        elif not(math.isclose(total, 1.0)):
            print("proportions of pub, lurk, and sybil nodes DON'T add up to ONE!!!")
            sys.exit(0)

        is_cold_boot = sys.argv[5] == 'y'
        init_peer_num = int(sys.argv[6])
        down_mean = float(sys.argv[7])
        down_std = float(sys.argv[8])
        up_mean = float(sys.argv[9])
        up_std = float(sys.argv[10])
        interval = float(sys.argv[11])
        # num_topic = int(sys.argv[12])
        # area_length = int(sys.argv[13])

        bit_nodes_setup = sys.argv[12]
        # inputs can be percentage/fraction pub, lurk, and sybil nodes (have to add to 1)

        bit_nodes_info = gn.parse_nodes_with_encoding(bit_nodes_setup)

        bit_node_attr_coll = BitNodeAttributesCollection(bit_nodes_info)
        nodes_id_and_attrs = bit_node_attr_coll.get_bit_nodes_and_attrs()
        total_continents = bit_node_attr_coll.get_total_continents()

        total_nodes = len(nodes_id_and_attrs)

        node_attr_setter = SetBitNodeAttributes(
            is_cold_boot,
            init_peer_num,
            round(proportion_pub * total_nodes), round(proportion_lurk * total_nodes),
            round(proportion_sybil * total_nodes),
            down_mean, down_std,
            up_mean, up_std,
            interval,
            nodes_id_and_attrs,
            total_continents
        )
        network_generator = BitNodesGenerateNetwork(node_attr_setter, nodes_id_and_attrs, total_continents)
        network_generator.generate_network()

    elif cmd == "graph_essential_bitnode":
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

        # Coordinates = namedtuple('Coordinates', ['latitude', 'longitude'])
        nodes_from_json, _, _ = gn.parse_real_data("topo/essential_bitnode_info.json")
        node_plotter = PlotNodes(nodes_from_json)
        node_plotter.group_nodes()
        node_plotter.plot_scatter_plot()

        # sets topics' subscribing nodes and nodes' coordinates
        # topic_to_subscribing_nodes = dict()  # key=continent, value=set of node ids
        # node_id_w_its_coordinate = dict()  # key = node id, value = its coordinate
        # for node_info in nodes_from_json:
        #     topic = node_info["continent"]
        #
        #     node_coordinate = Coordinates(node_info["latitude"], node_info["longitude"])
        #     node_id = int(node_info["id"])
        #     node_id_w_its_coordinate[node_id] = node_coordinate
        #
        #     if topic not in topic_to_subscribing_nodes:
        #         topic_to_subscribing_nodes[topic] = {node_id}  # add topic key and initializes a set w/ node's id
        #     else:
        #         topic_to_subscribing_nodes[topic].add(node_id)  # add node id to respective topic's set

        # plotted_topics_labels = []  # used to get legend of topic combinations' intersections that were plotted
        # for combo_len in range(1, len(topic_to_subscribing_nodes) + 1):
        #     # find all combos of topics based on current combo length
        #     combos_of_topics = combinations(topic_to_subscribing_nodes.keys(), combo_len)
        #
        #     # find each topic combination's intersected/common nodes, then plot them
        #     for combo in combos_of_topics:
        #
        #         # gets topics' subscribed nodes (in sets) and add them in list_of_sets
        #         list_of_sets = []
        #         topics_label = ""
        #         for topic in combo:
        #             set_of_node_ids = topic_to_subscribing_nodes[topic]
        #             list_of_sets.append(set_of_node_ids)
        #             topics_label = " ".join([topics_label, topic])
        #
        #         # gets intersected/common topic nodes in current topic combination
        #         common_node_ids = set.intersection(*list_of_sets)
        #
        #         # if there are intersected/common nodes, then plot nodes' coordinates
        #         if len(common_node_ids) > 0:
        #             # create a scatter plot of similarities between these set of nodes from combo of topics
        #             latitudes = []
        #             longitudes = []
        #             for node_id in common_node_ids:
        #                 node_coordinate = node_id_w_its_coordinate[node_id]
        #                 latitudes.append(node_coordinate.latitude)
        #                 longitudes.append(node_coordinate.longitude)
        #
        #             plt.scatter(longitudes, latitudes)
        #             plotted_topics_labels.append(topics_label)
        #
        # plt.legend(plotted_topics_labels, loc='center left', bbox_to_anchor=(1, 0.5))
        # plt.xlabel("longitude")
        # plt.ylabel("latitude")
        # plt.show()

    else:
        print('Require a valid subcommand', cmd)
