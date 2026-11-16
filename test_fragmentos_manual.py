import socket
import time
from router import create_packet, fragment_IP_packet

ROUTER_INICIAL = ("127.0.0.1", 8881)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def make_packet(message, packet_id):
    return create_packet({
        "destination_address": ("127.0.0.1", 8885),
        "ttl": 255,
        "id": packet_id,
        "offset": 0,
        "size": len(message),
        "flag": 0,
        "message": message,
    })


# los dos datagramas de prueba, con IDs distintos, y sus listas de fragmentos
paquete_a = make_packet(b"A" * 132, 111)   # 150 bytes -> 2 fragmentos con MTU 100
paquete_b = make_packet(b"B" * 90, 222)    # 108 bytes -> 2 fragmentos con MTU 100

lista_a = fragment_IP_packet(paquete_a, 100)
lista_b = fragment_IP_packet(paquete_b, 100)
print("lista A (ID 111): tamanos", [len(f) for f in lista_a])
print("lista B (ID 222): tamanos", [len(f) for f in lista_b])


def enviar(fragmentos, delay=0.5):
    for fragment in fragmentos:
        sock.sendto(fragment, ROUTER_INICIAL)
        print("enviado:", len(fragment), "bytes")
        time.sleep(delay)


print("--- caso 1: lista A en orden ---")
enviar(lista_a)
time.sleep(1)

print("--- caso 2: lista B en desorden ---")
enviar(lista_b[::-1])
time.sleep(1)

print("--- caso 3: A y B intercalados ---")
enviar([lista_a[0], lista_b[0], lista_a[1], lista_b[1]])
