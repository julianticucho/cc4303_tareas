import SocketTCP

address = ("localhost", 8000)
mode = "go_back_n" 

# CLIENT
client_socketTCP = SocketTCP.SocketTCP()
client_socketTCP.connect(address)
# test 1
message = "Mensje de len=16".encode()
client_socketTCP.send(message, mode=mode)
# test 2
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message, mode=mode)
# test 3
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message, mode=mode)