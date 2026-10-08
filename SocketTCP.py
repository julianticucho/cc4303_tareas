import socket
import random
import sys
import time

HEADER_SIZE = 7 
MAX_DATA = 16

class SocketTCP:
    def __init__(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.local_addr = None
        self.dest_addr = None
        self.seq = 0
        self.timeout = 2
        self.debug = False
        self.message_length = 0
        self.pending = 0
        self.buffer = b""
    
    @staticmethod
    def parse_segment(segment):
        return {
            "syn": bool(segment[0]),
            "ack": bool(segment[1]),
            "fin": bool(segment[2]),
            "seq": int.from_bytes(segment[3:7], "big"),
            "data": segment[7:],
        }
    
    @staticmethod
    def create_segment(parsed):
        return bytes([
            int(parsed["syn"]),
            int(parsed["ack"]),
            int(parsed["fin"]),
        ]) + parsed["seq"].to_bytes(4, "big") + parsed["data"]

    def _send_segment(self, syn, ack, fin, seq, data=b"", resend=False):
        segment = self.create_segment({
            "syn": syn,
            "ack": ack,
            "fin": fin,
            "seq": seq,
            "data": data,
        })
        self.udp_socket.sendto(segment, self.dest_addr)
        if self.debug:
            types = []
            if syn:
                types.append("SYN")
            if ack:
                types.append("ACK")
            if fin:
                types.append("FIN")
            if not types:
                types.append("DATOS")
            mark = " [reenvío]" if resend else ""
            print(f"[DEBUG] Enviando {'+'.join(types)} seq={seq} ({len(data)} bytes){mark}", file=sys.stderr)

    def bind(self, address):
        self.udp_socket.bind(address)
        self.local_addr = self.udp_socket.getsockname()
        if self.debug:
            print(f"[DEBUG] bind en {self.local_addr}", file=sys.stderr)
    
    # lado del cliente
    def connect(self, address):
        # (1) elegir un seq aleatorio  
        self.dest_addr = address
        self.seq = random.randint(0, 100)

        # (2) enviar el SYN y esperar el SYN+ACK, si hay timeout, retransmitir
        self.udp_socket.settimeout(self.timeout)
        synack_ok = False
        resend = False
        while not synack_ok:
            self._send_segment(True, False, False, self.seq, resend=resend)
            try:
                while not synack_ok:
                    segment, addr = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
                    parsed = self.parse_segment(segment)
                    if parsed["syn"] and parsed["ack"]:
                        if self.debug:
                            print(f"[DEBUG] connect: recibí SYN+ACK seq={parsed["seq"]} desde {addr}", file=sys.stderr)
                        synack_ok = True
            except socket.timeout:
                # no llegó el SYN+ACK, retransmitir el SYN
                if self.debug:
                    print(f"[DEBUG] connect: timeout, retransmito SYN seq={self.seq}", file=sys.stderr)
                resend = True
        
        # (3) enviar un ACK final
        self.dest_addr = addr
        self.seq = parsed["seq"] + 1
        self._send_segment(False, True, False, self.seq)
        self.seq += 1
        self.udp_socket.settimeout(None)

    # lado del servidor
    def accept(self):
        # (1) espera hasta que llege un SYN
        while True:
            segment, addr = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
            parsed = self.parse_segment(segment)
            if parsed["syn"] and not parsed["ack"]:
                break
        if self.debug:
            print(f"[DEBUG] accept: recibí SYN seq={parsed["seq"]} de {addr}", file=sys.stderr)
        
        # (2) crear un socket nuevo de la conexión
        conn = SocketTCP()
        conn.debug = self.debug
        conn.udp_socket.bind((self.local_addr[0], 0))
        conn.local_addr = conn.udp_socket.getsockname()
        conn.dest_addr = addr
        conn.seq = parsed["seq"] + 1

        # (3) enviar un SYN+ACK        
        # (4) esperar el ACK final
        conn.udp_socket.settimeout(self.timeout)
        ack_ok = False
        resend = False
        while not ack_ok:
            conn._send_segment(True, True, False, conn.seq, resend=resend)
            try:
                while not ack_ok:
                    segment, addr2 = conn.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
                    parsed2 = conn.parse_segment(segment)
                    if parsed2["ack"] and not parsed2["syn"] and parsed2["seq"] == conn.seq + 1:
                        if self.debug:
                            print(f"[DEBUG] accept: recibí ACK seq={parsed2['seq']}, handshake completo", file=sys.stderr)
                        ack_ok = True
            except socket.timeout:
                # no llegó el ACK, retransmitir el SYN+ACK
                if self.debug:
                    print(f"[DEBUG] accept: timeout, retransmito SYN+ACK seq={conn.seq}", file=sys.stderr)
                resend = True
        
        conn.udp_socket.settimeout(None)
        conn.seq = parsed2["seq"] + 1
        return conn, conn.local_addr
    
    # lado del emisor: stop and wait
    def send(self, message):
        # (1) primer segmento con el largo del mensaje, luego trozos de 16 bytes
        parts = [len(message).to_bytes(4, "big")]
        for i in range(0, len(message), MAX_DATA):
            parts.append(message[i:i+MAX_DATA])

        # (2) enviar cada parte y esperar su ACK antes de pasar a la siguiente
        self.udp_socket.settimeout(self.timeout)
        for part in parts:
            seq_segment = self.seq
            esperado = self.seq + len(part)
            ack_ok = False
            resend = False
            while not ack_ok:
                self._send_segment(False, False, False, seq_segment, part, resend=resend)
                try:
                    # esperar hasta recibir un ACK con el seq que corresponde
                    while not ack_ok:
                        raw, _ = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
                        parsed = self.parse_segment(raw)
                        
                        # caso borde: se perdió el último ACK del handshake,
                        # el servidor reenvía el SYN+ACK; hay que reenviar ese ACK
                        if parsed["syn"] and parsed["ack"]:
                            if self.debug:
                                print(f"[DEBUG] send: SYN+ACK duplicado del handshake, reenvío ACK seq={parsed['seq'] + 1}", file=sys.stderr)
                            self._send_segment(False, True, False, parsed["seq"] + 1)
                            continue
                        
                        if parsed["ack"] and parsed["seq"] == esperado:
                            ack_ok = True
                        
                except socket.timeout:
                    # si no llego el ACK a tiempo, retransmitir el mismo segmento
                    if self.debug:
                        print(f"[DEBUG] send: timeout esperando ACK de seq={seq_segment}, retransmito", file=sys.stderr)
                    resend = True
            self.seq = esperado
        self.udp_socket.settimeout(None)
        if self.debug:
            print(f"[DEBUG] send: mensaje de {len(message)} bytes entregado", file=sys.stderr)

    # lado del receptor: stop and wait
    def recv(self, buff_size):
        # (1) si no hay mensaje en curso, esperar el segmento que trae el largo
        if self.message_length == 0:
            while True:
                raw, _ = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
                parsed = self.parse_segment(raw)
                # si seq es distinto al esperado es un duplicado, reenviar el ACK y ignorar
                if parsed["seq"] != self.seq or not parsed["data"]:
                    self._send_segment(False, True, False, self.seq)
                    if self.debug:
                        print(f"[DEBUG] recv: duplicado seq={parsed['seq']}, reenvío ACK seq={self.seq}", file=sys.stderr)
                    continue
                self.message_length = int.from_bytes(parsed["data"], "big")
                self.pending = self.message_length
                self.seq += len(parsed["data"])
                self._send_segment(False, True, False, self.seq)
                if self.debug:
                    print(f"[DEBUG] recv: largo del mensaje = {self.message_length}", file=sys.stderr)
                break
        
        # (2) cuánto falta entregar de este mensaje, sin pasar buff_size
        target = min(self.pending + len(self.buffer), buff_size)

        # (3) recibir segmentos y acumular hasta llegar a la meta
        while len(self.buffer) < target:
            raw, _ = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
            parsed = self.parse_segment(raw)
            # duplicado: solo reenviar el ACK, los datos ya se entregaron
            if parsed["seq"] != self.seq or not parsed["data"]:
                self._send_segment(False, True, False, self.seq)
                if self.debug:
                    print(f"[DEBUG] recv: duplicado seq={parsed['seq']}, reenvío ACK seq={self.seq}", file=sys.stderr)
                continue
            self.buffer += parsed["data"]
            self.pending -= len(parsed["data"])
            self.seq += len(parsed["data"])
            self._send_segment(False, True, False, self.seq)
            if self.debug:
                print(f"[DEBUG] recv: seq={parsed['seq']} ({len(parsed['data'])} bytes)", file=sys.stderr)

        # (4) entregar a lo sumo buff_size bytes
        result = self.buffer[:target]
        self.buffer = self.buffer[target:]

        # (5) si se entregó todo el mensaje, dejar el estado listo para el próximo
        if self.pending == 0 and len(self.buffer) == 0:
            self.message_length = 0

        if self.debug:
            print(f"[DEBUG] recv: entregando {len(result)} bytes", file=sys.stderr)
        return result
    
    # lado del emisor: cierre de conexión
    def close(self):
        # (1) enviar el FIN y esperar el FIN+ACK seq=z+1, hasta 3 timeouts
        timeouts = 0
        finack_ok = False
        resend = False
        self.udp_socket.settimeout(self.timeout)
        while not finack_ok and timeouts < 3:
            self._send_segment(False, False, True, self.seq, resend=resend)
            try:
                while not finack_ok:
                    segment, addr = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
                    parsed = self.parse_segment(segment)
                    if parsed["fin"] and parsed["ack"] and parsed["seq"] == self.seq + 1:
                        if self.debug:
                            print(f"[DEBUG] close: recibí FIN+ACK seq={parsed['seq']}", file=sys.stderr)
                        finack_ok = True
            except socket.timeout:
                # no llegó el FIN+ACK, reenviar el mismo FIN
                timeouts += 1
                if self.debug:
                    print(f"[DEBUG] close: timeout {timeouts}/3 esperando FIN+ACK, reenvío FIN", file=sys.stderr)
                resend = True

        # (2) con FIN+ACK recibido, reenviar el último ACK 3 veces, 
        # esperando un timeout entre envíos
        if finack_ok:
            self.seq = parsed["seq"] + 1
            for i in range(3):
                if i > 0:
                    time.sleep(self.timeout)
                self._send_segment(False, True, False, self.seq, resend=(i > 0))
            self.seq += 1
        else:
            # 3er timeout: asumo que la contraparte se cerró
            if self.debug:
                print("[DEBUG] close: 3 timeouts sin FIN+ACK, asumo que la contraparte cerró", file=sys.stderr)

        # (3) liberar el socket UDP
        self.udp_socket.close()

    # lado del receptor: continúa el cierre de conexión
    def recv_close(self):
        # (1) esperar el FIN seq=z, hasta 3 timeouts
        timeouts = 0
        fin_ok = False
        self.udp_socket.settimeout(self.timeout)
        while not fin_ok and timeouts < 3:
            try:
                while not fin_ok:
                    segment, addr = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
                    parsed = self.parse_segment(segment)
                    if parsed["fin"] and not parsed["ack"] and parsed["seq"] == self.seq:
                        if self.debug:
                            print(f"[DEBUG] recv_close: recibí FIN seq={parsed['seq']}", file=sys.stderr)
                        fin_ok = True
                    elif parsed["data"]:
                        # dato duplicado (se perdió su ACK): reenviar el ACK para que
                        # el emisor no quede retransmitiendo para siempre
                        self._send_segment(False, True, False, self.seq)
                        if self.debug:
                            print(f"[DEBUG] recv_close: dato duplicado seq={parsed['seq']}, reenvío ACK seq={self.seq}", file=sys.stderr)

            except socket.timeout:
                timeouts += 1
                if self.debug:
                    print(f"[DEBUG] recv_close: timeout {timeouts}/3 esperando FIN", file=sys.stderr)

        if not fin_ok:
            # 3er timeout: asumo que la contraparte se cerró
            if self.debug:
                print("[DEBUG] recv_close: 3 timeouts sin FIN, asumo que la contraparte cerró", file=sys.stderr)
            self.udp_socket.close()
            return

        # (2) responder con un FIN+ACK seq=z+1
        self.seq = parsed["seq"] + 1
        self._send_segment(False, True, True, self.seq)

        # (3) esperar el ACK final seq=z+2
        timeouts = 0
        ack_ok = False
        while not ack_ok and timeouts < 3:
            try:
                while not ack_ok:
                    segment, addr = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
                    parsed2 = self.parse_segment(segment)
                    if parsed2["ack"] and not parsed2["fin"] and parsed2["seq"] == self.seq + 1:
                        if self.debug:
                            print(f"[DEBUG] recv_close: recibí ACK seq={parsed2['seq']}, conexión cerrada", file=sys.stderr)
                        ack_ok = True
                        self.seq = parsed2["seq"] + 1
                    elif parsed2["fin"] and not parsed2["ack"]:
                        # el emisor reenvía el FIN porque no recibió nuestro FIN+ACK:
                        # reenviar el FIN+ACK y renovar la espera
                        timeouts = 0
                        self._send_segment(False, True, True, self.seq)
                        if self.debug:
                            print(f"[DEBUG] recv_close: FIN duplicado, reenvío FIN+ACK seq={self.seq}", file=sys.stderr)
                    
            except socket.timeout:
                timeouts += 1
                if self.debug:
                    print(f"[DEBUG] recv_close: timeout {timeouts}/3 esperando el ACK final", file=sys.stderr)

        if not ack_ok:
            # 3er timeout: asumo que la contraparte se cerró
            if self.debug:
                print("[DEBUG] recv_close: 3 timeouts sin ACK final, asumo que la contraparte cerró", file=sys.stderr)

        # (4) liberar el socket UDP
        self.seq = parsed2["seq"] + 1
        self.udp_socket.close()
