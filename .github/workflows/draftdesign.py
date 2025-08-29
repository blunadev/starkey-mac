# draftdesign.py
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import io
from pyamf import amf3
from msp import invoke_method, ticket_header
import pprint

class DraftDesignFrame(tk.Frame):
    def __init__(self, master, session_info, back_callback=None):
        super().__init__(master, bg="black")
        self.master = master
        self.session_info = session_info
        self.back_callback = back_callback
        self.selected_design = None
        self.snapshot_path = None
        self.draft_designs = []

        tk.Label(self, text="Draft Design Snapshot Updater", font=("Tahoma", 16), bg="black", fg="cyan").pack(pady=10)

        self.listbox = tk.Listbox(self, bg="gray15", fg="white", font=("Tahoma", 12), width=60, height=10)
        self.listbox.pack(pady=10)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        btn_frame = tk.Frame(self, bg="black")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Choose Snapshot", command=self.choose_snapshot, bg="gray15", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Update Snapshot", command=self.update_snapshot, bg="green", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Back", command=self.go_back, bg="gray15", fg="white").pack(side="left", padx=5)

        self.load_drafts()

    def load_drafts(self):
        """Fetch draft designs from MSP using correct endpoint spec"""
        try:
            server = self.session_info["server"]
            ticket = self.session_info["ticket"]
            actor_id = int(self.session_info["actor_id"])
            session_id = self.session_info["session_id"]

            code, resp = invoke_method(
                server,
                "MovieStarPlanet.MobileServices.AMFDesignService.GetPagedListOfMyDesigns",
                [ticket_header(ticket), actor_id, 0, 50],
                session_id
            )

            if code != 200 or not resp:
                messagebox.showerror("Error", f"Failed to retrieve designs.\nResponse: {resp}")
                return

            self.draft_designs = [d for d in resp.get("items", []) if d.get("Status") == 0]
            if not self.draft_designs:
                messagebox.showinfo("Info", "No draft designs found.")
                return

            self.listbox.delete(0, tk.END)
            for idx, d in enumerate(self.draft_designs):
                self.listbox.insert(tk.END, f"{idx+1}. {d['Name']} (ID: {d['DesignId']})")

        except Exception as e:
            messagebox.showerror("Error", f"Exception loading drafts: {e}")

    def on_select(self, event):
        idx = self.listbox.curselection()
        if idx:
            self.selected_design = self.draft_designs[idx[0]]

    def choose_snapshot(self):
        path = filedialog.askopenfilename(
            title="Select Snapshot Image",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tiff;*.webp")]
        )
        if path:
            self.snapshot_path = path
            messagebox.showinfo("Snapshot Selected", f"Selected file: {path}")

    def update_snapshot(self):
        if not self.selected_design:
            messagebox.showwarning("Select Design", "Please select a draft design first.")
            return
        if not self.snapshot_path:
            messagebox.showwarning("Select Snapshot", "Please choose a snapshot image first.")
            return

        try:
            # Open image and convert to RGB if needed
            img = Image.open(self.snapshot_path)
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Resize to 267x355 (AMF endpoint expects this)
            img_resized = img.resize((267, 355), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img_resized.save(buffer, format="PNG")
            snapshot = amf3.ByteArray(buffer.getvalue())

            # Use FAKE_DESIGN_DATA for testing
            design_data = amf3.ByteArray(b"FAKE_DESIGN_DATA")

            args = [
                ticket_header(self.session_info["ticket"]),
                int(self.session_info["actor_id"]),
                self.selected_design['DesignId'],
                self.selected_design['Name'],
                design_data,
                [],  # Clothes list placeholder
                self.selected_design.get('ClothesId', 0),
                "#FF00FF,#00FFFF",  # Template colors placeholder
                snapshot
            ]

            code, resp = invoke_method(
                self.session_info["server"],
                "MovieStarPlanet.WebService.DesignStudio.AMFDesignStudioWebService.SaveDesignSecureWithSnapshot",
                args,
                self.session_info["session_id"]
            )

            if code == 200:
                messagebox.showinfo("Success", f"Snapshot successfully updated!\nResponse: {pprint.pformat(resp)}")
            else:
                messagebox.showerror("Error", f"Failed to update snapshot.\nStatus: {code}\nResponse: {pprint.pformat(resp)}")

        except Exception as e:
            messagebox.showerror("Error", f"Exception updating snapshot: {e}")

    def go_back(self):
        if self.back_callback:
            self.back_callback()
