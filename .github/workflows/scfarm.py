import os
import time
import threading
import glob
from datetime import datetime
from tkinter import Frame, Button, Label
from tkinter.scrolledtext import ScrolledText
from colorama import Fore, Style
from pyamf.remoting import ErrorFault
from msp import invoke_method, ticket_header
import pytz  # For timezone handling


def get_app_data_dir():
    """Cross-platform directory for storing app data."""
    if os.name == "nt":
        base_dir = os.getenv("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:  # Linux / others
        base_dir = os.path.join(os.path.expanduser("~"), ".local", "share")
    app_dir = os.path.join(base_dir, "StarKey")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


class SCFarm:
    def __init__(self, session_info, log_callback=None):
        """
        session_info: dict with ticket, actor_id, username, server, session_id
        log_callback: function to receive log messages (str)
        """
        self.session_info = session_info
        self.log_callback = log_callback or print
        self.stop_loop = False
        self.petted = set()
        self.progress_file = self.get_progress_file()

        # Load today's petted bonsters
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, "r") as f:
                    self.petted = set(int(line.strip()) for line in f if line.strip().isdigit())
            except Exception as e:
                self.log(f"[WARN] Failed to read progress file: {e}")
                self.petted = set()

    # ----------------- Utility -----------------
    def log(self, message):
        self.log_callback(message)

    def get_progress_file(self):
        """
        Generate a progress file name based on the username, and date.
        """
        appdata_dir = get_app_data_dir()

        # Retrieve username from session_info, fallback to actor_id
        username = self.session_info.get("username") or str(self.session_info.get("actor_id", "unknown_user"))

        # Current UTC date
        now = datetime.now(pytz.timezone("UTC"))
        formatted_date = now.strftime("%Y-%m-%d")

        # Build filename
        filename = f"{username}_bonsterids_{formatted_date}.txt"
        progress_file_path = os.path.join(appdata_dir, filename)

        # Remove old progress files (not today's)
        for old_file in glob.glob(os.path.join(appdata_dir, f"{username}_bonsterids_*.txt")):
            if old_file != progress_file_path:
                try:
                    os.remove(old_file)
                except Exception as e:
                    self.log(f"Failed to remove old file {old_file}: {e}")

        return progress_file_path

    def clean_name(self, name):
        return name.replace('\x1d', '').replace('\x1f', '')

    # ----------------- API Methods -----------------
    def import_highscore_bonsters(self, pageindex=0, pagesize=7):
        user_data = self.session_info
        endpoint = "MovieStarPlanet.WebService.Highscore.AMFHighscoreService.GetHighscoreBonster"
        params = [
            ticket_header(user_data["ticket"]),
            user_data["actor_id"],
            True,
            True,
            "EXPERIENCE",
            pageindex,
            pagesize
        ]
        try:
            code, resp = invoke_method(user_data["server"], endpoint, params, session_id=user_data.get("session_id"))
        except Exception as e:
            self.log(f"{Fore.RED}Error fetching highscore: {e}{Style.RESET_ALL}")
            return None

        if code != 200 or isinstance(resp, ErrorFault):
            self.log(f"{Fore.RED}Failed to fetch highscore, HTTP {code}{Style.RESET_ALL}")
            return None

        return resp.get("items", [])

    def pet_bonster(self, actorBonsterRelId):
        user_data = self.session_info
        endpoint = "MovieStarPlanet.WebService.Bonster.AMFBonsterService.PetFriendBonster"
        params = [ticket_header(user_data["ticket"]), user_data["actor_id"], actorBonsterRelId]
        try:
            code, resp = invoke_method(user_data["server"], endpoint, params, session_id=user_data.get("session_id"))
        except Exception as e:
            self.log(f"{Fore.RED}Error petting bonster {actorBonsterRelId}: {e}{Style.RESET_ALL}")
            return False

        if code == 200:
            self.log(f"{Fore.GREEN}✅ Pet sent to Bonster {actorBonsterRelId}{Style.RESET_ALL}")
            try:
                with open(self.progress_file, "a") as f:
                    f.write(f"{actorBonsterRelId}\n")
            except Exception as e:
                self.log(f"[WARN] Failed to write to progress file: {e}")
            self.petted.add(actorBonsterRelId)
            return True
        else:
            self.log(f"{Fore.RED}Failed to pet Bonster {actorBonsterRelId}, HTTP {code}{Style.RESET_ALL}")
            return False

    # ----------------- Auto-Pet Loop -----------------
    def start_auto_pet(self, short_delay=5, long_cooldown=60, max_requests_before_cooldown=50):
        if getattr(self, "thread", None) and self.thread.is_alive():
            self.log("[INFO] Auto-pet is already running.")
            return
        self.stop_loop = False
        self.thread = threading.Thread(target=self._auto_pet_loop, args=(short_delay, long_cooldown, max_requests_before_cooldown), daemon=True)
        self.thread.start()
        self.log("[INFO] Auto-pet started.")

    def stop_auto_pet(self):
        self.stop_loop = True
        self.log("[INFO] Auto-pet stopped by user.")

    def _auto_pet_loop(self, short_delay, long_cooldown, max_requests_before_cooldown):
        pageindex = 0
        pagesize = 7
        request_count = 0

        while not self.stop_loop:
            items = self.import_highscore_bonsters(pageindex=pageindex, pagesize=pagesize)
            if not items:
                self.log("No bonsters found on this page. Waiting 5 seconds...")
                time.sleep(5)
                continue

            for bonster in items:
                if self.stop_loop:
                    break
                rel_id = bonster.get("ActorBonsterRelId")
                name = self.clean_name(bonster.get("BonsterName", "Unknown"))
                if rel_id and rel_id not in self.petted:
                    self.log(f"Petting {name} (RelID: {rel_id})...")
                    self.pet_bonster(rel_id)
                    request_count += 1
                    time.sleep(short_delay)

                    if request_count >= max_requests_before_cooldown:
                        self.log(f"Reached {max_requests_before_cooldown} requests, pausing {long_cooldown}s...")
                        time.sleep(long_cooldown)
                        request_count = 0
            pageindex += 1


# ----------------- GUI Frame for SC Farm -----------------
class SCFarmFrame(Frame):
    def __init__(self, master, session_info, back_callback=None):
        super().__init__(master, bg="black")
        self.session_info = session_info
        self.back_callback = back_callback

        # Title Label
        Label(self, text="StarCoins Auto-Farm (Bonster Petter)", bg="black", fg="thistle1", font=("Tahoma", 16)).pack(pady=10)

        # Button Frame (Start, Stop, Back)
        btn_frame = Frame(self, bg="black")
        btn_frame.pack(pady=6)

        # Create SCFarm instance
        self.scfarm = SCFarm(self.session_info, log_callback=self._log)

        # Start and Stop buttons
        self.start_btn = Button(btn_frame, text="Start Auto-Pet", bg="green", fg="white", command=self.scfarm.start_auto_pet)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = Button(btn_frame, text="Stop Auto-Pet", bg="red", fg="white", command=self.scfarm.stop_auto_pet)
        self.stop_btn.pack(side="left", padx=6)
        
        if back_callback:
            self.back_btn = Button(btn_frame, text="Back", bg="gray15", fg="white", command=lambda: [self.scfarm.stop_auto_pet(), back_callback()])
            self.back_btn.pack(side="left", padx=6)

        # Output Console (Scrolled Text)
        self.output = ScrolledText(self, state="disabled", bg="black", fg="white", height=10)
        self.output.pack(fill="both", expand=True, padx=10, pady=10)

    def _log(self, message):
        self.output.configure(state="normal")
        self.output.insert("end", message + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")
