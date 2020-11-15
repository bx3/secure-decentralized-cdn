#!/usr/bin/env python
import sys
import os
from experiment import Experiment
from config import *

epoch = 100 # round 
heartbeat = HEARTBEAT

gossipsub = Experiment(heartbeat)
gossipsub.start(epoch)
gossipsub.analyze_snapshot()


