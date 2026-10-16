import socket
import random
import sys
import time

from socketUDP import SocketUDP
from slidingWindowCC import SlidingWindowCC
from CongestionControl import CongestionControl

HEADER_SIZE = 7 
MAX_DATA = 16

class SocketTCP:
    def __init__(self):
        self.udp_socket = SocketUDP()
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
        # control de congestión Tahoe: el objeto vive en el socket y se
        # usa dentro de send_using_go_back_n cuando está activado
        self.congestion_controler = CongestionControl(8)
        self.congestion_control_on = False
        # segmentos de datos emitidos, para el experimento comparativo
        self.number_of_sent_segments = 0

    def set_congestion_control(self, on):
        self.congestion_control_on = on
    
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
    
    # SocketUDP no detiene los timers al recibir, hay que pararlos a mano,
    # solo lo hacemos si hay un timer creado, si no, stop_timer crashea
    def _stop_timer(self):
        if self.udp_socket.timer_list[0] is not None:
            self.udp_socket.stop_timer(0)

    def _send_segment(self, syn, ack, fin, seq, data=b"", resend=False, timer=True):
        segment = self.create_segment({
            "syn": syn,
            "ack": ack,
            "fin": fin,
            "seq": seq,
            "data": data,
        })
        if timer is None:
            # envío puro que no toca los timers: si pasáramos por sendto con
            # un timer ya cumplido, SocketUDP intenta reiniciar el Timer
            # muerto y truena con RuntimeError; mandamos directo por el
            # socket interno, el timer de la ventana sigue corriendo y si
            # vence el próximo recvfrom lo anuncia con su TimeoutError
            self.udp_socket.socket_udp.sendto(segment, self.dest_addr)
        else:
            self.udp_socket.sendto(segment, self.dest_addr)
            # timer=False para los ACK puros del receptor: si no, ese timer
            # correría en segundo plano y dispararía un TimeoutError en recv
            if not timer:
                self._stop_timer()
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
        self.local_addr = self.udp_socket.socket_udp.getsockname()
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
                # hay que parar el timer muerto antes de poder reenviar,
                # sendto no puede reiniciar un Timer que ya corrió
                self._stop_timer()
                if self.debug:
                    print(f"[DEBUG] connect: timeout, retransmito SYN seq={self.seq}", file=sys.stderr)
                resend = True
        
        self._stop_timer()
        self.dest_addr = addr
        self.seq = parsed["seq"] + 1
        self._send_segment(False, True, False, self.seq, timer=False)
        self.seq += 1
        self.udp_socket.settimeout(-1)

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
        conn.local_addr = conn.udp_socket.socket_udp.getsockname()
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
                conn._stop_timer()
                if self.debug:
                    print(f"[DEBUG] accept: timeout, retransmito SYN+ACK seq={conn.seq}", file=sys.stderr)
                resend = True
        
        conn._stop_timer()
        conn.udp_socket.settimeout(-1)
        conn.seq = parsed2["seq"] + 1
        return conn, conn.local_addr
    
    # los dispatchers: mode indica qué ARQ usa el emisor y el receptor
    # por dentro, stop & wait es el modo por defecto
    def send(self, message, mode="stop_and_wait"):
        if mode == "stop_and_wait":
            self.send_using_stop_and_wait(message)
        elif mode == "go_back_n":
            self.send_using_go_back_n(message)
    
    def recv(self, buff_size, mode="stop_and_wait"):
        if mode == "stop_and_wait":
            return self.recv_using_stop_and_wait(buff_size)
        elif mode == "go_back_n":
            return self.recv_using_go_back_n(buff_size)
        
    # como emisor, primero enviaremos el largo del mensaje en 4 bytes, y luego 
    # el mensaje en segmentos de 16 bytes, por cada segmento, lo enviamos y esperamos
    # una respuesta ACK del receptor, con número de secuencia aumentado en el largo 
    # del paquete, y con un timeout, esta parte se programa análoga a la parte anterior,
    # finalmente se actualiza el número de seq y se pasa al siguiente segmento 
    def send_using_stop_and_wait(self, message):
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
                            self._send_segment(False, True, False, parsed["seq"] + 1, timer=None)
                            continue
                        if parsed["ack"] and parsed["seq"] == esperado:
                            ack_ok = True
                except socket.timeout:
                    self._stop_timer()
                    if self.debug:
                        print(f"[DEBUG] send: timeout esperando ACK de seq={seq_segment}, retransmito", file=sys.stderr)
                    resend = True
            self._stop_timer()
            self.seq = esperado
        
        self.udp_socket.settimeout(-1)
        if self.debug:
            print(f"[DEBUG] send: mensaje de {len(message)} bytes entregado", file=sys.stderr)


    # como emisor en Go Back N mantenemos una ventana de 8 segmentos en
    # vuelo: los enviamos todos sin esperar sus ACKs uno a uno, un solo
    # timer cubre la ventana, y el ACK es acumulativo: confirma todo lo
    # que llegó en orden hasta su seq. si el timer vence reenviamos la
    # ventana completa, y si el ACK llega con la ventana ya reducida
    # movemos la ventana como si el último elemento hubiese llegado
    def send_using_go_back_n(self, message):
        # mismo armado de partes que en stop & wait, pero con control de
        # congestión los trozos tienen tamaño MSS = 8; sin control
        # mantenemos los 16 bytes y la ventana fija de 8 de antes
        chunk = self.congestion_controler.MSS if self.congestion_control_on else MAX_DATA
        parts = [len(message).to_bytes(4, "big")]
        for i in range(0, len(message), chunk):
            parts.append(message[i:i+chunk])

        # con control de congestión la ventana parte en 1 MSS: cwnd=8
        # y MSS=8 dan get_MSS_in_cwnd()=1; sin control seguimos en 8
        if self.congestion_control_on:
            window_size = self.congestion_controler.get_MSS_in_cwnd()
        else:
            window_size = 8
        data_window = SlidingWindowCC(window_size, parts, self.seq)
        total_acked = 0

        def print_cc():
            if self.debug and self.congestion_control_on:
                print(f"[DEBUG] send_gbn CC: cwnd={self.congestion_controler.get_cwnd()} "
                      f"ssthresh={self.congestion_controler.get_ssthresh()} "
                      f"estado={self.congestion_controler.current_state} "
                      f"window_size={window_size}", file=sys.stderr)

        self.udp_socket.settimeout(self.timeout)
        # enviar la ventana inicial completa, el primer envío crea el timer
        for i in range(window_size):
            d = data_window.get_data(i)
            if d is not None:
                self._send_segment(False, False, False, data_window.get_sequence_number(i), d)
                self.number_of_sent_segments += 1
        print_cc()

        done = False
        while not done:
            try:
                while not done:
                    raw, _ = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
                    parsed = self.parse_segment(raw)
                    # mismo caso borde del handshake que en stop & wait
                    if parsed["syn"] and parsed["ack"]:
                        if self.debug:
                            print(f"[DEBUG] send_gbn: SYN+ACK duplicado, reenvío ACK seq={parsed['seq'] + 1}", file=sys.stderr)
                        self._send_segment(False, True, False, parsed["seq"] + 1, timer=None)
                        continue
                    if not parsed["ack"] or parsed["fin"]:
                        continue
                    ack_seq = parsed["seq"]

                    # el ACK acumulativo confirma todos los segmentos cuyo
                    # fin está cubierto por su seq; si el ACK queda más
                    # allá del último elemento de la ventana movemos como
                    # si el último hubiese llegado, y repetimos si el
                    # siguiente ACK sigue fuera de la ventana
                    while True:
                        steps = 0
                        last_real = -1
                        for i in range(window_size):
                            d = data_window.get_data(i)
                            if d is None:
                                break
                            last_real = i
                            if data_window.get_sequence_number(i) + len(d) <= ack_seq:
                                steps = i + 1
                        if steps == 0 and last_real >= 0:
                            last_end = data_window.get_sequence_number(last_real) + len(data_window.get_data(last_real))
                            if ack_seq > last_end:
                                steps = last_real + 1
                        if steps == 0:
                            # ACK duplicado o viejo, ignorar
                            break

                        old_size = window_size
                        data_window.move_window(steps)
                        total_acked += steps
                        # con control de congestión este ACK confirma datos
                        # y agranda la cwnd; crece la ventana y entran
                        # nuevos segmentos que se envían de inmediato,
                        # igual que cuando avanzábamos la ventana
                        if self.congestion_control_on:
                            self.congestion_controler.event_ack_received()
                            window_size = self.congestion_controler.get_MSS_in_cwnd()
                            if window_size != old_size:
                                data_window.update_window_size(window_size)
                                print_cc()
                        # los segmentos que entraron a la ventana se envían
                        # de inmediato; el primero reinicia el timer, y si
                        # no entran nuevos dejo correr el timer actual para
                        # los que quedan sin confirmar
                        sent_new = 0
                        for i in range(old_size - steps, window_size):
                            d = data_window.get_data(i)
                            if d is not None:
                                if sent_new == 0:
                                    self._stop_timer()
                                self._send_segment(False, False, False, data_window.get_sequence_number(i), d)
                                self.number_of_sent_segments += 1
                                sent_new += 1
                        if self.debug:
                            print(f"[DEBUG] send_gbn: ACK seq={ack_seq} confirma {steps}, entraron {sent_new} segmentos", file=sys.stderr)
                        if total_acked >= len(parts):
                            self._stop_timer()
                            done = True
                            break
            except TimeoutError:
                self._stop_timer()
                # con control de congestión el timeout dispara el
                # multiplicative decrease: ssthresh = cwnd/2, cwnd = 1 MSS
                if self.congestion_control_on:
                    self.congestion_controler.event_timeout()
                    # la ventana se achica al nuevo cwnd y solo queda el
                    # primer segmento sin confirmar para reenviar
                    new_size = self.congestion_controler.get_MSS_in_cwnd()
                    if new_size != window_size:
                        data_window.update_window_size(new_size)
                        window_size = new_size
                    print_cc()
                if self.debug:
                    print(f"[DEBUG] send_gbn: timeout, reenvío la ventana completa", file=sys.stderr)
                # reenviar todos los segmentos sin confirmar de la ventana,
                # el primer envío vuelve a crear el timer
                for i in range(window_size):
                    d = data_window.get_data(i)
                    if d is not None:
                        self._send_segment(False, False, False, data_window.get_sequence_number(i), d, resend=True)
                        self.number_of_sent_segments += 1

        # el envío quedó completo: el próximo seq es el que sigue al
        # último byte transmitido (4 bytes de largo + el mensaje);
        # sin esto close() manda el FIN con un seq viejo y el
        # recv_close del servidor lo descarta y se queda esperando
        self.seq += 4 + len(message)
        if self.debug and self.congestion_control_on:
            print(f"[DEBUG] send_gbn: envié {self.number_of_sent_segments} segmentos de datos", file=sys.stderr)

    # como receptor, primero esperamos al segmento que trae el largo del mensaje, 
    # luego calculamos cuandos bytes debemos entregar segun el límite solicitado
    # por el usuario, luego seguimos recibiendo segmentos hasta acumular
    # la cantidad necesaria, luego retornamos los datos solicitados cortando 
    # el buffer hasta el tamaño objetivo y conservamos los restantes para futuras
    # llamadas, finalmente si ya se entregaron todos los bytes del mensaje,
    # dejamos todo listo para el próximo mensaje
    def recv_using_stop_and_wait(self, buff_size):
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
                self._send_segment(False, True, False, self.seq, timer=False)
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
                self._send_segment(False, True, False, self.seq, timer=False)
                if self.debug:
                    print(f"[DEBUG] recv: duplicado seq={parsed['seq']}, reenvío ACK seq={self.seq}", file=sys.stderr)
                continue
            self.buffer += parsed["data"]
            self.pending -= len(parsed["data"])
            self.seq += len(parsed["data"])
            self._send_segment(False, True, False, self.seq, timer=False)
            if self.debug:
                print(f"[DEBUG] recv: seq={parsed['seq']} ({len(parsed['data'])} bytes)", file=sys.stderr)

        result = self.buffer[:target]
        self.buffer = self.buffer[target:]
        if self.pending == 0 and len(self.buffer) == 0:
            self.message_length = 0
        if self.debug:
            print(f"[DEBUG] recv: entregando {len(result)} bytes", file=sys.stderr)
        return result
    
    # como receptor en Go Back N la lógica no cambia respecto de stop & wait,
    # solo aceptamos segmentos consecutivos, y ante uno fuera de orden
    # reenviamos el ACK del seq que esperamos, el receptor no necesita
    # ventana ni timers, esa parte es solo del emisor
    def recv_using_go_back_n(self, buff_size):
        if self.message_length == 0:
            while True:
                raw, _ = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
                parsed = self.parse_segment(raw)
                # si seq es distinto al esperado, reenviar el ACK y ignorar
                if parsed["seq"] != self.seq or not parsed["data"]:
                    self._send_segment(False, True, False, self.seq, timer=False)
                    if self.debug:
                        print(f"[DEBUG] recv_gbn: fuera de orden seq={parsed['seq']}, reenvío ACK seq={self.seq}", file=sys.stderr)
                    continue
                self.message_length = int.from_bytes(parsed["data"], "big")
                self.pending = self.message_length
                self.seq += len(parsed["data"])
                self._send_segment(False, True, False, self.seq, timer=False)
                if self.debug:
                    print(f"[DEBUG] recv_gbn: largo del mensaje = {self.message_length}", file=sys.stderr)
                break
        
        # cuánto falta entregar de este mensaje, sin pasar buff_size
        target = min(self.pending + len(self.buffer), buff_size)
        while len(self.buffer) < target:
            raw, _ = self.udp_socket.recvfrom(HEADER_SIZE + MAX_DATA)
            parsed = self.parse_segment(raw)
            # fuera de orden, solo reenviar el ACK, los datos ya se entregaron
            if parsed["seq"] != self.seq or not parsed["data"]:
                self._send_segment(False, True, False, self.seq, timer=False)
                if self.debug:
                    print(f"[DEBUG] recv_gbn: fuera de orden seq={parsed['seq']}, reenvío ACK seq={self.seq}", file=sys.stderr)
                continue
            self.buffer += parsed["data"]
            self.pending -= len(parsed["data"])
            self.seq += len(parsed["data"])
            self._send_segment(False, True, False, self.seq, timer=False)
            if self.debug:
                print(f"[DEBUG] recv_gbn: seq={parsed['seq']} ({len(parsed['data'])} bytes)", file=sys.stderr)

        result = self.buffer[:target]
        self.buffer = self.buffer[target:]
        if self.pending == 0 and len(self.buffer) == 0:
            self.message_length = 0
        if self.debug:
            print(f"[DEBUG] recv_gbn: entregando {len(result)} bytes", file=sys.stderr)
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
                self._stop_timer()
                timeouts += 1
                if self.debug:
                    print(f"[DEBUG] close: timeout {timeouts}/3 esperando FIN+ACK, reenvío FIN", file=sys.stderr)
                resend = True

        if finack_ok:
            self._stop_timer()
            self.seq = parsed["seq"] + 1
            for i in range(3):
                if i > 0:
                    time.sleep(self.timeout)
                self._send_segment(False, True, False, self.seq, resend=(i > 0), timer=False)
            self.seq += 1
        else:
            if self.debug:
                print("[DEBUG] close: 3 timeouts sin FIN+ACK, asumo que la contraparte cerró", file=sys.stderr)

        self.udp_socket.close()

    # como receptor, esperamos el FIN que mandó el emisor. si nos
    # llega un dato duplicado reenviamos el ACK correspondiente, ya
    # que su ACK se perdió, luego de recibir el FIN respondemos
    # con un FIN+ACK con seq + 1, y esperamos un ACK con seq + 2
    # con un límite de 3 reintentos, si el emisor reenvía el FIN
    # reenviamos el FIN+ACK y renovamos la espera, ya que eso
    # significa que nuestro FIN+ACK se perdió
    def recv_close(self):
        fin_ok = False
        # esta espera no tiene timer asociado: SocketUDP solo inicia
        # timers al enviar, así que esperamos el FIN sin límite y
        # confiamos en que close() lo retransmite hasta 3 veces
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
                self._send_segment(False, True, False, self.seq, timer=False)
                if self.debug:
                    print(f"[DEBUG] recv_close: dato duplicado seq={parsed['seq']}, reenvío ACK seq={self.seq}", file=sys.stderr)

        self.seq = parsed["seq"] + 1
        # desde aqui el FIN+ACK que enviamos dispara un timer que si
        # nos sirve para acotar la espera del ACK final
        self.udp_socket.settimeout(self.timeout)
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
                        # reenviar el FIN+ACK y renovar la espera, parando antes
                        # el timer por si ya venció, así sendto crea uno nuevo
                        timeouts = 0
                        self._stop_timer()
                        self._send_segment(False, True, True, self.seq)
                        if self.debug:
                            print(f"[DEBUG] recv_close: FIN duplicado, reenvío FIN+ACK seq={self.seq}", file=sys.stderr)
                    
            except socket.timeout:
                self._stop_timer()
                timeouts += 1
                if self.debug:
                    print(f"[DEBUG] recv_close: timeout {timeouts}/3 esperando el ACK final", file=sys.stderr)
                if timeouts < 3:
                    self._send_segment(False, True, True, self.seq)

        if not ack_ok:
            if self.debug:
                print("[DEBUG] recv_close: 3 timeouts sin ACK final, asumo que la contraparte cerró", file=sys.stderr)
            self._stop_timer()

        self.udp_socket.close()
