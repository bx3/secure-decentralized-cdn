#!/usr/bin/env python
import sys
import os
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from experiment import Experiment


epoch = 20 # round 

gossipsub = Experiment()
gossipsub.start(epoch)
gossipsub.analyze_snapshot()


