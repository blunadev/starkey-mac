import io
from tkinter import Tk, Frame, Label, Button, filedialog
from tkinter.scrolledtext import ScrolledText
from PIL import Image
from pyamf import amf3
from msp import invoke_method, ticket_header
import sys
from colorama import Fore, Style


class GUIConsole(io.StringIO):
    """Redirects stdout/stderr to a Tkinter ScrolledText widget"""
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


class ProfilePictureFrame(Frame):
    def __init__(self, master, session_info, back_callback=None):
        super().__init__(master, bg="black")
        self.session_info = session_info
        self.back_callback = back_callback

        Label(self, text="Profile Picture Changer", font=("Tahoma", 16),
              bg="black", fg="white").pack(pady=20)

        # ---------- Buttons ----------
        btn_frame = Frame(self, bg="black")
        btn_frame.pack(pady=10)
        Button(btn_frame, text="Select Image & Apply",
               command=self.apply_profile_picture,
               bg="gray15", fg="white").pack(side="left", padx=10)
        if back_callback:
            Button(btn_frame, text="Back",
                   command=back_callback,
                   bg="gray15", fg="white").pack(side="left", padx=10)

        # ---------- Console ----------
        self.console = ScrolledText(
            self, state="disabled", height=15,
            bg="black", fg="white", font=("Consolas", 10)
        )
        self.console.pack(fill="both", expand=True, padx=10, pady=10)

        # Redirect prints to console
        self.stdout_backup = sys.stdout
        self.stderr_backup = sys.stderr
        sys.stdout = GUIConsole(self.console)
        sys.stderr = GUIConsole(self.console)

    def apply_profile_picture(self):
        print(Fore.CYAN + "[INFO] Starting profile picture update..." + Style.RESET_ALL)

        acc = self.session_info


        # Extract ticket/session info
        ticket = acc.get("ticket")
        session_id = acc.get("session_id")
        actor_id = acc.get("actor_id")

        if not ticket or not session_id or not actor_id:
            print(Fore.RED + "❌ Missing required session information (ticket, session_id, or actor_id)." + Style.RESET_ALL)
            return

        # Select image
        file_path = filedialog.askopenfilename(
            parent=self.master,
            title="Select Image",
            filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.tiff;*.webp")]
        )
        if not file_path:
            print(Fore.RED + "❌ No file selected. Returning..." + Style.RESET_ALL)
            return

        img = Image.open(file_path)
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Create snapshots
        img_small = img.resize((100, 100), Image.Resampling.LANCZOS)
        buf_small = io.BytesIO()
        img_small.save(buf_small, format="JPEG")
        snapshot_small = amf3.ByteArray(buf_small.getvalue())

        buf_big = io.BytesIO()
        img.save(buf_big, format="JPEG")
        snapshot_big = amf3.ByteArray(buf_big.getvalue())

        print(Fore.CYAN + "[INFO] Uploading custom profile picture..." + Style.RESET_ALL)
        code, response = invoke_method(
            acc["server"],
            'MovieStarPlanet.WebService.Snapshots.AMFGenericSnapshotService.CreateSnapshotSmallAndBig',
            [ticket_header(ticket), actor_id, 'moviestar', 'fullSizeMovieStar',
             snapshot_small, snapshot_big, 'jpg'],
            session_id
        )

        if code == 200:
            print(Fore.GREEN + "✅ Custom Profile Picture successfully applied!" + Style.RESET_ALL)
            print(Fore.CYAN + "ℹ️ It may take a while to see changes." + Style.RESET_ALL)
        else:
            print(Fore.RED + f"❌ Failed to apply custom profile picture. Status code: {code}" + Style.RESET_ALL)
