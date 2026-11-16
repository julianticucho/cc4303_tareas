from router import create_packet, fragment_IP_packet, reassemble_IP_packet


def make_packet(message, packet_id=347, offset=0):
    return create_packet({
        "destination_address": ("127.0.0.1", 8885),
        "ttl": 10,
        "id": packet_id,
        "offset": offset,
        "size": len(message),
        "flag": 0,
        "message": message,
    })


# 1) ida y vuelta: 150 bytes, MTU 100, en orden
big = make_packet(bytes(range(132)))
frags = fragment_IP_packet(big, 100)
print("caso 1:", len(frags), "fragmentos en orden ->", reassemble_IP_packet(frags) == big)
assert reassemble_IP_packet(frags) == big

# 2) mismos fragmentos en desorden
print("caso 2: desorden ->", reassemble_IP_packet([frags[1], frags[0]]) == big)
assert reassemble_IP_packet([frags[1], frags[0]]) == big

# 3) re-fragmentado con MTU 50 y totalmente invertido
frags50 = fragment_IP_packet(big, 50)
print("caso 3: MTU 50 invertido ->", reassemble_IP_packet(frags50[::-1]) == big)
assert reassemble_IP_packet(frags50[::-1]) == big

# 4) lista incompleta: falta el ultimo fragmento
print("caso 4: sin el ultimo ->", reassemble_IP_packet(frags[:-1]))
assert reassemble_IP_packet(frags[:-1]) is None

# 5) solo el ultimo fragmento suelto (flag 0 pero offset 82)
print("caso 5: ultimo suelto ->", reassemble_IP_packet([frags[1]]))
assert reassemble_IP_packet([frags[1]]) is None

# 6) un solo elemento que es el paquete completo sin fragmentar
print("caso 6: sin fragmentar ->", reassemble_IP_packet([big]) == big)
assert reassemble_IP_packet([big]) == big

# 7) fragmentos de dos IDs distintos intercalados: no se puede ensamblar
a = make_packet(bytes(range(132)), packet_id=347)
b = make_packet(b"mensaje corto de otro paquete", packet_id=500)
fa = fragment_IP_packet(a, 100)
fb = fragment_IP_packet(b, 100)
print("caso 7: IDs mezclados ->", reassemble_IP_packet([fa[0], fb[0], fa[1]]))
assert reassemble_IP_packet([fa[0], fb[0], fa[1]]) is None

print("todos los casos OK")
