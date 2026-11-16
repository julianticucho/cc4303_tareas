from router import parse_packet, create_packet, fragment_IP_packet, HEADER_SIZE


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


# 1) paquete chico con MTU grande: lista de 1, intacto
small = make_packet(b"hola!")
result = fragment_IP_packet(small, 100)
print("caso 1 (cabe):", len(result), "fragmento(s)")
assert result == [small]

# 2) paquete de 150 bytes totales (18 de header + 132 de mensaje), MTU 100
big = make_packet(bytes(range(132)))
frags = fragment_IP_packet(big, 100)
print("caso 2 (fragmenta):", len(frags), "fragmentos de tamano", [len(f) for f in frags])
assert all(len(f) <= 100 for f in frags)
for f in frags:
    p = parse_packet(f)
    print("  id", p["id"], "offset", p["offset"], "size", p["size"], "flag", p["flag"], "ttl", p["ttl"])
assert [parse_packet(f)["offset"] for f in frags] == [0, 82]
assert [parse_packet(f)["size"] for f in frags] == [82, 50]
assert [parse_packet(f)["flag"] for f in frags] == [1, 0]

# 3) re-fragmentacion: el primer fragmento (mensaje de 82) contra un enlace MTU 50
refrag = fragment_IP_packet(frags[0], 50)
print("caso 3 (re-fragmenta):", len(refrag), "fragmentos de tamano", [len(f) for f in refrag])
assert all(len(f) <= 50 for f in refrag)
for f in refrag:
    p = parse_packet(f)
    print("  id", p["id"], "offset", p["offset"], "size", p["size"], "flag", p["flag"], "ttl", p["ttl"])
assert [parse_packet(f)["offset"] for f in refrag] == [0, 32, 64]
assert [parse_packet(f)["flag"] for f in refrag] == [1, 1, 1]

print("todos los casos OK")
