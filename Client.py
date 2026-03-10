import socket
import threading
import tkinter as tk
from tkinter import messagebox

HOST = '127.0.0.1'
PORT = 4000

class TicTic:
    def __init__(self, root):
        self.root = root
        self.root.title("TicTic")
        self.root.geometry("250x250")
        self.root.configure(bg="#F0F0F0")
        frame = tk.Frame(root, bd=2, relief="groove", bg="#F0F0F0")
        frame.pack(padx=10, pady=10)
        self.info = tk.Label(frame, text="Connecting . . .", bg="#F0F0F0")
        self.info.grid(row=0, column=0, columnspan=3)
        self.buttons = []

        for i in range(9):

            btn = tk.Button(
                frame,
                text=" ",
                width=6,
                height=3,
                command=lambda i=i: self.send_move(i)
            )
            btn.grid(row=i//3 + 1, column=i % 3)
            self.buttons.append(btn)
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((HOST, PORT))
        except:
            messagebox.showerror("Error", "Server is not running")
            root.destroy()
            return
        threading.Thread(target=self.receive, daemon=True).start()

    def send_move(self, pos):
        try:
            self.client.send(str(pos).encode())
        except:
            pass

    def receive(self):
        while True:
            try:
                data = self.client.recv(1024).decode()
                if not data:
                    break
                if data.startswith("SYMBOL"):
                    symbol = data.split("|")[1]
                    self.root.after(
                        0,
                        lambda: self.info.config(text=f"You are {symbol}")
                    )
                elif data.startswith("BOARD"):
                    board = data.split("|")[1].split(",")
                    for i in range(9):
                        self.root.after(
                            0,
                            lambda i=i: self.buttons[i].config(text=board[i])
                        )
                elif data.startswith("WIN"):
                    winner = data.split("|")[1]
                    if winner == "DRAW":
                        msg = "Draw!"
                    else:
                        msg = f"{winner} wins!"
                    self.root.after(
                        0,
                        lambda: messagebox.showinfo("Game Over", msg)
                    )
                    break
            except:
                break
root = tk.Tk()
TicTic(root)
root.mainloop()