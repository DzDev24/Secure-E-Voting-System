"""
voter_client_gui.py – Tkinter-based GUI voter client (bonus).

Provides the same cryptographic voting logic as voter_client.py but through
a graphical interface built with tkinter/ttk.

Run:
    python voter_client_gui.py
"""

import json
import os
import tkinter as tk
from tkinter import messagebox, ttk

from voter_client import cast_vote

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")


class VoterApp(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("Secure E-Voting System")
        self.resizable(False, False)

        style = ttk.Style(self)
        style.theme_use("clam")

        self._build_ui()
        self._load_candidates()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        padding = {"padx": 12, "pady": 6}

        # Title label
        header = ttk.Label(
            self,
            text="🗳  Secure E-Voting System",
            font=("Helvetica", 16, "bold"),
        )
        header.grid(row=0, column=0, columnspan=2, pady=(16, 8))

        # Voter ID
        ttk.Label(self, text="Voter ID:").grid(row=1, column=0, sticky="e", **padding)
        self._voter_id_var = tk.StringVar()
        ttk.Entry(self, textvariable=self._voter_id_var, width=20).grid(
            row=1, column=1, sticky="w", **padding
        )

        # Candidate selection
        ttk.Label(self, text="Candidate:").grid(row=2, column=0, sticky="e", **padding)
        self._candidate_var = tk.StringVar()
        self._candidate_combo = ttk.Combobox(
            self,
            textvariable=self._candidate_var,
            state="readonly",
            width=18,
        )
        self._candidate_combo.grid(row=2, column=1, sticky="w", **padding)

        # Cast Vote button
        self._vote_btn = ttk.Button(
            self, text="Cast Vote", command=self._on_cast_vote
        )
        self._vote_btn.grid(row=3, column=0, columnspan=2, pady=(8, 4))

        # Status label
        self._status_var = tk.StringVar(value="")
        self._status_label = ttk.Label(
            self,
            textvariable=self._status_var,
            font=("Helvetica", 10, "italic"),
            foreground="gray",
        )
        self._status_label.grid(row=4, column=0, columnspan=2, pady=(4, 16))

    def _load_candidates(self) -> None:
        try:
            with open(CANDIDATES_FILE) as fh:
                candidates = json.load(fh)
            self._candidate_combo["values"] = candidates
            if candidates:
                self._candidate_combo.current(0)
        except FileNotFoundError:
            messagebox.showerror(
                "Setup Error",
                f"Candidates file not found.\nRun admin_setup.py first.",
            )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_cast_vote(self) -> None:
        voter_id = self._voter_id_var.get().strip()
        candidate = self._candidate_var.get()

        if not voter_id:
            messagebox.showwarning("Input Error", "Please enter your Voter ID.")
            return
        if not candidate:
            messagebox.showwarning("Input Error", "Please select a candidate.")
            return

        self._set_status("Sending vote …", "blue")
        self._vote_btn.config(state="disabled")
        self.update_idletasks()

        try:
            response = cast_vote(voter_id, candidate)
        except KeyError as exc:
            self._set_status(f"Error: {exc}", "red")
            self._vote_btn.config(state="normal")
            return
        except ConnectionRefusedError:
            self._set_status("Cannot connect to voting server.", "red")
            self._vote_btn.config(state="normal")
            return
        except Exception as exc:
            self._set_status(f"Unexpected error: {exc}", "red")
            self._vote_btn.config(state="normal")
            return

        status = response.get("status", "unknown")
        message = response.get("message", "")

        if status == "accepted":
            self._set_status(f"✓ {message}", "green")
            messagebox.showinfo("Vote Accepted", message)
        else:
            self._set_status(f"✗ {message}", "red")
            messagebox.showerror("Vote Rejected", message)

        self._vote_btn.config(state="normal")

    def _set_status(self, text: str, color: str = "gray") -> None:
        self._status_var.set(text)
        self._status_label.config(foreground=color)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = VoterApp()
    app.mainloop()
