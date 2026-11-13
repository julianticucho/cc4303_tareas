from router import check_routes

cases = [
    ("rutas/rutas_R1_v2.txt", ("127.0.0.1", 8882), ("127.0.0.1", 8882)),
    ("rutas/rutas_R1_v2.txt", ("127.0.0.1", 8883), ("127.0.0.1", 8882)),
    ("rutas/rutas_R2_v2.txt", ("127.0.0.1", 8881), ("127.0.0.1", 8881)),
    ("rutas/rutas_R2_v2.txt", ("127.0.0.1", 8883), ("127.0.0.1", 8883)),
    ("rutas/rutas_R3_v2.txt", ("127.0.0.1", 8881), ("127.0.0.1", 8882)),
    ("rutas/rutas_R1_v2.txt", ("127.0.0.1", 8884), None),
]

for routes_file, dest, expected in cases:
    result = check_routes(routes_file, dest)
    status = "OK" if result == expected else "FALLA"
    print(f"{status}: check_routes({routes_file!r}, {dest}) = {result} (esperado {expected})")
