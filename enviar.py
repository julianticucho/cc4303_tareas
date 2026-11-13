import sys
import socket
from router import create_packet


# este es el host de nuestro mini-internet: arma el diccionario parseado con
# destino final, ttl y mensaje, lo pasa por create_packet para obtener los
# bytes del paquete, y lo manda con un socket UDP via sendto
def main():
    # python3 enviar.py IP_router_final puerto_router_final mensaje IP_envio puerto_envio [TTL]
    if len(sys.argv) not in (6, 7):
        print("Uso: python3 enviar.py IP_router_final puerto_router_final mensaje IP_envio puerto_envio [TTL]")
        sys.exit(1)

    final_ip = sys.argv[1]
    final_port = int(sys.argv[2])
    message = sys.argv[3]
    send_ip = sys.argv[4]
    send_port = int(sys.argv[5])
    ttl = int(sys.argv[6]) if len(sys.argv) == 7 else 255

    parsed_packet = {
        "destination_address": (final_ip, final_port),
        "ttl": ttl,
        "message": message.encode(),
    }
    packet = create_packet(parsed_packet)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (send_ip, send_port))

    print(f"Paquete enviado: {packet!r}")
    print(f"  Destino final (header): ({final_ip}, {final_port})")
    print(f"  TTL: {ttl}")
    print(f"  Enviado hacia (socket): ({send_ip}, {send_port})")


if __name__ == "__main__":
    main()
