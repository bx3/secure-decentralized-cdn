from enum import Enum
import sys

# network
ATTACK_DEG = 100

# time round
RTT = 100 # millisecond

SPEED_OF_LIGHT = 300000  # Km if point in 2D of 20000 Km, longest delay is 100ms

NODE_PROPCESS = 5 # millisecond

MILLISEC_PER_ROUND = NODE_PROPCESS
HEARTBEAT = 1000/MILLISEC_PER_ROUND  # 0.2 sec <=> 100 round
HEARTBEAT_START = 0  # round
SEC_PER_ROUND = MILLISEC_PER_ROUND/1000.0
ROUND_PER_SEC = 1 / SEC_PER_ROUND

SEC_PER_TRANS = 0.5

# Bandwidth
NETWORK_QUEUE_LIM = 100
MAX_BANDWIDTH = 1000000000000


# message len
CTRL_MSG_LEN = 10  # bytes
TRANS_MSG_LEN = 2000  #  bytes

ATTACK_START = 0

# mesh para
OVERLAY_D = 4#6 # 6 even number 4
OVERLAY_DLO = 2#5 # 5 2
OVERLAY_DHI = 7#12 # 12 7
OVERLAY_DSCORE = 3#6 # 6 3
OVERLAY_DLAZY = 12#12 # 12 12

UPLINK_CONGEST_THRESH = OVERLAY_DHI*5  # num message in the up link capacity

NETWORK_ASSIGN = "EQUAL"
#NETWORK_ASSIGN = "PROP"

BOMB_FACTOR = 10
ADV_SAFE_RATIO = 1.2
ADV_WELL_LOWER_BOUND = 1
ADV_HONEST_REPRESS = -1

ADV_SPECIAL_SENDER = -1
ADV_SPECIAL_SEQNO = -1

TIMEOUT = 4  # round
GOSSIP_FACTOR = 0.25


class NodeType(str, Enum):
    PUB = 'PUB'
    LURK = 'LURK'
    SYBIL = 'SYBIL'
    IND = 'IND' # INDIFFERENT


def get_nodetype(i):
    if i == 0 or i == 'PUB':
        return NodeType.PUB
    elif i == 0 or i == 'LURK':
        return NodeType.LURK
    elif i == 0 or i == 'SYBIL':
        return NodeType.SYBIL
    elif i == 0 or i == 'IND':
        return NodeType.IND
    else:
        print('Error. Unknown Node Type')
        sys.exit(1)


DECAY_INTERVAL = 10  # rounds
RETENSION_PERIOD = 100  # rounds how long peer's score is removed


# Peer Score Parameters
# from Gossipsub V1.1 evaluation report
TOPIC_WEIGHT = 0.25
TIME_IN_MESH_WEIGHT = 0.0027
# TIME_IN_MESH_WEIGHT = 0.0015
TIME_IN_MESH_QUANTUM = "1s"
TIME_IN_MESH_CAP = 3600.0
FIRST_MESSAGE_DELIVERIES_WEIGHT = 0.664
FIRST_MESSAGE_DELIVERIES_DECAY = 0.9916
FIRST_MESSAGE_DELIVERIES_CAP = 1500.0
MESH_MESSAGE_DELIVERIES_WEIGHT = -0.25
# MESH_MESSAGE_DELIVERIES_WEIGHT = -0.05
MESH_MESSAGE_DELIVERIES_DECAY = 0.997
MESH_MESSAGE_DELIVERIES_CAP = 400.0
#  MESH_MESSAGE_DELIVERIES_THRESHOLD = 10.0
MESH_MESSAGE_DELIVERIES_THRESHOLD = 2.5
MESH_MESSAGE_DELIVERIES_ACTIVATION = "1m"
MESH_MESSAGE_DELIVERY_WINDOW = 30  # round <= "5ms"
MESH_FAILURE_PENALTY_WEIGHT = -0.25
MESH_FAILURE_PENALTY_DECAY = 0.997
INVALID_MESSAGE_DELIVERIES_WEIGHT = -99.0
INVALID_MESSAGE_DELIVERIES_DECAY = 0.9994
