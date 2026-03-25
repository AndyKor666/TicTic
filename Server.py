import socket
import threading
import json
import os
from cryptography.fernet import Fernet
import config
cipher = Fernet(config.FERNET_KEY)

def load_users():
    if not os.path.exists(config.USERS_FILE): return {}
    with open(config.USERS_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}
def save_users(users_dict):
    with open(config.USERS_FILE, "w") as f: json.dump(users_dict, f, indent=4)

users = load_users()
lock = threading.Lock()
waiting_conn, waiting_email = None, None

def send_secure_msg(conn, msg):
    try:
        encrypted_msg = cipher.encrypt(msg.encode()).decode()
        conn.send((encrypted_msg + "\n").encode())
    except:
        pass

class Session:
    def __init__(self, p1, p2, photo1, photo2):
        self.players = [p1, p2]
        self.symbols = ["X", "O"]
        self.board = [" "] * 9
        self.turn = 0
        send_secure_msg(p1, f"START|X|{photo1}|{photo2}")
        send_secure_msg(p2, f"START|O|{photo2}|{photo1}")
        threading.Thread(target=self.handle, args=(0,), daemon=True).start()
        threading.Thread(target=self.handle, args=(1,), daemon=True).start()

    def broadcast(self, msg):
        for p in self.players: send_secure_msg(p, msg)

    def check(self):
        w = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
        for a, b, c in w:
            if self.board[a] == self.board[b] == self.board[c] and self.board[a] != " ":
                return self.board[a]
        return "DRAW" if " " not in self.board else None

    def handle(self, i):
        conn = self.players[i]
        buffer = ""
        while True:
            try:
                data = conn.recv(16384).decode()
                if not data: break
                buffer += data
                while "\n" in buffer:
                    raw_msg, buffer = buffer.split("\n", 1)
                    msg = cipher.decrypt(raw_msg.encode()).decode()
                    if not msg.isdigit(): continue
                    move = int(msg)
                    if self.turn == i and self.board[move] == " ":
                        self.board[move] = self.symbols[i]
                        self.turn = 1 - self.turn
                        self.broadcast("BOARD|" + ",".join(self.board))
                        res = self.check()
                        if res:
                            self.broadcast("WIN|" + res)
                            return
            except:
                break
        conn.close()

def client_handler(conn):
    global waiting_conn, waiting_email, users
    email, buffer = None, ""

    while not email:
        try:
            data = conn.recv(16384).decode()
            if not data: return
            buffer += data
            while "\n" in buffer:
                raw_msg, buffer = buffer.split("\n", 1)
                msg = cipher.decrypt(raw_msg.encode()).decode()
                if msg.startswith("REGISTER"):
                    _, em, hashed_ps = msg.split("|")
                    users = load_users()
                    if em in users:
                        send_secure_msg(conn, "ERROR|Exists")
                    else:
                        users[em] = {"password": hashed_ps, "photo": "", "banned": False}
                        save_users(users)
                        send_secure_msg(conn, "OK|Registered")

                elif msg.startswith("LOGIN"):
                    _, em, hashed_ps = msg.split("|")
                    users = load_users()
                    if em in users and users[em]["password"] == hashed_ps:
                        if users[em].get("banned", False):
                            send_secure_msg(conn, "ERROR|You are banned! >:(")
                            conn.close()
                            return
                        send_secure_msg(conn, "OK|Success")
                        email = em
                    else:
                        send_secure_msg(conn, "ERROR|Fail")
        except:
            return
    if users[email]["photo"] == "":
        send_secure_msg(conn, "PHOTO_REQUIRED")
        try:
            photo_buffer = ""
            while True:
                chunk = conn.recv(16384).decode()
                if not chunk: return
                photo_buffer += chunk
                if "\n" in photo_buffer:
                    raw_photo_msg, _ = photo_buffer.split("\n", 1)
                    msg = cipher.decrypt(raw_photo_msg.encode()).decode()
                    if msg.startswith("PHOTO"):
                        _, _, img = msg.split("|", 2)
                        users[email]["photo"] = img
                        save_users(users)
                    break
        except:
            return
    with lock:
        if waiting_conn is None:
            waiting_conn, waiting_email = conn, email
            send_secure_msg(conn, "WAIT|Waiting...")
        else:
            p1_c, p1_e = waiting_conn, waiting_email
            waiting_conn, waiting_email = None, None
            Session(p1_c, conn, users[p1_e]["photo"], users[email]["photo"])

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((config.HOST, config.PORT))
    server.listen()
    print("--- SERVER RUNNING ---")
    while True:
        conn, _ = server.accept()
        threading.Thread(target=client_handler, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    start_server()