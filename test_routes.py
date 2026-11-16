from router import check_routes

cases = [
    ("rutas/rutas_R1_v3_mtu.txt", ("127.0.0.1", 8882), (("127.0.0.1", 8882), 100)),
    ("rutas/rutas_R1_v3_mtu.txt", ("127.0.0.1", 8885), (("127.0.0.1", 8882), 100)),
    ("rutas/rutas_R2_v3_mtu.txt", ("127.0.0.1", 8881), (("127.0.0.1", 8881), 100)),
    ("rutas/rutas_R2_v3_mtu.txt", ("127.0.0.1", 8883), (("127.0.0.1", 8883), 50)),
    ("rutas/rutas_R3_v3_mtu.txt", ("127.0.0.1", 8885), (("127.0.0.1", 8882), 50)),
    ("rutas/rutas_R4_v3_mtu.txt", ("127.0.0.1", 8885), (("127.0.0.1", 8882), 80)),
    ("rutas/rutas_R5_v3_mtu.txt", ("127.0.0.1", 8881), (("127.0.0.1", 8884), 140)),
    ("rutas/rutas_R1_v3.txt",     ("127.0.0.1", 8885), (("127.0.0.1", 8882), 65535)),
    ("rutas/rutas_R1_v3_mtu.txt", ("127.0.0.1", 9999), None),
]

for routes_file, dest, expected in cases:
    result = check_routes(routes_file, dest)
    status = "OK" if result == expected else "FALLA"
    print(f"{status}: check_routes({routes_file!r}, {dest}) = {result} (esperado {expected})")
