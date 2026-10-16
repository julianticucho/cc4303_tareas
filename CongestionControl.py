
class CongestionControl:

    SLOW_START = "slow_start"
    CONGESTION_AVOIDANCE = "congestion_avoidance"

    def __init__(self, MSS: int):
        self.MSS = MSS
        self.cwnd = MSS  # en bytes, parte con 1 MSS
        self.ssthresh = None  # se define con el primer timeout
        self.current_state = self.SLOW_START

    def get_cwnd(self) -> int:
        return self.cwnd

    def get_MSS_in_cwnd(self) -> int:
        return int(self.cwnd // self.MSS)

    def get_ssthresh(self):
        return self.ssthresh

    def is_state_slow_start(self) -> bool:
        return self.current_state == self.SLOW_START

    def is_state_congestion_avoidance(self) -> bool:
        return self.current_state == self.CONGESTION_AVOIDANCE
    
    def event_ack_received(self):
        if self.is_state_slow_start():
            # slow start: sube 1 MSS por cada ACK
            self.cwnd += self.MSS
            # si ya tenemos ssthresh y la cwnd lo alcanzó, pasamos a AIMD
            if self.ssthresh is not None and self.cwnd >= self.ssthresh:
                self.current_state = self.CONGESTION_AVOIDANCE
        else:
            # congestion avoidance: sube una fracción de MSS por ACK,
            # 1 MSS recién cuando se acumulan MSS_in_cwnd ACKs
            self.cwnd += self.MSS / self.get_MSS_in_cwnd()
    
    def event_timeout(self):
        # el umbral se calcula con la cwnd actual, antes de resetearla
        self.ssthresh = int(self.cwnd / 2)
        self.cwnd = self.MSS  # vuelvo a 1 MSS
        self.current_state = self.SLOW_START