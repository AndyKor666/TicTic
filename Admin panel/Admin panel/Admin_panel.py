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
        self.root.geometry("600x450")
        self.root.configure(bg="#2b2b2b")

        btn_frame = tk.Frame(root, bg="#2b2b2b")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(btn_frame, text="Refresh", bg="#1D5300", fg="white", width=12,
                  command=self.load_users).pack(side="left", padx=5)
        tk.Button(btn_frame, text="BAN/UNBAN", bg="#530041", fg="white", width=12,
                  command=self.toggle_ban).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete User", bg="#8b0000", fg="white", width=12,
                  command=self.delete_user).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Clear Photo", bg="#b8860b", fg="white", width=12,
                  command=self.clear_photo).pack(side="left", padx=5)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#d3d3d3", foreground="black", rowheight=25, fieldbackground="#d3d3d3")
        
        self.tree = ttk.Treeview(root, columns=("login", "photo", "status"), show="headings")
        self.tree.heading("login", text="Login (Email)")
        self.tree.heading("photo", text="Photo Status")
        self.tree.heading("status", text="Access Status")
        
        self.tree.column("login", width=200)
        self.tree.column("photo", width=100, anchor="center")
        self.tree.column("status", width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.load_users()

    def get_conn(self):
        return pyodbc.connect(DB_CONF)

    def load_users(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            with self.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT Login, Photo, Banned FROM Users")
                for row in cursor.fetchall():
                    login, photo, banned = row
                    p_status = "OK :)" if photo else "NO :("
                    a_status = "BANNED >:(" if banned else "Active :)"
                    self.tree.insert("", "end", values=(login, p_status, a_status))
        except Exception as e:
            messagebox.showerror("DB Error", f"Failed to load: {e}")

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
            self.load_users()
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
                self.load_users()
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
            self.load_users()
            messagebox.showinfo("Success", "Photo cleared!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminPanel(root)
    root.mainloop()