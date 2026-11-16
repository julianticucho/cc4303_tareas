import sys
import socket


# parse_packet :: toma el paquete en bytes, lo corta, y lo convierte en un
# diccionario de python manejable, el header de 18 bytes fijos se corta campo
# por campo y el mensaje es el resto del paquete
def parse_packet(IP_packet: bytes):
    ip_bytes = IP_packet[:4]
    port_bytes = IP_packet[4:6]
    ttl_bytes = IP_packet[6:7]
    id_bytes = IP_packet[7:9]
    offset_bytes = IP_packet[9:13]
    size_bytes = IP_packet[13:17]
    flag_bytes = IP_packet[17:18]
    message = IP_packet[18:]

    ip = ".".join(str(b) for b in ip_bytes)
    port = int.from_bytes(port_bytes, "big")
    ttl = int.from_bytes(ttl_bytes, "big")
    packet_id = int.from_bytes(id_bytes, "big")
    offset = int.from_bytes(offset_bytes, "big")
    size = int.from_bytes(size_bytes, "big")
    flag = int.from_bytes(flag_bytes, "big")

    return {
        "destination_address": (ip, port),
        "ttl": ttl,
        "id": packet_id,
        "offset": offset,
        "size": size,
        "flag": flag,
        "message": message,
    }


# create_packet :: parte de la estructura de datos anterior y retorna todo en
# bytes, concatena los 18 bytes de header y los del mensaje
def create_packet(parsed_IP_packet: dict) -> bytes:
    ip, port = parsed_IP_packet["destination_address"]
    ttl = parsed_IP_packet["ttl"]
    packet_id = parsed_IP_packet["id"]
    offset = parsed_IP_packet["offset"]
    size = parsed_IP_packet["size"]
    flag = parsed_IP_packet["flag"]
    message = parsed_IP_packet["message"]

    ip_bytes = bytes(int(part) for part in ip.split("."))
    port_bytes = port.to_bytes(2, "big")
    ttl_bytes = ttl.to_bytes(1, "big")
    id_bytes = packet_id.to_bytes(2, "big")
    offset_bytes = offset.to_bytes(4, "big")
    size_bytes = size.to_bytes(4, "big")
    flag_bytes = flag.to_bytes(1, "big")

    return ip_bytes + port_bytes + ttl_bytes + id_bytes + offset_bytes + size_bytes + flag_bytes + message


# ip_to_in :: convierte una ip a.b.c.d en su entero de 32 bits equivalente
def ip_to_int(ip: str) -> int:
    a, b, c, d = (int(x) for x in ip.split("."))
    return (a << 24) | (b << 16) | (c << 8) | d


# last_route_index :: estado global para round-robin: por cada "área" (red + rango de puertos)
# recuerda cuántas rutas de esa área se han usado, para ir alternando
last_route_index = {}


# check_routes :: implementa lo que hace un router con su tabla, recibe el destino
# que dice el header y recorre las lineas en orden, la primera linea que matchee
# gana, y devuelve el next hop junto con el MTU del enlace hacia el. Si ninguna
# matchea, devuelve None
def check_routes(routes_file_name: str, destination_address: tuple[str, int]) -> tuple[tuple[str, int], int] | None:
    dest_ip, dest_port = destination_address
    dest_ip_int = ip_to_int(dest_ip)

    matches = []
    with open(routes_file_name) as routes_file:
        for line in routes_file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # formato: red(CIDR) puerto_inicial puerto_final ip_next_hop puerto_next_hop [MTU]
            # el MTU es el sexto campo; si la linea no lo trae se asume un enlace sin 
            # restriccion de tamaño
            fields = line.split()
            network, port_start, port_end, next_hop_ip, next_hop_port = fields[:5]
            if len(fields) >= 6:
                link_mtu = int(fields[5])
            else:
                link_mtu = 65535

            # la ip de destino pertenece a la red si los primeros bits coinciden
            network_ip, prefix_str = network.split("/")
            prefix = int(prefix_str)
            mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF

            network_int = ip_to_int(network_ip)
            if (network_int & mask) != (dest_ip_int & mask):
                continue

            # el rango de puertos es inclusivo en ambos extremos
            if not (int(port_start) <= dest_port <= int(port_end)):
                continue

            matches.append({
                "area": (network, int(port_start), int(port_end)),
                "next_hop": (next_hop_ip, int(next_hop_port)),
                "mtu": link_mtu,
            })

    if not matches:
        return None

    if len(matches) == 1:
        return (matches[0]["next_hop"], matches[0]["mtu"])

    # round-robin por area, igual que antes, pero el elegido ahora viaja
    # acompañado del MTU de su enlace
    area = matches[0]["area"]
    area_routes = [match for match in matches if match["area"] == area]

    index = last_route_index.get(area, 0)
    last_route_index[area] = (index + 1) % len(area_routes)
    chosen = area_routes[index]
    return (chosen["next_hop"], chosen["mtu"])


# tamano en bytes del header de 18 bytes fijos
HEADER_SIZE = 18


