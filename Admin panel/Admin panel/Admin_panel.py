import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_path not in sys.path:
    sys.path.append(root_path)
try:
    import config

except ImportError:
    messagebox.showerror("Error", f"Could not find config.py at {root_path}")
    sys.exit()

class AdminPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("ADMIN PANEL")
        self.root.geometry("560x450")
        self.root.configure(bg="#2b2b2b")
        self.db_path = os.path.join(root_path, config.USERS_FILE)
        self.users = {}

 
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
        style.map('Treeview', background=[('selected', '#347083')])
        columns = ("email", "password", "photo_status", "status")
        self.tree = ttk.Treeview(root, columns=columns, show="headings")
        self.tree.heading("email", text="Email (Login)")
        self.tree.heading("password", text="Password Hash")
        self.tree.heading("photo_status", text="Photo")
        self.tree.heading("status", text="Access Status")
        self.tree.column("email", width=150)
        self.tree.column("password", width=180)
        self.tree.column("photo_status", width=100, anchor="center")
        self.tree.column("status", width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.load_users()

    def load_users(self):
       
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not os.path.exists(self.db_path):
            return
        try:
            with open(self.db_path, "r") as f:
                self.users = json.load(f)
        except (json.JSONDecodeError, Exception):
            self.users = {}

        for email, data in self.users.items():
            photo_status = "OK" if data.get("photo") else "No"
            is_banned = data.get("banned", False)
            access_text = "BANNED" if is_banned else "Active"
            pw_hash = (data.get("password", "")[:15] + "...") if data.get("password") else "N/A"
            
            self.tree.insert("", "end", values=(email, pw_hash, photo_status, access_text))

    def save_users(self):
        try:
            with open(self.db_path, "w") as f:
                json.dump(self.users, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save database: {e}")

    def get_selected_email(self):
       
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection", "Please select a user from the list first!")
            return None
        return self.tree.item(selected[0])['values'][0]

    def toggle_ban(self):
        email = self.get_selected_email()
        if not email: return
        
        if email in self.users:
            current_status = self.users[email].get("banned", False)
            self.users[email]["banned"] = not current_status
            self.save_users()
            self.load_users()
            
            new_status = "BANNED" if not current_status else "UNBANNED"
            messagebox.showinfo("Success", f"User {email} is now {new_status}")

    def delete_user(self):
        email = self.get_selected_email()
        if not email: return
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {email}?"):
            if email in self.users:
                del self.users[email]
                self.save_users()
                self.load_users()

    def clear_photo(self):
        email = self.get_selected_email()
        if not email: return
        if email in self.users:
            self.users[email]["photo"] = ""
            self.save_users()
            self.load_users()
            messagebox.showinfo("Success", f"Photo for {email} has been cleared.")

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminPanel(root)
    root.mainloop()