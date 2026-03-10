import socket
import threading

HOST = '127.0.0.1'
PORT = 4000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen(2)

print("--- SERVER STARTED ---")
print("Waiting for players . . .")

clients = []
symbols = ["X", "O"]
board = [" "]*9
turn = 0
lock = threading.Lock()

def broadcast(msg):
    for c in clients:
        try:
            c.send(msg.encode())
        except:
            pass

def check_winner():
    wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    for a,b,c in wins:
        if board[a] == board[b] == board[c] and board[a] != " ":
            return board[a]
    if " " not in board:
        return "DRAW"
    return None

def handle_client(conn, player):
    global turn
    conn.send(f"SYMBOL|{symbols[player]}".encode())
    while True:
        try:
            data = conn.recv(1024).decode()
            if not data:
                break
            move = int(data)
            with lock:
                if turn != player:
                    continue
                if board[move] != " ":
                    continue
                board[move] = symbols[player]
                turn = 1 - turn
                broadcast("BOARD|" + ",".join(board))
                winner = check_winner()
                if winner:
                    broadcast("WIN|" + winner)
                    break
        except:
            break
    conn.close()

while len(clients) < 2:
    conn, addr = server.accept()
    print("Player connected:", addr)
    clients.append(conn)
print("Game started . . .")

threads = []
for i in range(2):
    t = threading.Thread(target=handle_client, args=(clients[i], i))
    t.start()
    threads.append(t)

for t in threads:
    t.join()