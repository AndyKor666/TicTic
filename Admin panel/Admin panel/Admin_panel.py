import tkinter as tk
from tkinter import ttk, messagebox
import pyodbc
import os
import sys

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_path not in sys.path:
    sys.path.append(root_path)

try:
    import config
    from security import encrypt_msg, decrypt_msg
except ImportError:
    messagebox.showerror("Error", "Could not find config.py")
    sys.exit()

DB_CONF = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-DOGCDD4\\SQLEXPRESS;DATABASE=AuthSystemDB;Trusted_Connection=yes'

class AdminPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("ADMIN PANEL")
        self.root.geometry("600x600")
        self.root.configure(bg="#2b2b2b")
        self.search_var = tk.StringVar()

        search_frame = tk.Frame(root, bg="#2b2b2b")
        search_frame.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(search_frame, text="Search by Login:", bg="#2b2b2b", fg="white").pack(side="left")
        
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=67)
        search_entry.pack(side="left", padx=10)
        search_entry.bind("<Return>", lambda event: self.perform_search())
        
        tk.Button(search_frame, text="Find", bg="#000956", fg="white", width=7,
                  command=self.perform_search).pack(side="left")

        btn_frame = tk.Frame(root, bg="#2b2b2b")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(btn_frame, text="Refresh", bg="#1D5300", fg="white", width=12,
                  command=self.refresh_users).pack(side="left", padx=5)
        tk.Button(btn_frame, text="BAN/UNBAN", bg="#530041", fg="white", width=12,
                  command=self.toggle_ban).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete User", bg="#8b0000", fg="white", width=12,
                  command=self.delete_user).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Clear Photo", bg="#b8860b", fg="white", width=12,
                  command=self.clear_photo).pack(side="left", padx=5)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#d3d3d3", foreground="black", rowheight=25, fieldbackground="#d3d3d3")
        style.map('Treeview', background=[('selected', '#347083')])

        self.tree = ttk.Treeview(root, columns=("login", "photo", "status"), show="headings", height=10)
        self.tree.heading("login", text="Login (Email)")
        self.tree.heading("photo", text="Photo Status")
        self.tree.heading("status", text="Access Status")
        
        self.tree.column("login", width=200)
        self.tree.column("photo", width=100, anchor="center")
        self.tree.column("status", width=120, anchor="center")
        self.tree.pack(fill="x", padx=10, pady=(0, 10))
        self.tree.bind("<<TreeviewSelect>>", self.on_user_select)

        tk.Label(root, text="Match History (Selected User):", bg="#2b2b2b", fg="white").pack(anchor="w", padx=10)
        
        self.history_tree = ttk.Treeview(root, columns=("id", "date", "opponent", "result"), show="headings", height=8)
        self.history_tree.heading("id", text="ID")
        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("opponent", text="Opponent")
        self.history_tree.heading("result", text="Result")

        self.history_tree.column("id", width=50, anchor="center")
        self.history_tree.column("date", width=150, anchor="center")
        self.history_tree.column("opponent", width=150, anchor="center")
        self.history_tree.column("result", width=100, anchor="center")
        self.history_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.load_users()

    def get_conn(self):
        return pyodbc.connect(DB_CONF)

    def on_user_select(self, event):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
            
        selected = self.tree.selection()
        if not selected:
            return
            
        login = self.tree.item(selected[0])['values'][0]

        try:
            with self.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT Id, MatchDate, Player1, Player2, Result 
                    FROM Matches 
                    WHERE Player1=? OR Player2=? 
                    ORDER BY Id DESC
                """, (login, login))
                
                for row in cursor.fetchall():
                    m_id, m_date, p1, p2, result = row
                    opponent = p2 if p1 == login else p1
                    if result == "DRAW":
                        user_result = "Draw"
                    elif result == login:
                        user_result = "WIN"
                    else:
                        user_result = "LOSS"
                    date_str = str(m_date).split('.')[0] if m_date else "N/A"
                    
                    self.history_tree.insert("", "end", values=(m_id, date_str, opponent, user_result))
                    
        except pyodbc.Error as e:
            pass 

    def load_users(self, search_query=""):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
            
        try:
            with self.get_conn() as conn:
                cursor = conn.cursor()
                if search_query:
                    cursor.execute("SELECT Login, Photo, Banned FROM Users WHERE Login LIKE ?", (f"%{search_query}%",))
                else:
                    cursor.execute("SELECT Login, Photo, Banned FROM Users")
                    
                for row in cursor.fetchall():
                    login, photo, banned = row
                    p_status = "OK :)" if photo else "NO :("
                    a_status = "BANNED >:(" if banned else "Active :)"
                    self.tree.insert("", "end", values=(login, p_status, a_status))

        except Exception as e:
            messagebox.showerror("DB Error", f"Failed to load: {e}")

    def perform_search(self):
        query = self.search_var.get().strip()
        self.load_users(query)

    def refresh_users(self):
        self.search_var.set("")
        self.load_users()

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
            messagebox.showinfo("Success", f"User {login} status updated . . .")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_user(self):
        login = self.get_selected_login()
        if not login: return
        if messagebox.askyesno("Confirm", f"Delete {login} FOREVER?"):
            try:
                with self.get_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM Users WHERE Login=?", (login,))
                    conn.commit()
                self.perform_search()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def clear_photo(self):
        login = self.get_selected_login()
        if not login: return
        try:
            with self.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE Users SET Photo=NULL WHERE Login=?", (login,))
                conn.commit()
            self.perform_search()
            messagebox.showinfo("Success", "Photo cleared!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminPanel(root)
    root.mainloop()