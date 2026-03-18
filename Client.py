import socket
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
import base64
from PIL import Image, ImageTk
import io

HOST = '127.0.0.1'
PORT = 4000

class TicTic:
    def __init__(self, root):
        self.root = root
        self.root.title("TicTic")
        self.root.geometry("300x200")
        self.root.configure(bg="#d4d0c8")
        self.symbol = None
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((HOST, PORT))
        except:
            messagebox.showerror("Error", "Server offline")
            root.destroy()
            return

        self.login_ui()
        threading.Thread(target=self.receive, daemon=True).start()

    def send_msg(self, msg):
        try:
            self.client.send((msg + "\n").encode())
        except:
            pass

    def clear(self):
        for w in self.root.winfo_children(): w.destroy()

    def login(self):
        email = self.e.get().strip()
        password = self.p.get().strip()

        if not email or not password:
            messagebox.showwarning("ACHTUNG!", "Please, fill this form . . .")
            return
        self.send_msg(f"LOGIN|{email}|{password}")

    def register(self):
        email = self.e.get().strip()
        password = self.p.get().strip()

        if not email or not password:
            messagebox.showwarning("ACHTUNG!", "Please, fill this form . . .")
            return

        self.send_msg(f"REGISTER|{email}|{password}")

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

    def game_ui(self):
        self.clear()
        self.root.geometry("320x400")
        top_frame = tk.Frame(self.root, bg="#d4d0c8")
        top_frame.pack(fill="x", pady=10, padx=10)
        try:
            my_data = base64.b64decode(self.my_photo_b64)
            my_img = Image.open(io.BytesIO(my_data))

            self.win_icon = ImageTk.PhotoImage(my_img)
            self.root.iconphoto(False, self.win_icon)

            my_img_resized = my_img.resize((50, 50))
            self.my_tk = ImageTk.PhotoImage(my_img_resized)
            tk.Label(top_frame, image=self.my_tk, bg="#d4d0c8").pack(side="left")
        except:
            pass

        self.info = tk.Label(top_frame, text=f"YOU ARE {self.symbol}", bg="#d4d0c8", font=("Tahoma", 12, "bold"))
        self.info.pack(side="left", expand=True)

        try:
            opp_data = base64.b64decode(self.opp_photo_b64)
            opp_img_resized = Image.open(io.BytesIO(opp_data)).resize((50, 50))
            self.opp_tk = ImageTk.PhotoImage(opp_img_resized)
            tk.Label(top_frame, image=self.opp_tk, bg="#d4d0c8").pack(side="right")
        except:
            pass
        f = tk.Frame(self.root, bg="#d4d0c8")
        f.pack(pady=10)
        self.btns = []
        for i in range(9):
            b = tk.Button(f, text=" ", width=6, height=3, font=("Tahoma", 14, "bold"),
                          relief="raised", command=lambda idx=i: self.send_msg(str(idx)))
            b.grid(row=i // 3, column=i % 3)
            self.btns.append(b)

    def receive(self):
        buffer = ""
        while True:
            try:
                data = self.client.recv(4096).decode()
                if not data: break
                buffer += data

                while "\n" in buffer:
                    msg, buffer = buffer.split("\n", 1)
                    if not msg: continue

                    if msg == "PHOTO_REQUIRED":
                        self.root.after(0, self.send_photo)
                    elif msg.startswith("START"):
                        _, sym, my_p, opp_p = msg.split("|", 3)
                        self.symbol = sym
                        self.my_photo_b64 = my_p
                        self.opp_photo_b64 = opp_p
                        self.root.after(0, self.game_ui)
                    elif msg.startswith("BOARD"):
                        b_data = msg.split("|")[1].split(",")
                        self.root.after(0, lambda bd=b_data: self.update_board(bd))
                    elif msg.startswith("WIN"):
                        w = msg.split("|")[1]
                        res = "Draw . . ." if w == "DRAW" else f"{w} WINS :)"
                        self.root.after(0, lambda r=res: messagebox.showinfo("GAME OVER :(", r))
                    elif msg.startswith("ERROR"):
                        messagebox.showerror("ERR . . .", msg.split("|")[1])
            except Exception as e:
                print("Disconnect:", e)
                break

    def send_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg")])
        if path:
            with open(path, "rb") as f:
                img = base64.b64encode(f.read()).decode()
            self.send_msg(f"PHOTO|{self.e.get()}|{img}")

    def update_board(self, board):
        for i in range(9): self.btns[i].config(text=board[i])

root = tk.Tk()
TicTic(root)
root.mainloop()