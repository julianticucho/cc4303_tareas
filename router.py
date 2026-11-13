import sys
import socket


# parse_packet :: toma el paquete en bytes, lo corta, y lo convierte en un
# diccionario de python manejable, la ip se rearma leyendo cada byte como un
# número, el puerto se reconstruye interpretando sus 2 bytes como entero, y el
# ttl se lee del 1 byte que sigue al puerto
def parse_packet(IP_packet: bytes):
    ip_bytes = IP_packet[:4]
    port_bytes = IP_packet[4:6]
    ttl_bytes = IP_packet[6:7]
    message = IP_packet[7:]

    ip = ".".join(str(b) for b in ip_bytes)
    port = int.from_bytes(port_bytes, "big")
    ttl = int.from_bytes(ttl_bytes, "big")

    return {
        "destination_address": (ip, port),
        "ttl": ttl,
        "message": message,
    }


# create_packet :: parte de la estructura de datos anterior y retorna todo en
# bytes, concatena los 4 bytes de la ip, 2 del puerto, 1 del ttl y los del
# mensaje (header de 7 bytes fijos)
def create_packet(parsed_IP_packet: dict) -> bytes:
    ip, port = parsed_IP_packet["destination_address"]
    ttl = parsed_IP_packet["ttl"]
    message = parsed_IP_packet["message"]

    ip_bytes = bytes(int(part) for part in ip.split("."))
    port_bytes = port.to_bytes(2, "big")
    ttl_bytes = ttl.to_bytes(1, "big")

    return ip_bytes + port_bytes + ttl_bytes + message


# ip_to_in :: convierte una ip a.b.c.d en su entero de 32 bits equivalente
def ip_to_int(ip: str) -> int:
    a, b, c, d = (int(x) for x in ip.split("."))
    return (a << 24) | (b << 16) | (c << 8) | d


# last_route_index :: estado global para round-robin: por cada "área" (red + rango de puertos)
# recuerda cuántas rutas de esa área se han usado, para ir alternando
last_route_index = {}


# check_routes :: implementa lo que hace un router con su tabla, recibe el destino
# que dice el header y recorre las lineas en orden, la primera linea que matchee
# gana, y su gateway se devuelve como next hop, si ninguna matchea, devuelve None 
def check_routes(routes_file_name: str, destination_address: tuple[str, int]) -> tuple[str, int] | None:
    dest_ip, dest_port = destination_address
    dest_ip_int = ip_to_int(dest_ip)
 
    matches = []
    with open(routes_file_name) as routes_file:
        for line in routes_file:

            # los comentarios y las lineas en blanco del .txt no son rutas
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # formato: red(CIDR) puerto_inicial puerto_final ip_next_hope puerto_next_hope
            # la ip de destino pertenece a la red si los primeros bits coinciden, usamos
            # una máscara para comparar
            network, port_start, port_end, next_hop_ip, next_hop_port = line.split()
            network_ip, prefix_str = network.split("/")
            prefix = int(prefix_str)
            mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
            network_int = ip_to_int(network_ip)
            if (network_int & mask) != (dest_ip_int & mask):
                continue

            # el rango de puertos es inclusivo en ambos extremos, de esta forma
            # (8882, 8882) representa el conjunto {8882}
            if not (int(port_start) <= dest_port <= int(port_end)):
                continue

            # recolectar todas las lineas que matchean, en el orden del archivo
            matches.append({
                "area": (network, int(port_start), int(port_end)),
                "next_hop": (next_hop_ip, int(next_hop_port)),
            })

    if not matches:
        return None

    if len(matches) == 1:
        return matches[0]["next_hop"]

    # si hay mas de una ruta, son rutas de las misma área de la red, el área se
    # identifica por la linea que matcheo primero (red + rango de puertos),
    # y dentro de esa área se alterna la ruta usada (round-robin)
    area = matches[0]["area"]
    area_routes = [match["next_hop"] for match in matches if match["area"] == area]

    index = last_route_index.get(area, 0)
    last_route_index[area] = (index + 1) % len(area_routes)
    return area_routes[index]

    
def main():
    # python3 router.py router_IP router_puerto router_rutas.txt
    router_ip = sys.argv[1]
    router_port = int(sys.argv[2])
    routes_file = sys.argv[3]
    
    print(f"Router escuchando en ({router_ip}, {router_port})")
    print(f"Tabla de rutas: {routes_file}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((router_ip, router_port))

    while True:
        data, addr = sock.recvfrom(65536)  # bloqueante: se queda esperando
        parsed_packet = parse_packet(data)
        destination = parsed_packet["destination_address"]
        ttl = parsed_packet["ttl"]

        # el paquete solo se procesa si TTL > 0; si llega con TTL 0 se descarta
        if ttl == 0:
            print(f"Se recibió paquete {data!r} con TTL 0")
            continue

        # ¿el destino del header soy yo?
        if destination == (router_ip, router_port):
            print(parsed_packet["message"].decode())
            continue

        # si no es para mí, consultar la tabla y hacer forward
        next_hop = check_routes(routes_file, destination)
        if next_hop is not None:
            print(f"redirigiendo paquete {data!r} con destino final {destination} "
                  f"desde {(router_ip, router_port)} hacia {next_hop}")

            # el TTL disminuye en 1 antes del forward, y el paquete se
            # re-empaqueta con el TTL nuevo antes de salir
            parsed_packet["ttl"] -= 1
            sock.sendto(create_packet(parsed_packet), next_hop)
        else:
            print(f"No hay rutas hacia {destination} para paquete {data!r}")


if __name__ == "__main__":
    main()
