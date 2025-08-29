# autograph.py
import io
import sys
import threading
import time
from tkinter import Frame, Label, Entry, Button
from tkinter.scrolledtext import ScrolledText
from colorama import Fore, Style

from msp import invoke_method, ticket_header  # only these two


# ===== GUI Console =====
class GUIConsole(io.StringIO):
    """Redirect stdout/stderr to a Tkinter ScrolledText widget"""
    def __init__(self, textbox):
        super().__init__()
        self.textbox = textbox

    def write(self, s):
        super().write(s)
        self.textbox.configure(state="normal")
        self.textbox.insert("end", s)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def flush(self):
        pass


# ===== Autograph Logic =====
def give_autograph(server, ticket, giver_actor_id, receiver_actor_id, session_id):
    code, resp = invoke_method(
        server,
        "MovieStarPlanet.WebService.UserSession.AMFUserSessionService.GiveAutographAndCalculateTimestamp",
        [ticket_header(ticket), giver_actor_id, receiver_actor_id],
        session_id
    )
    if code != 200:
        raise Exception(Fore.RED + f"GiveAutograph failed with HTTP code {code}")
    return resp


def get_actor_id_by_name(server, name, session_id):
    code, resp = invoke_method(
        server,
        "MovieStarPlanet.WebService.AMFActorService.GetActorIdByName",
        [name],
        session_id
    )
    if code != 200:
        raise Exception(Fore.RED + f"GetActorIdByName failed with HTTP code {code}")
    return resp


# ===== GUI Frame =====
class AutographFrame(Frame):
    COOLDOWN_SECONDS = 120  # seconds between autographs

    def __init__(self, master, session_info, back_callback=None):
        super().__init__(master, bg="black")
        self.session_info = session_info
        self.back_callback = back_callback
        self.stop_loop = False

        Label(self, text="Autograph Giver", font=("Tahoma", 16),
              bg="black", fg="white").pack(pady=10)

        # ---------- Entry Fields ----------
        Label(self, text="Target Username:", bg="black", fg="white").pack()
        self.target_entry = Entry(self)
        self.target_entry.pack(pady=4)

        # ---------- Buttons ----------
        btn_frame = Frame(self, bg="black")
        btn_frame.pack(pady=6)
        Button(btn_frame, text="Start Autograph Loop", bg="gray15", fg="white",
               command=self.start_autograph_loop).pack(side="left", padx=4)
        Button(btn_frame, text="Stop", bg="red", fg="white",
               command=self.stop_autograph_loop).pack(side="left", padx=4)
        if back_callback:
            Button(btn_frame, text="Back", bg="gray15", fg="white",
                   command=back_callback).pack(side="left", padx=4)

        # ---------- Console ----------
        self.console = ScrolledText(self, state="disabled", height=15,
                                    bg="black", fg="white", font=("Consolas", 10))
        self.console.pack(fill="both", expand=True, padx=10, pady=10)

        # Redirect stdout/stderr to console
        self.stdout_backup = sys.stdout
        self.stderr_backup = sys.stderr
        sys.stdout = GUIConsole(self.console)
        sys.stderr = GUIConsole(self.console)

    def start_autograph_loop(self):
        target_name = self.target_entry.get().strip()
        if not target_name:
            print(Fore.RED + "❌ Please enter a target username." + Style.RESET_ALL)
            return

        if not self.session_info.get("ticket"):
            print(Fore.RED + "❌ Missing session ticket. Login required." + Style.RESET_ALL)
            return

        self.stop_loop = False
        threading.Thread(target=self.autograph_loop, args=(target_name,), daemon=True).start()

    def stop_autograph_loop(self):
        self.stop_loop = True
        print(Fore.RED + "⏹️ Autograph loop stopped by user." + Style.RESET_ALL)

    def autograph_loop(self, target_name):
        acc = self.session_info
        ticket = acc["ticket"]
        session_id = acc["session_id"]
        giver_actor_id = acc["actor_id"]
        server = acc["server"]

        while not self.stop_loop:
            try:
                print(Fore.CYAN + f"\n[INFO] Fetching actor ID for {target_name}..." + Style.RESET_ALL)
                receiver_actor_id = get_actor_id_by_name(server, target_name, session_id)
                print(Fore.CYAN + f"[INFO] Sending autograph to {target_name} (Actor ID: {receiver_actor_id})..." + Style.RESET_ALL)

                response = give_autograph(server, ticket, giver_actor_id, receiver_actor_id, session_id)
                fame = response.get("Fame", None)
                if fame == 0:
                    print(Fore.RED + f"❌ Autograph sending failed for {target_name}!" + Style.RESET_ALL)
                else:
                    print(Fore.GREEN + f"✅ Autograph sent to {target_name}!" + Style.RESET_ALL)

                # ---------- Countdown ----------
                for remaining in range(self.COOLDOWN_SECONDS, 0, -1):
                    if self.stop_loop:
                        break
                    self.console.configure(state="normal")
                    # Delete previous line
                    self.console.delete("end-2l", "end-1l")
                    self.console.insert("end", Fore.LIGHTBLUE_EX + f"⏳ Next autograph in {remaining} seconds...\n" + Style.RESET_ALL)
                    self.console.see("end")
                    self.console.configure(state="disabled")
                    time.sleep(1)
                # Clear countdown line
                self.console.configure(state="normal")
                self.console.delete("end-2l", "end-1l")
                self.console.configure(state="disabled")

            except Exception as e:
                print(Fore.RED + f"❌ Error: {e}" + Style.RESET_ALL)
                self.stop_loop = True
