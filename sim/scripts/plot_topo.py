#!/usr/bin/env python
import matplotlib.pyplot as plt
import json
import sys

if len(sys.argv) < 1:
    print('need json topology file, show pub for continent cluster')
    sys.exit(1)

infile = sys.argv[1]

nodes = []
with open(infile) as f:
    data = json.load(f)
    nodes = data['nodes']

x_list = []
y_list = []
pubs_x = []
pubs_y = []
for u in nodes:
    u_id = int(u["id"])
    x = float(u["x"])
    y = float(u["y"])
    x_list.append(x)
    y_list.append(y)
    topics = u["topics"]
    roles = u['roles']
    for t, r in roles.items():
        if r == 'PUB':
            pubs_x.append(x)
            pubs_y.append(y)

plt.scatter(y_list, x_list)
plt.scatter(pubs_y, pubs_x, color='red')
plt.show()
