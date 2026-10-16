import sys
import SocketTCP

# uso: python3 cliente.py <host> <puerto> [--debug] [--cc] [--timeout S] [--mode stop_and_wait|go_back_n] < archivo.txt
debug = False
mode = "stop_and_wait"
cc = False
timeout = None
args = []
i = 1
while i < len(sys.argv):
    if sys.argv[i] == "--debug":
        debug = True
    elif sys.argv[i] == "--cc":
        cc = True
    elif sys.argv[i] == "--mode":
        mode = sys.argv[i + 1]
        i += 1
    elif sys.argv[i] == "--timeout":
        timeout = float(sys.argv[i + 1])
        i += 1
    else:
        args.append(sys.argv[i])
    i += 1
host, port = args[0], int(args[1])

client_socketTCP = SocketTCP.SocketTCP()
client_socketTCP.debug = debug
client_socketTCP.set_congestion_control(cc)
if timeout is not None:
    client_socketTCP.timeout = timeout
client_socketTCP.connect((host, port))

# (1) cargar todo el archivo de entrada estándar
data = sys.stdin.buffer.read()

# (2) enviarlo con el modo elegido y cerrar la conexión
client_socketTCP.send(data, mode=mode)
print(f"Cliente: enviado {len(data)} bytes, {client_socketTCP.number_of_sent_segments} segmentos de datos", file=sys.stderr)
client_socketTCP.close()
print("Cliente: conexión cerrada", file=sys.stderr)