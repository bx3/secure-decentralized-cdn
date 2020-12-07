from config import *
class PeerScoreCounter:
    def __init__(self):
        self.r = 0 # the lastest update round
        self.W1 = TIME_IN_MESH_WEIGHT
        self.P1 = 0 # time in mesh

        self.W2 = FIRST_MESSAGE_DELIVERIES_WEIGHT
        self.P2 = 0 # num first message from 

        self.msg_delivery = 0
        self.W3a = MESH_MESSAGE_DELIVERIES_WEIGHT
        self.P3a = 0 # num message failure rate, need to a window

        self.W3b = MESH_FAILURE_PENALTY_WEIGHT
        self.P3b = 0 # num mesh message deliver failure
        self.W4 = INVALID_MESSAGE_DELIVERIES_WEIGHT
        self.P4 = 0 # num invalid message uncapped
        self.W5 = TOPIC_WEIGHT
        self.P5 = 0 # application specific
        self.W6 = -0.1
        self.P6 = 0 # node id collocation

        self.score = 0

        # state
        self.in_mesh = False
        self.mesh_r = 0 # in round
        #  self.graft_r = 0 # in round

        # background
        self.decay_r = 0

    def init_r(self, r):
        self.r = r

    def run_background(self, curr_r):
        self.update_p1(curr_r)
        self.get_score()

        # Measure Mesh Message Delivery Rate (P3a)
        if self.mesh_r > 9:
            count_r = self.mesh_r - 10
            if count_r % MESH_MESSAGE_DELIVERY_WINDOW == 0:
                self.reset_msg_delivery()
            elif count_r % (MESH_MESSAGE_DELIVERY_WINDOW-1) == 0:
                self.update_p3a()

        # Decay
        if curr_r - self.decay_r >= DECAY_INTERVAL:
            #  print('Decay, current round: {}, decay_r: {}'.format(curr_r, self.decay_r))
            self.decay_r = curr_r
            self.decay()


    def update_p1(self, r):
        if self.in_mesh:
            #  self.mesh_r = r - self.graft_r
            self.mesh_r += 1
        self.P1 = self.mesh_r

    def update_p2(self):
        # num first msg from, when first get the message
        self.P2 += 1

    def reset_msg_delivery(self):
        self.msg_delivery = 0
    def add_msg_delivery(self):
        self.msg_delivery += 1
    def update_p3a(self):
        # mesh message deliveries, when window ends
        # update p3a
        if self.msg_delivery >= MESH_MESSAGE_DELIVERIES_THRESHOLD:
            self.P3a = 0
        else:
            self.P3a = (MESH_MESSAGE_DELIVERIES_THRESHOLD-self.msg_delivery)**2

    def update_p3b(self, rate_deficit):
        # Whenever a peer is pruned with a negative score, the parameter is augmented by the rate deficit at the time of prune.
        self.P3b += rate_deficit
    
    def update_p4(self):
        # invalid messages, when get the invalid message
        self.P4 += 1

    def update_p5(self):
        # TODO
        pass

    def update_p6(self):
        # TODO
        pass

    # TODO add decay to all counters, see section 5.2
    def decay(self):
        self.W2 *= FIRST_MESSAGE_DELIVERIES_DECAY
        self.W3a *= MESH_MESSAGE_DELIVERIES_DECAY
        self.W3b *= MESH_FAILURE_PENALTY_DECAY 
        self.W4 *= INVALID_MESSAGE_DELIVERIES_DECAY
    
    # TODO implement window-ed counters 
    def get_counters(self):
        pass

    def get_score(self):
        score1 = self.W1 * self.P1
        if score1 > TIME_IN_MESH_CAP:
            score1 = TIME_IN_MESH_CAP
        score2 = self.W2 * self.P2
        if score2 > FIRST_MESSAGE_DELIVERIES_CAP:
            score2 = FIRST_MESSAGE_DELIVERIES_CAP 
        score3a = self.W3a * self.P3a
        if score3a < (-MESH_MESSAGE_DELIVERIES_CAP):
            score3a = -MESH_MESSAGE_DELIVERIES_CAP
        score3b = self.W3b * self.P3b
        score4 = self.W4 * self.P4
        score5 = self.W5 * self.P5
        score6 = self.W6 * self.P6

        # self.score = score1 + score2 + score3a + score3b + score4 + score5 + score6 
        self.score = score1+ score2 + score3a + score4 + score5 + score6 
        return self.score

    def get_fake_score(self):
        self.fake_score += random.uniform(-1,1)
        return self.fake_score


