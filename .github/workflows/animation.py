# animation.py
import tkinter as tk
from tkinter import messagebox
import threading
from msp import invoke_method, ticket_header
from login_helper import login_user_ticket  # reuse existing login logic


class AnimationFrame(tk.Frame):
    def __init__(self, master, session_info=None, account_info=None, back_callback=None):
        """
        session_info: dict with keys 'ticket', 'actor_id', 'session_id', 'server' (optional)
        account_info: dict with keys 'username', 'password', 'server' (optional if session_info exists)
        """
        super().__init__(master, bg="black")
        self.master = master
        self.back_callback = back_callback
        self.session_info = session_info or {}
        self.account_info = account_info

        tk.Label(self, text="Animation Purchaser", font=("Tahoma", 16), bg="black", fg="cyan").pack(pady=10)

        form_frame = tk.Frame(self, bg="black")
        form_frame.pack(pady=20)

        tk.Label(form_frame, text="Animation ID:", bg="black", fg="white", font=("Tahoma", 12)).grid(row=0, column=0, padx=5, pady=5)
        self.animation_entry = tk.Entry(form_frame, font=("Tahoma", 12))
        self.animation_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Button(self, text="Purchase Animation", bg="green", fg="white",
                  command=self.start_purchase_thread).pack(pady=10)
        tk.Button(self, text="Back", bg="gray15", fg="white",
                  command=self.go_back).pack(pady=5)

        self.ensure_login()

    def ensure_login(self):
        """Ensures session_info is filled either from session_info or account_info."""
        if self.session_info.get("ticket") and self.session_info.get("actor_id") and self.session_info.get("session_id"):
            print(f"[ANIM DEBUG] Using existing session_info: {self.session_info}")
            return  # already logged in

        if not self.account_info:
            messagebox.showerror("Error", "No account info or session info provided for AnimationFrame.")
            return

        username = self.account_info.get("username")
        password = self.account_info.get("password")
        server = self.account_info.get("server", "US")

        if not username or not password:
            messagebox.showerror("Error", "Username or password missing!")
            return

        print(f"[ANIM DEBUG] Logging in with username/password...")
        ticket, actor_id, session_id = login_user_ticket(username, password, server)
        if not ticket:
            messagebox.showerror("Login Failed", f"Cannot login {username} ({server})")
            return

        self.session_info = {
            "server": server.lower(),
            "actor_id": str(actor_id),
            "ticket": ticket,         # raw ticket
            "session_id": session_id
        }
        print(f"[ANIM DEBUG] Login succeeded: {self.session_info}")

    def start_purchase_thread(self):
        t = threading.Thread(target=self.purchase_animation)
        t.daemon = True
        t.start()

    def purchase_animation(self):
        anim_id_str = self.animation_entry.get().strip()
        if not anim_id_str.isdigit():
            messagebox.showerror("Invalid Input", "Animation ID must be a number.")
            return
        animation_id = int(anim_id_str)

        if not self.session_info:
            messagebox.showerror("Error", "No valid session found.")
            return

        SERVER = self.session_info["server"]
        ticket = self.session_info["ticket"]
        actor_id = self.session_info["actor_id"]
        session_id = self.session_info["session_id"]

        print(f"[ANIM DEBUG] About to call BuyAnimation with:")
        print(f"[ANIM DEBUG]   server={SERVER}, actor_id={actor_id}, animation_id={animation_id}, session_id={session_id}")
        print(f"[ANIM DEBUG]   ticket (len)={len(ticket)}, sample={ticket[:30]}...")

        try:
            # ✅ Use ticket_header to wrap the ticket properly
            code, response = invoke_method(
                SERVER,
                "MovieStarPlanet.WebService.Spending.AMFSpendingService.BuyAnimation",
                [ticket_header(ticket), actor_id, animation_id],
                session_id
            )

            if code == 200 and isinstance(response, dict):
                desc = response.get("Description", "")
                if desc == "VIP_ANIMATION":
                    messagebox.showerror("Purchase Failed", "Animation requires VIP membership.")
                elif response.get("Data"):
                    messagebox.showinfo("Success", f"Animation {animation_id} successfully purchased!")
                else:
                    messagebox.showwarning("Warning", "Purchase request completed, but no confirmation received.")
            else:
                desc = response.get('Description') if isinstance(response, dict) else str(response)
                messagebox.showerror("Error", f"Failed to buy animation.\nStatus: {code}\nDescription: {desc}")
        except Exception as e:
            messagebox.showerror("Error", f"Exception during BuyAnimation: {e}")

    def go_back(self):
        if self.back_callback:
            self.back_callback()


# ----------------- Standalone Test -----------------
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("400x200")

    # Example usage: either provide session_info or account_info
    # session_info = {
    #     "ticket": "GB,...",
    #     "actor_id": "54350735",
    #     "session_id": "ODI5NzczNGVm...",
    #     "server": "gb"
    # }
    account_info = {"username": "YourUsername", "password": "YourPassword", "server": "GB"}

    frame = AnimationFrame(root, account_info=account_info)
    frame.pack(fill="both", expand=True)
    root.mainloop()
