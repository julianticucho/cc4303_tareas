from router import parse_packet, create_packet

# 127 . 0 . 0 . 1 | puerto 8882 | TTL 10 | ID 347 | offset 0 | tamano 5 | flag 0 | mensaje
IP_packet_v1 = (bytes([127, 0, 0, 1])
    + (8882).to_bytes(2, "big")
    + bytes([10])
    + (347).to_bytes(2, "big")
    + (0).to_bytes(4, "big")
    + (5).to_bytes(4, "big")
    + bytes([0])
    + b"hola!")

parsed_IP_packet = parse_packet(IP_packet_v1)
print("Parsed:", parsed_IP_packet)

IP_packet_v2 = create_packet(parsed_IP_packet)
print("IP_packet_v1 == IP_packet_v2 ? {}".format(IP_packet_v1 == IP_packet_v2))
