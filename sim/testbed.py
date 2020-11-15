#!/usr/bin/env python
import sys
import os
from experiment import Experiment

epoch = 20 # round 
heartbeat = 100000

gossipsub = Experiment(heartbeat)
gossipsub.start(epoch)
gossipsub.analyze_snapshot()


