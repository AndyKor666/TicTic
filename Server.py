import socket
import threading

HOST = '127.0.0.1'
PORT = 4000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

print("--- SERVER STARTED ---")
print("Waiting for players . . .")
waiting_player = None
lock = threading.Lock()

class Session:
    def __init__(self, p1, p2):
        self.players = [p1, p2]
        self.symbols = ["X", "O"]
        self.board = [" "]*9
        self.turn = 0
        self.session_lock = threading.Lock()
        print("New session created . . .")
        for i in range(2):
            self.players[i].send(f"SYMBOL|{self.symbols[i]}".encode())
        threading.Thread(target=self.handle_player, args=(0,), daemon=True).start()
        threading.Thread(target=self.handle_player, args=(1,), daemon=True).start()

    def broadcast(self, msg):
        for p in self.players:
            try:
                p.send(msg.encode())
            except:
                pass

    def check_winner(self):
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        for a,b,c in wins:
            if self.board[a] == self.board[b] == self.board[c] and self.board[a] != " ":
                return self.board[a]
        if " " not in self.board:
            return "DRAW"
        return None

    def handle_player(self, player):
        conn = self.players[player]
        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break
                move = int(data)
                with self.session_lock:
                    if self.turn != player:
                        continue
                    if self.board[move] != " ":
                        continue
                    self.board[move] = self.symbols[player]
                    self.turn = 1 - self.turn
                    self.broadcast("BOARD|" + ",".join(self.board))
                    winner = self.check_winner()
                    if winner:
                        self.broadcast("WIN|" + winner)
                        break
            except:
                break
        conn.close()

def accept_players():
    global waiting_player
    while True:
        conn, addr = server.accept()
        print("Player connected :)", addr)
        with lock:
            if waiting_player is None:
                waiting_player = conn
                conn.send("INFO|Waiting for opponent . . .".encode())
            else:
                Session(waiting_player, conn)
                waiting_player = None

accept_players()