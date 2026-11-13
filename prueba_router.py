import sys
import time
import socket
from router import create_packet


# lee un archivo linea por linea desde stdin, encapsula cada linea con el
# header dado (formato IP;puerto;TTL) y envia cada paquete por UDP al router
# inicial indicado, opcionalmente espera `delay` segundos entre paquetes.
def main():
    # python3 prueba_router.py IP;puerto;TTL IP_router_inicial puerto_router_inicial [delay]
    if len(sys.argv) not in (4, 5):
        print("Uso: python3 prueba_router.py IP;puerto;TTL IP_router_inicial puerto_router_inicial [delay]")
        sys.exit(1)

    final_ip, final_port_str, ttl_str = sys.argv[1].split(";")
    headers = {
        "destination_address": (final_ip, int(final_port_str)),
        "ttl": int(ttl_str),
    }
    send_ip = sys.argv[2]
    send_port = int(sys.argv[3])
    delay = float(sys.argv[4]) if len(sys.argv) == 5 else 0

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for line in sys.stdin:
        message = line.rstrip("\n")
        if not message:
            continue
        packet = create_packet({**headers, "message": message.encode()})
        sock.sendto(packet, (send_ip, send_port))
        print(f"enviado: {packet!r}")
        if delay:
            time.sleep(delay)


if __name__ == "__main__":
    main()
