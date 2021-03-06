#!/usr/bin/env python
import sys
import os
import datetime
from experiment import Experiment
from config import *
import analyzer
import generate_network as gn
import random
random.seed(31)

if len(sys.argv) < 2:
    print("require subcommand: run, gen-network\n")
    print("run json epoch[int] outdir[str] method[individual/coll-subset]")
    print("gen-network num_pub_per_topic[int] num_lurk[int] num_sybil[int] is_cold_boot[y/n] init_peer_num[int] down_mean[float] down_std[float] up_mean[float] up_std[float] interval_sec[float] num_topic[int] area_length[int]") 
    print("gen-network-real-data is_cold_boot[y/n] init_peer_num[int] down_mean[float] down_std[float] up_mean[float] up_std[float] interval_sec[float]  geocluster-data[str]")
    print("gen-spec num_topic[int] num_pub_per_topic[int] num_lurk[int] num_sybil[int]")
    print("demo json")
    print('exmaple: ./testbed.py run topo/one_pub.json 100 output coll-subset')
    print('exmaple: ./testbed.py gen-network 4 96 0 n 20 1000000 0 1000000 0 0.1 2 20000> topo/two_topic_2_pub.json')
    print('exmaple: ./testbed.py gen-network-special 4 96 0 n 20 1000000 0 1000000 0 0.1 2 20000 y > topo/two_topic_2_pub.json')
    print('exmaple: ./testbed.py gen-network-real-data specs/spec.json n 20 1000000 0 1000000 0 0.1 input_data/bitcoin.json  > topo/real_data.json')
    print('exmaple: ./testbed.py gen-specs 4 1 4 0 true 2')
    print('exmaple: ./testbed.py demo topo/one_pub.json')
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
    init_peer_num =  int(sys.argv[6])
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
elif cmd == "run":
    if len(sys.argv) < 6:
        print("require arguments")
        sys.exit(0)
    setup = sys.argv[2]
    epoch = int(sys.argv[3])
    dirname = sys.argv[4]
    update_method = sys.argv[5]
    print('epoch', epoch)

    if not os.path.exists(dirname):
        os.makedirs(dirname)

    summery = gn.parse_summery(setup)
    heartbeat = HEARTBEAT
    gossipsub = Experiment(setup, heartbeat, update_method, dirname)
    num_snapshots = gossipsub.start(epoch)
    print(num_snapshots, 'snapshots saved')

elif cmd == "demo":
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
        rounds = HEARTBEAT/4 # input("Enter simulation rounds, such as '20'. Type 'exit' to exit: ")
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
        if len(targets) >0:
            analyzer.print_target_info(snapshots[-1], targets)
            analyzer.print_sybils(snapshots[-1], gossipsub.adversary)
        else:
            analyzer.print_target_info(snapshots[-1], history_targets)
            analyzer.print_sybils(snapshots[-1], gossipsub.adversary)

        # analyzer.print_sybil(91, snapshots[-1].sybils[91]) debug
        # analyzer.print_node(1, snapshots[-1].nodes[1], snapshots[-1].sybils, snapshots[-1].nodes) 
elif cmd == "plot":
    if len(sys.argv) < 4:
        print('Require args')
        sys.exit(1)
    setup = sys.argv[2]
    epoch = int(sys.argv[3])
    dirname = sys.argv[4]

    summery = gn.parse_summery(setup)
    topics = [gn.get_topic_type(t) for t in summery['TOPICS']]
    snapshots = analyzer.load_snapshots(os.path.join(dirname, 'snapshots'))
    analyzer.plot_topics_latency(snapshots, topics, dirname)
   
    plot_indices = [int(i*epoch/3) for i in range(4)]
    plot_slices = [(0, epoch)]
    for i in range(1,4):
        plot_slices.append((plot_indices[i-1], plot_indices[i]))
    analyzer.plot_topics_latency_cdfs(snapshots, topics, dirname, plot_slices)
    
elif cmd == "gen-network-special":
    if len(sys.argv) < 14:
        print("require arguments")
        sys.exit(0)
    n_pub = int(sys.argv[2])
    n_lurk = int(sys.argv[3])
    n_sybil = int(sys.argv[4])
    is_cold_boot = sys.argv[5] == 'y'
    init_peer_num =  int(sys.argv[6])
    down_mean = float(sys.argv[7])
    down_std = float(sys.argv[8])
    up_mean = float(sys.argv[9])
    up_std = float(sys.argv[10])
    prob = float(sys.argv[11])
    num_topic = int(sys.argv[12])
    area_length = int(sys.argv[13])
    grid_point = sys.argv[14] == 'y'

    gn.gen_two_topic_network(
        is_cold_boot,
        init_peer_num,
        n_pub, n_lurk, n_sybil,
        down_mean, down_std,
        up_mean, up_std,
        prob,
        num_topic,
        area_length,
        grid_point
        )
elif cmd== "gen-network-real-data":
    if len(sys.argv) < 10:
        print("require arguments")
        sys.exit(0)
    specs_json = sys.argv[2]
    is_cold_boot = sys.argv[3] == 'y'
    init_peer_num =  int(sys.argv[4])
    down_mean = float(sys.argv[5])
    down_std = float(sys.argv[6])
    up_mean = float(sys.argv[7])
    up_std = float(sys.argv[8])
    prob = float(sys.argv[9])
    geocluster_file = sys.argv[10]

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
    if len(sys.argv) < 7:
        print("require arguments")
        sys.exit(0)

    n_topic = int(sys.argv[2])
    n_pub_per_topic = int(sys.argv[3])
    n_lurk_per_topic = int(sys.argv[4])
    n_sybil_per_topic = int(sys.argv[5])
    is_clusterized = sys.argv[6] == 'true'
    n_non_cluster = int(sys.argv[7])
    gn.gen_specs(n_topic, n_pub_per_topic, n_lurk_per_topic, n_sybil_per_topic, is_clusterized, n_non_cluster)

elif cmd == 'old-plot':
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
    epoch = 1 # int(HEARTBEAT /4 _
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
else:
    print('Require a valid subcommand', cmd)



