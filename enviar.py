import sys
import socket
from router import create_packet


# este es el host de nuestro mini-internet: arma el diccionario parseado con
# destino final, ttl, id, offset, tamano y flag, lo pasa por create_packet para
# obtener los bytes del paquete, y lo manda con un socket UDP via sendto
def main():
    # python3 enviar.py IP_router_final puerto_router_final mensaje IP_envio puerto_envio [TTL] [ID]
    if len(sys.argv) not in (6, 7, 8):
        print("Uso: python3 enviar.py IP_router_final puerto_router_final mensaje IP_envio puerto_envio [TTL] [ID]")
        sys.exit(1)

    final_ip = sys.argv[1]
    final_port = int(sys.argv[2])
    message = sys.argv[3]
    send_ip = sys.argv[4]
    send_port = int(sys.argv[5])
    ttl = int(sys.argv[6]) if len(sys.argv) >= 7 else 255
    packet_id = int(sys.argv[7]) if len(sys.argv) == 8 else 1

    parsed_packet = {
        "destination_address": (final_ip, final_port),
        "ttl": ttl,
        "id": packet_id,
        "offset": 0,
        "size": len(message.encode()),
        "flag": 0,
        "message": message.encode(),
    }
    packet = create_packet(parsed_packet)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (send_ip, send_port))

    print(f"Paquete enviado: {packet!r}")
    print(f"  Destino final (header): ({final_ip}, {final_port})")
    print(f"  TTL: {ttl}, ID: {packet_id}, offset 0, tamano {len(message.encode())}, flag 0")
    print(f"  Enviado hacia (socket): ({send_ip}, {send_port})")


if __name__ == "__main__":
    main()
