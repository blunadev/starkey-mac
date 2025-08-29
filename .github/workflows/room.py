import os
from pyamf import amf3
from tkinter import Tk, filedialog, Frame, Label, Button
from tkinter.scrolledtext import ScrolledText  # <- fixed import
from msp import invoke_method, ticket_header
from PIL import Image
import io
from colorama import Fore, Style
import sys

class GUIConsole(io.StringIO):
    """Redirects stdout/stderr to a Tkinter Text widget"""
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

class RoomPictureFrame(Frame):
    def __init__(self, master, session_data, back_callback=None):
        super().__init__(master, bg="black")
        self.session_data = session_data
        self.back_callback = back_callback

        Label(self, text="Room Picture Changer", font=("Tahoma", 16), bg="black", fg="white").pack(pady=20)
        Button(self, text="Select Image & Apply", command=self.apply_room_picture, bg="gray15", fg="white").pack(pady=10)
        if back_callback:
            Button(self, text="Back", command=back_callback, bg="gray15", fg="white").pack(pady=10)

        # ---------- Console ----------
        self.console = ScrolledText(self, state="disabled", height=15, bg="black", fg="white", font=("Consolas", 10))
        self.console.pack(fill="both", expand=True, padx=10, pady=10)

        # Redirect prints to console
        self.stdout_backup = sys.stdout
        self.stderr_backup = sys.stderr
        sys.stdout = GUIConsole(self.console)
        sys.stderr = GUIConsole(self.console)

    def apply_room_picture(self):
        Tk().withdraw()
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.tiff;*.webp")]
        )
        if not file_path:
            print(Fore.RED + "No file selected." + Style.RESET_ALL)
            return

        img = Image.open(file_path)
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        img_profile = img.resize((400, 400), Image.Resampling.LANCZOS)
        img_medium = img.resize((200, 200), Image.Resampling.LANCZOS)
        img_small = img.resize((100, 100), Image.Resampling.LANCZOS)

        def to_bytes(image):
            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            return amf3.ByteArray(buf.getvalue())

        snapshot_profile = to_bytes(img_profile)
        snapshot_medium = to_bytes(img_medium)
        snapshot_small = to_bytes(img_small)

        room_save_info = {
            "ActorId": self.session_data["actor_id"],
            "RoomName": "My Custom Room",
            "RoomObjects": [],
            "OtherData": None
        }

        print(Fore.CYAN + "[INFO] Applying room picture..." + Style.RESET_ALL)

        try:
            code, resp = invoke_method(
                self.session_data["server"],
                "MovieStarPlanet.WebService.Room.AMFRoomService.SaveRoomWithSnapshot",
                [ticket_header(self.session_data["ticket"]), room_save_info,
                 snapshot_profile, snapshot_medium, snapshot_small],
                self.session_data["session_id"]
            )
        except Exception as e:
            print(Fore.RED + f"❌ Failed to apply custom picture: {e}" + Style.RESET_ALL)
            return

        if code == 200:
            print(Fore.GREEN + "✅ Custom Room Picture successfully applied!" + Style.RESET_ALL)
        else:
            print(Fore.RED + f"❌ Failed to apply custom picture. Status code: {code}" + Style.RESET_ALL)

        print(Fore.CYAN + "ℹ️ Please relog to see the changes." + Style.RESET_ALL)
