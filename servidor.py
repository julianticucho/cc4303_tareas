import sys
import SocketTCP

# uso: python3 servidor.py <host> <puerto> [--debug] [--buff N] > recibido.txt
debug = "--debug" in sys.argv
buff_size = int(sys.argv[sys.argv.index("--buff") + 1]) if "--buff" in sys.argv else 1 << 20
args = [a for a in sys.argv[1:] if a not in ("--debug", "--buff") and a != str(buff_size)]
host, puerto = args[0], int(args[1])

server_socketTCP = SocketTCP.SocketTCP()
server_socketTCP.debug = debug
server_socketTCP.bind((host, puerto))
print(f"Escuchando en {server_socketTCP.local_addr}", file=sys.stderr)

connection_socketTCP, new_address = server_socketTCP.accept()

# (1) recibir el archivo hasta completar el mensaje
data = b""
while True:
    data += connection_socketTCP.recv(buff_size)
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
