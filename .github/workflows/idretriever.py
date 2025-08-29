import tkinter as tk
from tkinter import messagebox
from msp import invoke_method
from pyamf.remoting import ErrorFault

class IDRetrieverFrame(tk.Frame):
    def __init__(self, master, session_data, back_callback, *args, **kwargs):
        super().__init__(master, bg="black", *args, **kwargs)
        self.session_data = session_data
        self.back_callback = back_callback
        self.build_ui()

    def build_ui(self):
        tk.Label(self, text="ID Retriever", font=("Tahoma", 18), fg="white", bg="black").pack(pady=10)

        tk.Label(self, text="Enter Username:", fg="white", bg="black", font=("Tahoma", 12)).pack(pady=(10, 2))
        self.username_entry = tk.Entry(self, font=("Tahoma", 12))
        self.username_entry.pack(pady=(0, 10))

        self.result_label = tk.Label(self, text="", fg="green", bg="black", font=("Tahoma", 11))
        self.result_label.pack(pady=(5, 10))

        btn_frame = tk.Frame(self, bg="black")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Retrieve ID", bg="gray15", fg="white",
                  font=("Tahoma", 12), command=self.retrieve_id).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Back", bg="gray15", fg="white",
                  font=("Tahoma", 12), command=self.back_callback).pack(side="left", padx=5)

    def retrieve_id(self):
        username = self.username_entry.get().strip()
        if not username:
            self.result_label.config(text="Please enter a username.", fg="red")
            return

        server = self.session_data.get("server")
        session_id = self.session_data.get("session_id")

        try:
            code, resp = invoke_method(
                server,
                "MovieStarPlanet.WebService.AMFActorService.GetActorIdByName",
                [username],
                session_id
            )

            if code != 200:
                self.result_label.config(text=f"Failed: Status code {code}", fg="red")
                return

            if isinstance(resp, ErrorFault):
                self.result_label.config(text=f"Server Error: {resp.description}", fg="red")
                return

            self.result_label.config(text=f"✅ {username} → Actor ID: {resp}", fg="green")

        except Exception as e:
            self.result_label.config(text=f"Error: {str(e)}", fg="red")