# fragment_IP_packet :: fragmenta un datagrama IP para que quepa por un enlace
# de MTU bytes. Si el paquete completo cabe, retorna una lista con el paquete ,
# si no, corta el mensaje en trozos de MTU - HEADER_SIZE bytes y retorna un 
# fragmento por trozo, con offset, tamaño y flag, y el id y ttl heredados del 
# original
def fragment_IP_packet(IP_packet: bytes, MTU: int) -> list[bytes]:
    if len(IP_packet) <= MTU:
        return [IP_packet]

    parsed = parse_packet(IP_packet)
    message = parsed["message"]
    chunk_size = MTU - HEADER_SIZE

    fragments = []
    sent = 0
    while sent < len(message):
        chunk = message[sent:sent + chunk_size]
        fragment = {
            "destination_address": parsed["destination_address"],
            "ttl": parsed["ttl"],
            "id": parsed["id"],
            "offset": parsed["offset"] + sent,
            "size": len(chunk),
            "flag": parsed["flag"] if sent + len(chunk) == len(message) else 1,
            "message": chunk,
        }
        fragments.append(create_packet(fragment))
        sent += len(chunk)

    return fragments


# reassemble_IP_packet :: re-ensambla un datagrama IP a partir de una lista de
# sus fragmentos. Ordena la lista por offset, verifica que no falte ningun
# trozo y retorna el paquete reconstruido con offset 0 y flag 0. Si la lista 
# esta incompleta retorna None
def reassemble_IP_packet(fragment_list: list[bytes]) -> bytes | None:
    if not fragment_list:
        return None

    fragments = sorted((parse_packet(fragment) for fragment in fragment_list), key=lambda p: p["offset"])

    # un solo elemento: o es el paquete completo sin fragmentar (offset 0 y
    # flag 0), o es un fragmento suelto de una lista incompleta
    if len(fragments) == 1:
        only = fragments[0]
        if only["offset"] == 0 and only["flag"] == 0:
            return fragment_list[0]
        return None

    message = b""
    for i, fragment in enumerate(fragments):
        # sin huecos ni repeticiones: cada fragmento debe empezar justo donde
        # termina lo acumulado hasta ahora
        if fragment["offset"] != len(message):
            return None

        message += fragment["message"]

        # todos los fragmentos menos el ultimo traen flag 1, el ultimo flag 0
        expected_flag = 0 if i == len(fragments) - 1 else 1
        if fragment["flag"] != expected_flag:
            return None

    rebuilt = {
        "destination_address": fragments[0]["destination_address"],
        "ttl": fragments[0]["ttl"],
        "id": fragments[0]["id"],
        "offset": 0,
        "size": len(message),
        "flag": 0,
        "message": message,
    }
    return create_packet(rebuilt)

    
def main():
    # python3 router.py router_IP router_puerto router_rutas.txt
    router_ip = sys.argv[1]
    router_port = int(sys.argv[2])
    routes_file = sys.argv[3]
    
    print(f"Router escuchando en ({router_ip}, {router_port})")
    print(f"Tabla de rutas: {routes_file}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((router_ip, router_port))

    # diccionario de re-ensamblado: por cada ID de datagrama, la lista de
    # fragmentos recibidos hasta ahora que estan destinados a este router
    received_fragments = {}

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
            packet_id = parsed_packet["id"]

            # guardar el fragmento en la lista de su ID, ignorando duplicados
            # con el mismo offset que ya esten en la lista
            fragments = received_fragments.setdefault(packet_id, [])
            if not any(parse_packet(fragment)["offset"] == parsed_packet["offset"] for fragment in fragments):
                fragments.append(data)

            # en cada llegada se intenta re-ensamblar la lista del ID
            assembled = reassemble_IP_packet(fragments)
            if assembled is not None:
                print(parse_packet(assembled)["message"].decode())
                del received_fragments[packet_id]
            continue

        # si no es para mí, consultar la tabla y hacer forward
        route = check_routes(routes_file, destination)
        if route is not None:
            next_hop, link_mtu = route

            print(f"redirigiendo paquete {data!r} con destino final {destination} "
                  f"desde {(router_ip, router_port)} hacia {next_hop}")

            # el TTL disminuye en 1 antes del forward, una vez por salto sin
            # importar en cuantos fragmentos se parta el paquete
            parsed_packet["ttl"] -= 1
            original_packet = create_packet(parsed_packet)

            # el paquete se fragmenta segun el MTU del enlace hacia el next
            # hop, y se envian todos los fragmentos de la lista
            fragments = fragment_IP_packet(original_packet, link_mtu)
            if len(fragments) > 1:
                print(f"fragmentando paquete de {len(original_packet)} bytes "
                      f"en {len(fragments)} fragmentos por enlace con MTU {link_mtu}")
            for fragment in fragments:
                sock.sendto(fragment, next_hop)
        else:
            print(f"No hay rutas hacia {destination} para paquete {data!r}")


if __name__ == "__main__":
    main()
