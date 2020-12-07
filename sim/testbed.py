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
    print("run json epoch[int]")
    print("gen-network num_pub[int] num_lurk[int] num_sybil[int] is_cold_boot[y/n] init_peer_num[int] down_mean[float] down_std[float] up_mean[float] up_std[float] interval_sec[float]") 
    print("demo json")
    print('exmaple: ./testbed.py run topo/one_pub.json 100')
    print('exmaple: ./testbed.py gen-network 10 90 0 n 20 1000000 0 1000000 0 0.5 > ten_pub.json')
    print('exmaple: ./testbed.py demo topo/one_pub.json')
    sys.exit()

cmd = sys.argv[1]
if cmd == "gen-network":
    if len(sys.argv) < 10:
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
    gn.generate_network(
        is_cold_boot,
        init_peer_num,
        n_pub, n_lurk, n_sybil,
        down_mean, down_std,
        up_mean, up_std,
        prob
        )
elif cmd == "run":
    if len(sys.argv) < 3:
        print("require arguments")
        sys.exit(0)
    setup = sys.argv[2]
    epoch = int(sys.argv[3])
    heartbeat = HEARTBEAT
    gossipsub = Experiment(setup, heartbeat)
    snapshots = gossipsub.start(epoch)
    analyzer.plot_eclipse_attack(snapshots, [1])
    print("start analyze")
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
        analyzer.visualize_network(snapshots[-1].nodes, draw_nodes='all')

        sub_nodes = [int(item) for item in input("Enter the nodes you want to zoom out with space as seperator, such as '0 13 67'. If not, just enter '-1': ").split()] 
        if sub_nodes == [-1]:
            continue
        analyzer.visualize_network(snapshots[-1].nodes, draw_nodes=sub_nodes)
        for sub_node in sub_nodes:
            analyzer.dump_node(snapshots, sub_node, data_dir)

else:
    print('Require a valid subcommand', cmd)



