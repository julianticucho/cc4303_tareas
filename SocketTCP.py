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
        # bytes que faltan por llegar desde la red
        self.pending = 0
        # bytes que ya se descargaron en la red, pero que el 
        # usuario no ha pedido retirar
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

    # el servidor asocia el socket UDP interno con una dirección
    # ip y un puerto específicos, guardamos la dirección asignada
    # para saber exactamente en que puerto quedó escuchando el socket
    def bind(self, address):
        self.udp_socket.bind(address)
        self.local_addr = self.udp_socket.getsockname()
        if self.debug:
            print(f"[DEBUG] bind en {self.local_addr}", file=sys.stderr)
    
    # como cliente establecemos la conexión usando Three-Way Handshake,
    # para esto enviamos un SYN con un seq=x aleatorio y esperamos una 
    # respuesta SYN+ACK, si se cumple el timeout y no ha llegado, volvemos
    # a enviar el SYN con seq=x, si llega cualquier otra cosa que no sea un
    # un SYN+ACK, lo descartamos y continuamos esperando el SYN+ACK,
    # finalmente enviamos el ACK final con el seq que llegó + 1
    def connect(self, address):
        self.dest_addr = address
        self.seq = random.randint(0, 100)
        
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
                if self.debug:
                    print(f"[DEBUG] connect: timeout, retransmito SYN seq={self.seq}", file=sys.stderr)
                resend = True
        
        self.dest_addr = addr
        self.seq = parsed["seq"] + 1
        self._send_segment(False, True, False, self.seq)
        self.seq += 1
        self.udp_socket.settimeout(None)

    # como servidor establemos la conexión usando Three-Way Handshake,
    # aqui tenemos que esperar el SYN que nos envió el cliente, si nos 
    # llega cualquier otra cosa seguimos esperando, luego creamos un
    # nuevo socket dedicado a la conexión, y lo usamos para enviar un
    # SYN+ACK con el seq recibido + 1 al cliente, y esperar una respuesta
    # ACK con el número de secuencia aumentado en 1, esta parte es
    # análoga al enviar/esperar con timeout del connect(), finalmente
    # actualizamos el número de seq y retornamos el socket dedicado
    def accept(self):
        while True:
            segment, addr = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
            parsed = self.parse_segment(segment)
            if parsed["syn"] and not parsed["ack"]:
                break
        if self.debug:
            print(f"[DEBUG] accept: recibí SYN seq={parsed["seq"]} de {addr}", file=sys.stderr)
        
        conn = SocketTCP()
        conn.debug = self.debug
        conn.udp_socket.bind((self.local_addr[0], 0))
        conn.local_addr = conn.udp_socket.getsockname()
        conn.dest_addr = addr
        conn.seq = parsed["seq"] + 1
        
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
                if self.debug:
                    print(f"[DEBUG] accept: timeout, retransmito SYN+ACK seq={conn.seq}", file=sys.stderr)
                resend = True
        
        conn.udp_socket.settimeout(None)
        conn.seq = parsed2["seq"] + 1
        return conn, conn.local_addr
    
    # como emisor, primero enviaremos el largo del mensaje en 4 bytes, y luego 
    # el mensaje en segmentos de 16 bytes, por cada segmento, lo enviamos y esperamos
    # una respuesta ACK del receptor, con número de secuencia aumentado en el largo 
    # del paquete, y con un timeout, esta parte se programa análoga a la parte anterior,
    # finalmente se actualiza el número de seq y se pasa al siguiente segmento 
    def send(self, message):
        parts = [len(message).to_bytes(4, "big")]
        for i in range(0, len(message), MAX_DATA):
            parts.append(message[i:i+MAX_DATA])

        self.udp_socket.settimeout(self.timeout)
        for part in parts:
            seq_segment = self.seq
            esperado = self.seq + len(part)
            ack_ok = False
            resend = False
            while not ack_ok:
                self._send_segment(False, False, False, seq_segment, part, resend=resend)
                try:
                    while not ack_ok:
                        raw, _ = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
                        parsed = self.parse_segment(raw)
                        # caso borde: se perdió el último ACK del handshake,
                        # el servidor reenvía el SYN+ACK, hay que reenviar ese ACK
                        if parsed["syn"] and parsed["ack"]:
                            if self.debug:
                                print(f"[DEBUG] send: SYN+ACK duplicado del handshake, reenvío ACK seq={parsed['seq'] + 1}", file=sys.stderr)
                            self._send_segment(False, True, False, parsed["seq"] + 1)
                            continue
                        if parsed["ack"] and parsed["seq"] == esperado:
                            ack_ok = True
                except socket.timeout:
                    if self.debug:
                        print(f"[DEBUG] send: timeout esperando ACK de seq={seq_segment}, retransmito", file=sys.stderr)
                    resend = True
            self.seq = esperado
        
        self.udp_socket.settimeout(None)
        if self.debug:
            print(f"[DEBUG] send: mensaje de {len(message)} bytes entregado", file=sys.stderr)

    # como receptor, primero esperamos al segmento que trae el largo del mensaje, 
    # luego calculamos cuandos bytes debemos entregar segun el límite solicitado
    # por el usuario, luego seguimos recibiendo segmentos hasta acumular
    # la cantidad necesaria, luego retornamos los datos solicitados cortando 
    # el buffer hasta el tamaño objetivo y conservamos los restantes para futuras
    # llamadas, finalmente si ya se entregaron todos los bytes del mensaje,
    # dejamos todo listo para el próximo mensaje
    def recv(self, buff_size):
        if self.message_length == 0:
            while True:
                raw, _ = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
                parsed = self.parse_segment(raw)
                # si seq es distinto al esperado, reenviar el ACK y ignorar
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
        
        # cuánto falta entregar de este mensaje, sin pasar buff_size
        target = min(self.pending + len(self.buffer), buff_size)
        while len(self.buffer) < target:
            raw, _ = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
            parsed = self.parse_segment(raw)
            # duplicado, solo reenviar el ACK, los datos ya se entregaron
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

        result = self.buffer[:target]
        self.buffer = self.buffer[target:]
        if self.pending == 0 and len(self.buffer) == 0:
            self.message_length = 0
        if self.debug:
            print(f"[DEBUG] recv: entregando {len(result)} bytes", file=sys.stderr)
        return result
    
    # como emisor, si queremos cerrar la conexión tenemos que enviar 
    # un FIN y esperar un FIN+ACK con seq aumentado en 1, esto lo 
    # hacemos análogamente a las otras funciones, pero poniendo un 
    # límite de 3 reintentos, luego con FIN+ACK recibido, reenviamos el
    # último ACK 3 veces seguidas, por si el último paquete se pierde
    # en el camino
    def close(self):
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
                timeouts += 1
                if self.debug:
                    print(f"[DEBUG] close: timeout {timeouts}/3 esperando FIN+ACK, reenvío FIN", file=sys.stderr)
                resend = True

        if finack_ok:
            self.seq = parsed["seq"] + 1
            for i in range(3):
                if i > 0:
                    time.sleep(self.timeout)
                self._send_segment(False, True, False, self.seq, resend=(i > 0))
            self.seq += 1
        else:
            if self.debug:
                print("[DEBUG] close: 3 timeouts sin FIN+ACK, asumo que la contraparte cerró", file=sys.stderr)

        self.udp_socket.close()

    # como receptor, esperamos el FIN que mandó el emisor, si 
    # acumula 3 timeouts sin ver el FIN, asumimos que la contraparte
    # murió, cerrando el socket, luego de recibir el FIN, respondemos
    # con un FIN+ACK con seq + 1, y esperamos un ACK con seq + 2, esto
    # lo programamos análogamente a las otras funciones
    def recv_close(self):
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
            if self.debug:
                print("[DEBUG] recv_close: 3 timeouts sin FIN, asumo que la contraparte cerró", file=sys.stderr)
            self.udp_socket.close()
            return

        self.seq = parsed["seq"] + 1
        self._send_segment(False, True, True, self.seq)
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
            if self.debug:
                print("[DEBUG] recv_close: 3 timeouts sin ACK final, asumo que la contraparte cerró", file=sys.stderr)

        self.seq = parsed2["seq"] + 1
        self.udp_socket.close()
