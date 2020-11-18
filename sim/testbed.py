#!/usr/bin/env python
import sys
import os
from experiment import Experiment
from config import *

epoch = 200 # round 
heartbeat = HEARTBEAT
prob = 0.5

gossipsub = Experiment(heartbeat, prob)
gossipsub.start(epoch)
gossipsub.analyze_snapshot()


