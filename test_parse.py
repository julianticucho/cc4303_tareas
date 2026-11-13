from router import parse_packet, create_packet

# 127 . 0 . 0 . 1  |  puerto 8882  |  TTL 10  |  mensaje
IP_packet_v1 = bytes([127, 0, 0, 1]) + (8882).to_bytes(2, "big") + bytes([10]) + b"hola R2!"

parsed_IP_packet = parse_packet(IP_packet_v1)
print("Parsed:", parsed_IP_packet)

IP_packet_v2 = create_packet(parsed_IP_packet)
print("IP_packet_v1 == IP_packet_v2 ? {}".format(IP_packet_v1 == IP_packet_v2))
