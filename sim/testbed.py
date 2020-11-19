#!/usr/bin/env python
import sys
import os
from experiment import Experiment
from config import *
from analyzer import analyze_snapshot

epoch = 200 # round 
heartbeat = HEARTBEAT
prob = 0.5

gossipsub = Experiment(heartbeat, prob)
snapshots = gossipsub.start(epoch)
analyze_snapshot(snapshots)


