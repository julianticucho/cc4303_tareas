import sys
import SocketTCP

# uso: python3 cliente.py <host> <puerto> [--debug] < archivo.txt
debug = "--debug" in sys.argv
args = [a for a in sys.argv[1:] if a != "--debug"]
host, port = args[0], int(args[1])

client_socketTCP = SocketTCP.SocketTCP()
client_socketTCP.debug = debug
client_socketTCP.connect((host, port))

# (1) cargar todo el archivo de entrada estándar
data = sys.stdin.buffer.read()

# (2) enviarlo con Stop & Wait y cerrar la conexión
client_socketTCP.send(data)
print(f"Cliente: enviado {len(data)} bytes", file=sys.stderr)
client_socketTCP.close()
print("Cliente: conexión cerrada", file=sys.stderr)
