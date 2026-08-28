import socket
import sys
import json

HOST = '0.0.0.0' # 192.168.1.19
PORT = 8000
IMG_PATH = "/gato.png"
IMG_TYPE = "image/png"


# funciones base (parte 1)

def load_config():
    if len(sys.argv) >= 2:
        path = sys.argv[1]
    else:
        path = "config.json"
    with open(path) as f:
        return json.load(f)


def parse_HTTP_message(http_message: bytes) -> dict:
    if b"\r\n\r\n" in http_message:
        head, body = http_message.split(b"\r\n\r\n", 1)
    else:
        head, body = http_message, b""

    lines = head.split(b"\r\n")
    start_line = lines[0].decode()
    parts = start_line.split()

    msg = {"headers": {}, "body": body}

    if parts[0].startswith("HTTP"):
        msg["is_request"] = False
        msg["version"] = parts[0]
        msg["status"] = parts[1]
        msg["reason"] = start_line.split(None, 2)[2] if len(parts) > 2 else ""
    else:
        msg["is_request"] = True
        msg["method"] = parts[0]
        msg["target"] = parts[1]
        msg["version"] = parts[2]

    for line in lines[1:]:
        name, value = line.decode().split(":", 1)
        msg["headers"][name.strip()] = value.strip()

    return msg


def create_HTTP_message(msg: dict) -> bytes:
    if msg["is_request"]:
        start_line = f"{msg['method']} {msg['target']} {msg['version']}"
    else:
        start_line = f"{msg['version']} {msg['status']} {msg['reason']}"
    lines = [start_line]
    for name, value in msg["headers"].items():
        lines.append(f"{name}: {value}")

    return "\r\n".join(lines).encode() + b"\r\n\r\n" + msg["body"]


# funciones auxiliares (parte 2)

def get_destination(parsed: dict) -> tuple:
    target = parsed["target"]
    if target.startswith("http://"):
        rest = target[len("http://"):]
        authority, _, remainder = rest.partition("/")
        path = "/" + remainder
    else:
        authority = parsed["headers"].get("Host", "")
        path = target

    if ":" in authority:
        host, port = authority.rsplit(":", 1)
        return host, int(port), path

    return authority, 80, path


def is_blocked(host: str, path: str, config: dict) -> bool:
    for entry in config.get("blocked", []):
        if entry == host or entry == host + path:
            return True
    return False


def create_image_response() -> dict:
    with open(IMG_PATH.lstrip("/"), "rb") as f:
        body = f.read()
    return {
        "is_request": False,
        "version": "HTTP/1.1",
        "status": "200",
        "reason": "OK",
        "headers": {
            "Content-Type": IMG_TYPE,
            "Content-Length": str(len(body)),
            "Connection": "close",
        },
        "body": body,
    }


def create_403_response() -> dict:
    html = (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<body>\n"
        "    <h1>Error 403</h1>\n"
        f'    <img src="{IMG_PATH}"></img>\n'
        "</body>\n"
        "</html>"
    )
    body = html.encode()
    return {
        "is_request": False,
        "version": "HTTP/1.1",
        "status": "403",
        "reason": "Forbidden",
        "headers": {
            "Content-Type": "text/html; charset=utf-8",
            "Content-Length": str(len(body)),
            "Connection": "close",
        },
        "body": body,
    }


def apply_replacements(parsed_resp: dict, config: dict) -> dict:
    content_type = parsed_resp["headers"].get("Content-Type", "")
    if "text" not in content_type:
        return parsed_resp
    text = parsed_resp["body"].decode("utf-8", errors="replace")
    for pair in config.get("forbidden_words", []):
        for word, replacement in pair.items():
            text = text.replace(word, replacement)
    new_body = text.encode("utf-8")
    parsed_resp["body"] = new_body
    parsed_resp["headers"]["Content-Length"] = str(len(new_body))
    return parsed_resp


# manejo de buffers (paso 5)

def recv_full_message(sock, buffer_size=4096):
    sock.settimeout(5)
    data = b""

    # fase 1: acumular trozos hasta que los headers esten completos
    while b"\r\n\r\n" not in data:
        try:
            chunk = sock.recv(buffer_size)
        except socket.timeout:
            return data
        if not chunk:
            return data
        data += chunk

    head, _, body = data.partition(b"\r\n\r\n")
    is_request = not head.startswith(b"HTTP")

    # fase 2: buscar Content-Length
    content_length = None
    for line in head.split(b"\r\n")[1:]:
        name, _, value = line.partition(b":")
        if name.strip().lower() == b"content-length":
            content_length = int(value.strip())

    # fase 3a: con Content-Length, leer exactamente ese resto del body
    if content_length is not None:
        while len(body) < content_length:
            chunk = sock.recv(buffer_size)
            if not chunk:
                break
            data += chunk
            body = data.partition(b"\r\n\r\n")[2]
        return data

    # fase 3b: request sin Content-Length (GET/HEAD) ya esta completa
    if is_request:
        return data

    # fase 3c: response sin Content-Length, leer hasta cerrar o timeout
    while True:
        try:
            chunk = sock.recv(buffer_size)
        except socket.timeout:
            break
        if not chunk:
            break
        data += chunk
    return data


# proxy principal (parte 2)

def main():
    config = load_config()
    user = config["user"]
    print(f"Proxy iniciado con usuario: {user}")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f"Escuchando en {HOST}:{PORT}")

    while True:
        client_socket, addr = s.accept()
        print(f"Conexion desde {addr}")
        try:
            request = recv_full_message(client_socket , buffer_size=50)
            if not request:
                print(f"Conexion vacia de {addr}, cerrando")
                client_socket.close()
                continue

            parsed = parse_HTTP_message(request)
            host, port, path = get_destination(parsed)

            # paso 1: proxy transparente
            # paso 2: bloqueo de dominios
            if path == IMG_PATH:
                response = create_HTTP_message(create_image_response())
            elif is_blocked(host, path, config):
                response = create_HTTP_message(create_403_response())
            else:
                # paso 3: agregar header X-ElQuePregunta
                parsed["headers"]["X-ElQuePregunta"] = user
                
                request_to_send = create_HTTP_message(parsed)

                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_socket.connect((host, port))
                server_socket.sendall(request_to_send)

                raw_response = recv_full_message(server_socket, buffer_size=50)
                server_socket.close()

                # paso 4: reemplazar palabras prohibidas
                parsed_response = parse_HTTP_message(raw_response)
                parsed_response = apply_replacements(parsed_response, config)
                response = create_HTTP_message(parsed_response)

            print(f"Respondiendo a {addr}")
            client_socket.sendall(response)

        except Exception as e:
            print(f"Error con {addr}: {type(e).__name__}: {e}")
        finally:
            client_socket.close()


if __name__ == "__main__":
    main()
