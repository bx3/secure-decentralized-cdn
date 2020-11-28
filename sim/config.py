from enum import Enum

# network
N_PUB = 90
N_LURK = 10
N_DEGREE = 20
N_SYBIL = 10
ATTACK_DEG = 100

# time round
RTT = 100 # millisecond

PROPAGATION_DELAY = 50 # millisecond
MILLISEC_PER_ROUND = PROPAGATION_DELAY # intrinsic propagation delay
HEARTBEAT = 1e3/MILLISEC_PER_ROUND # 1 sec <=> 20 round
HEARTBEAT_START = 0 # round
SEC_PER_ROUND = MILLISEC_PER_ROUND/1000.0

# Bandwidth
NETWORK_QUEUE_LIM = 100
MAX_BANDWIDTH = 1000000000000


# message len
CTRL_MSG_LEN = 20 # bytes
TRANS_MSG_LEN = 5000 #  bytes

# mesh para
OVERLAY_D = 8
OVERLAY_DLO = 6
OVERLAY_DHI = 12
OVERLAY_DSCORE = 6
OVERLAY_DLAZY = 12

UPLINK_CONGEST_THRESH = OVERLAY_DHI*5  # num message in the up link capacity

NETWORK_ASSIGN = "EQUAL"
#NETWORK_ASSIGN = "PROP"



TIMEOUT = 4 # round
GOSSIP_FACTOR = 0.25

assert(N_PUB + N_LURK > OVERLAY_D)

class NodeType(Enum):
    PUB = 0
    LURK = 1
    SYBIL = 2
    BOOTSTRAP = 3 


DECAY_INTERVAL = 10 # rounds
RETENSION_PERIOD = 100 # rounds how long peer's score is removed


# Peer Score Parameters
# from Gossipsub V1.1 evaluation report
TOPIC_WEIGHT = 0.25
TIME_IN_MESH_WEIGHT = 0.0027
TIME_IN_MESH_QUANTUM = "1s"
TIME_IN_MESH_CAP = 3600.0
FIRST_MESSAGE_DELIVERIES_WEIGHT = 0.664
FIRST_MESSAGE_DELIVERIES_DECAY = 0.9916
FIRST_MESSAGE_DELIVERIES_CAP = 1500.0
MESH_MESSAGE_DELIVERIES_WEIGHT = -0.25
MESH_MESSAGE_DELIVERIES_DECAY = 0.997
MESH_MESSAGE_DELIVERIES_CAP = 400.0
MESH_MESSAGE_DELIVERIES_THRESHOLD = 10.0
MESH_MESSAGE_DELIVERIES_ACTIVATION = "1m"
MESH_MESSAGE_DELIVERY_WINDOW = 30 # round <= "5ms"
MESH_FAILURE_PENALTY_WEIGHT = -0.25
MESH_FAILURE_PENALTY_DECAY = 0.997
INVALID_MESSAGE_DELIVERIES_WEIGHT = -99.0
INVALID_MESSAGE_DELIVERIES_DECAY = 0.9994
