import sys
import SocketTCP

# uso: python3 servidor.py <host> <puerto> [--debug] [--buff N] [--mode stop_and_wait|go_back_n] > recibido.txt
debug = False
mode = "stop_and_wait"
buff_size = 1 << 20
args = []
i = 1
while i < len(sys.argv):
    if sys.argv[i] == "--debug":
        debug = True
    elif sys.argv[i] == "--buff":
        buff_size = int(sys.argv[i + 1])
        i += 1
    elif sys.argv[i] == "--mode":
        mode = sys.argv[i + 1]
        i += 1
    else:
        args.append(sys.argv[i])
    i += 1
host, puerto = args[0], int(args[1])

server_socketTCP = SocketTCP.SocketTCP()
server_socketTCP.debug = debug
server_socketTCP.bind((host, puerto))
print(f"Escuchando en {server_socketTCP.local_addr}", file=sys.stderr)

connection_socketTCP, new_address = server_socketTCP.accept()

# (1) recibir el archivo hasta completar el mensaje
data = b""
while True:
    data += connection_socketTCP.recv(buff_size, mode=mode)
    if connection_socketTCP.message_length == 0:
        # recv entregó todo el mensaje
        break

# (2) escribirlo en salida estándar
sys.stdout.buffer.write(data)
sys.stdout.buffer.flush()
print(f"Servidor: recibido {len(data)} bytes", file=sys.stderr)

# (3) cierre de conexión
connection_socketTCP.recv_close()
print("Servidor: conexión cerrada", file=sys.stderr)