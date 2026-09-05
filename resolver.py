import socket
from dnslib import DNSRecord, QTYPE
import sys

IP_VM = "0.0.0.0" # 192.168.1.19
PORT = 8000
BUFFER_SIZE = 4096
ROOT_IP = "198.41.0.4"

def parse_dns(data):
    msg = DNSRecord.parse(data)

    ancount = msg.header.a
    nscount = msg.header.auth
    arcount = msg.header.ar

    print(f"Dominio: {str(msg.q.qname)} | AN:{ancount} NS:{nscount} AR:{arcount}")

    for rr in msg.rr:
        print(f"  A: {rr.rname} -> {rr.rdata}")

    for rr in msg.auth:
        print(f"  NS: {rr.rname} -> {rr.rdata}")

    for rr in msg.ar:
        ip = rr.rdata
        if QTYPE.get(rr.rtype) == "A":
            print(f"  AR: {rr.rname} -> {ip}")

    return msg

def resolve(query_data, ip_addr=ROOT_IP, debug=False):
    ns_name = "."
    domain = str(parse_dns(query_data).q.qname)
    while True:
        if debug:
            print(f"(debug) Consultando '{domain}' a {ns_name} con dirección IP '{ip_addr}'")

        # a. enviar query al NS indicado
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        try:
            sock.sendto(query_data, (ip_addr, 53))
            data, _ = sock.recvfrom(BUFFER_SIZE)
        except socket.timeout:
            sock.close()
            return None
        sock.close()
        msg = parse_dns(data)

        for rr in msg.auth:
            if QTYPE.get(rr.rtype) == "NS":
                ns_name = str(rr.rdata)
                break

        # b. ¿hay registros A en Answer?
        for rr in msg.rr:
            if QTYPE.get(rr.rtype) == "A":
                return data

        # c. delegación a NS
        if msg.header.auth > 0:
            # buscar ip en additional
            next_ip = None
            for rr in msg.ar:
                if QTYPE.get(rr.rtype) == "A":
                    next_ip = str(rr.rdata)
                    break
            # si no hay, resolver el ns recursivamente
            if next_ip is None:
                for rr in msg.auth:
                    if QTYPE.get(rr.rtype) == "NS":
                        q = DNSRecord.question(ns_name)
                        ns_ip = resolve(bytes(q.pack()), ROOT_IP)
                        if ns_ip:
                            ns_msg = parse_dns(ns_ip)
                            if ns_msg.rr and QTYPE.get(ns_msg.rr[0].rtype) == "A":
                                next_ip = str(ns_msg.rr[0].rdata)
                            break
            # enviar query original al siguiente ns
            if next_ip:
                ip_addr = next_ip
                continue

        # ignorar otros tipos
        return None

history = []
cache = {}
MAX_HISTORY = 20

def top3():
    counts = {}
    for d in history:
        counts[d] = counts.get(d, 0) + 1
    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [d for d, _ in sorted_items][:3]

if __name__ == "__main__":
    debug = "--debug" in sys.argv
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP_VM, PORT))
    print(f"Escuchando en {IP_VM}:{PORT}")

    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        print(f"Mensaje recibido de {addr}:")
        msg = parse_dns(data)
        domain = str(msg.q.qname)

        if domain in cache:
            response = bytearray(cache[domain])
            response[0:2] = data[0:2]
            if debug:
                print(f"(debug) Usando caché para '{domain}'")
            sock.sendto(bytes(response), addr)
        else:
            history.append(domain)
            if len(history) > MAX_HISTORY:
                history.pop(0)
            response = resolve(data, debug=debug)
            if response:
                if domain in top3():
                    cache[domain] = response
                sock.sendto(response, addr)
