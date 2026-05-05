"""
voter_client_gui.py – Clean light-themed voter client (CustomTkinter).

Run:  python voter_client_gui.py
"""

import json
import os
import sys
import customtkinter as ctk

from voter_client import cast_vote


ctk.set_appearance_mode("light")


BG        = "#F3F4F6"
CARD      = "#FFFFFF"
BORDER    = "#E5E7EB"
ACCENT    = "#4F46E5"
ACCENT_HV = "#4338CA"
SUCCESS   = "#059669"
ERROR     = "#DC2626"
WARNING   = "#D97706"
TEXT      = "#111827"
TEXT_SUB  = "#6B7280"
HEADER_BG = "#1E293B"
HEADER_FG = "#FFFFFF"


DATA_DIR        = os.path.join(os.path.dirname(__file__), "data")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
VOTERS_FILE     = os.path.join(DATA_DIR, "voters.json")
RESULTS_FILE    = os.path.join(DATA_DIR, "results.json")

FONT = "Segoe UI"


class VoterApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Secure E-Voting System")
        self.geometry("520x600")
        self.minsize(460, 520)
        self.configure(fg_color=BG)

        self._voter_name = None
        self._candidates = []
        self._voters = {}
        self._current_round = 1
        self._poll_id = None

        if not self._load_data():
            return

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True)

        if self._is_election_closed():
            self._show_closed_message()
        else:
            self._show_login_page()

  

    def _load_data(self):
        """Loads data files from disk into memory. Returns False if files are missing."""
        errors = []
        try:
            with open(CANDIDATES_FILE) as f:
                self._candidates = json.load(f)
        except FileNotFoundError:
            errors.append("Candidates file not found.")
        try:
            with open(VOTERS_FILE) as f:
                self._voters = json.load(f)
        except FileNotFoundError:
            errors.append("Voter registry not found.")
            
        if errors:
            # Show error inside the GUI itself instead of an ugly system popup
            self._container = ctk.CTkFrame(self, fg_color="transparent")
            self._container.pack(fill="both", expand=True)
            self._header(self._container)
            content = ctk.CTkFrame(self._container, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=36, pady=24)
            card = self._card(content)
            card.pack(fill="x")
            ctk.CTkLabel(card, text="SETUP ERROR",
                         font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
                         text_color=ERROR).pack(pady=(24, 8))
            ctk.CTkLabel(card, text="\n".join(errors) + "\n\nRun admin_setup.py first.",
                         font=ctk.CTkFont(family=FONT, size=12),
                         text_color=TEXT_SUB, wraplength=360, justify="center"
                         ).pack(padx=24, pady=(0, 20))
            ctk.CTkButton(card, text="Exit", height=42, corner_radius=8,
                          fg_color=BORDER, hover_color="#D1D5DB", text_color=TEXT,
                          font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                          command=self.destroy).pack(fill="x", padx=24, pady=(0, 24))
            return False
            
        # Check if there is an active runoff round saved in the results file
        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE) as f:
                    data = json.load(f)
                active = data.get("active_candidates")
                if active:
                    self._candidates = active
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return True

    def _is_election_closed(self):
        """Helper to quickly check if the election was closed by the admin."""
        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE) as f:
                    return json.load(f).get("election_closed", False)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return False

    def _has_voted(self, vid):
        """Helper to check if the user has already voted."""
        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE) as f:
                    return vid in json.load(f).get("voted_ids", [])
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return False

    def _reload_state(self):
        """Refresh current round and candidate list from disk before rendering UI."""
        self._current_round = 1
        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE) as f:
                    data = json.load(f)
                active = data.get("active_candidates")
                if active:
                    self._candidates = active
                self._current_round = data.get("round", 1)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

    def _poll_state(self):
        """Auto-refresh mechanism running every 3 seconds to check for runoffs or closures."""
        old_round = getattr(self, "_current_round", 1)
        self._reload_state()
        
        # If admin closed the election while voter was looking at the login screen
        if self._is_election_closed():
            self._show_closed_message()
            return
            
        # If a runoff round started while voter was looking at the screen
        if self._current_round != old_round:
            self._show_login_page()
            return
            
        # self.after(delay_ms, function) tells Tkinter to run a function in the future
        self._poll_id = self.after(3000, self._poll_state)

    def _clear(self):
        """Wipes the screen clean. Also cancels any pending poll timers to prevent bugs."""
        if self._poll_id:
            # Cancel the loop timer if we change screens
            self.after_cancel(self._poll_id)
            self._poll_id = None
        for w in self._container.winfo_children():
            w.destroy()

   

    def _header(self, parent, subtitle=""):
        h = 74 if subtitle else 60
        hdr = ctk.CTkFrame(parent, fg_color=HEADER_BG, corner_radius=0, height=h)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="SECURE E-VOTING SYSTEM",
                     font=ctk.CTkFont(family=FONT, size=18, weight="bold"),
                     text_color=HEADER_FG).pack(pady=(14, 1))
        if subtitle:
            ctk.CTkLabel(hdr, text=subtitle,
                         font=ctk.CTkFont(family=FONT, size=11),
                         text_color="#94A3B8").pack()

    def _card(self, parent, title=""):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12,
                            border_width=1, border_color=BORDER)
        if title:
            ctk.CTkLabel(card, text=title,
                         font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
                         text_color=TEXT, anchor="w").pack(fill="x", padx=24, pady=(20, 6))
            ctk.CTkFrame(card, fg_color=BORDER, height=1).pack(fill="x", padx=24, pady=(0, 12))
        return card

    def _fade_in(self, widget, steps=14, delay=35, step=0):
        """Card slide-up animation with an ease-out cubic curve.
        Uses a mathematical curve to make the animation start fast and end slowly (easing).
        """
        total_offset = 30
        if step >= steps:
            # Animation complete: lock widget in final position
            widget.pack_configure(pady=(20, 10))
            return
            
        # Calculate mathematical easing (1 - (1 - t)^3)
        t = step / steps
        eased = 1 - (1 - t) ** 3
        offset = int(total_offset * (1 - eased))
        
        # Update widget position
        widget.pack_configure(pady=(20 + offset, 10))
        
        # Call this function again after 'delay' milliseconds to process the next frame
        self.after(delay, self._fade_in, widget, steps, delay, step + 1)

 

    def _show_closed_message(self):
        self._clear()
        self._header(self._container, "Election Closed")
        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=36, pady=24)
        card = self._card(content)
        card.pack(fill="x")
        ctk.CTkLabel(card, text="ELECTION HAS ENDED",
                     font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
                     text_color=TEXT_SUB).pack(pady=(28, 8))
        ctk.CTkLabel(card, text="The voting period is over. Contact the administrator for results.",
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT_SUB, wraplength=360, justify="center").pack(pady=(0, 24))
        ctk.CTkButton(card, text="Exit", height=42, corner_radius=8,
                      fg_color=BORDER, hover_color="#D1D5DB", text_color=TEXT,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=self.destroy).pack(fill="x", padx=24, pady=(0, 24))

   

    def _show_login_page(self):
        self._reload_state()
        if self._is_election_closed():
            self._show_closed_message()
            return
        self._clear()
        self._voter_name = None

        sub = f"Runoff — Round {self._current_round}" if self._current_round > 1 else ""
        self._header(self._container, subtitle=sub)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=36, pady=24)

        card = self._card(content, "VOTER AUTHENTICATION")
        card.pack(fill="x", pady=(20, 10))

        ctk.CTkLabel(card, text="Enter your name to access the ballot",
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT_SUB, anchor="w"
                     ).pack(fill="x", padx=24, pady=(0, 6))

        self._login_var = ctk.StringVar()
        entry = ctk.CTkEntry(card, textvariable=self._login_var,
                             placeholder_text="e.g. Nazim",
                             height=42, corner_radius=8,
                             font=ctk.CTkFont(family=FONT, size=13),
                             border_color=BORDER, fg_color="#F9FAFB")
        entry.pack(fill="x", padx=24, pady=(0, 14))
        entry.focus_set()
        entry.bind("<Return>", lambda e: self._on_login())

        ctk.CTkButton(card, text="Log In", height=44, corner_radius=8,
                      fg_color=ACCENT, hover_color=ACCENT_HV,
                      font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
                      command=self._on_login).pack(fill="x", padx=24)

        self._login_msg = ctk.StringVar()
        ctk.CTkLabel(card, textvariable=self._login_msg,
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=ERROR, wraplength=360
                     ).pack(fill="x", padx=24, pady=(8, 20))

        self._fade_in(card)
        self._poll_state()

    def _on_login(self):
        name = self._login_var.get().strip()
        if not name:
            self._login_msg.set("Please enter your name.")
            return
        if name not in self._voters:
            self._login_msg.set(f"Name '{name}' not found in the registry.")
            return
        if not self._voters[name].get("public_key"):
            self._login_msg.set(f"No keys registered for '{name}'. Run generate_keys.py first.")
            return
        if self._has_voted(name):
            self._login_msg.set(f"'{name}' has already cast their vote.")
            return
            
        self._voter_name = name
        self._show_voting_page()

   

    def _show_voting_page(self):
        self._reload_state()
        if self._is_election_closed():
            self._show_closed_message()
            return
        self._clear()

        sub = f"Runoff — Round {self._current_round}" if self._current_round > 1 else ""
        self._header(self._container, subtitle=sub)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=36, pady=16)

        # Top bar showing who is logged in
        bar = ctk.CTkFrame(content, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(bar, text=f"{self._voter_name}",
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT_SUB).pack(side="left")
        ctk.CTkButton(bar, text="Log Out", width=72, height=28, corner_radius=6,
                      fg_color="transparent", hover_color=BORDER,
                      border_width=1, border_color=BORDER, text_color=TEXT_SUB,
                      font=ctk.CTkFont(family=FONT, size=11),
                      command=self._show_login_page).pack(side="right")

        card = self._card(content, "SELECT YOUR CANDIDATE")
        card.pack(fill="both", expand=True)

        ctk.CTkLabel(card, text="Choose one candidate from the list below.",
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT_SUB, anchor="w"
                     ).pack(fill="x", padx=24, pady=(0, 10))

        # Use a scrollable frame only if there are many candidates, to save space
        if len(self._candidates) > 6:
            cand_frame = ctk.CTkScrollableFrame(card, fg_color="transparent",
                                                 scrollbar_button_color=BORDER,
                                                 scrollbar_button_hover_color="#D1D5DB")
        else:
            cand_frame = ctk.CTkFrame(card, fg_color="transparent")
        cand_frame.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        # Radio buttons all share this one StringVar. When clicked, it stores the candidate's name.
        self._cand_var = ctk.StringVar(value="")
        for c in self._candidates:
            ctk.CTkRadioButton(
                cand_frame, text=f"  {c}", variable=self._cand_var, value=c,
                font=ctk.CTkFont(family=FONT, size=13),
                fg_color=ACCENT, hover_color=ACCENT_HV,
                border_color="#D1D5DB", text_color=TEXT,
                radiobutton_width=18, radiobutton_height=18,
            ).pack(fill="x", padx=10, pady=5, anchor="w")

        self._vote_btn = ctk.CTkButton(
            card, text="Cast Vote", height=44, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HV,
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
            command=self._on_cast_vote,
        )
        self._vote_btn.pack(fill="x", padx=24, pady=(6, 4))

        self._vote_msg = ctk.StringVar()
        ctk.CTkLabel(card, textvariable=self._vote_msg,
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=WARNING, wraplength=360
                     ).pack(fill="x", padx=24, pady=(4, 16))

        self._fade_in(card)

    def _on_cast_vote(self):
        cand = self._cand_var.get()
        if not cand:
            self._vote_msg.set("Please select a candidate before voting.")
            return
            
        # Show inline confirmation page instead of an annoying popup
        self._show_confirm_vote(cand)

  

    def _show_confirm_vote(self, candidate):
        self._clear()
        sub = f"Runoff — Round {self._current_round}" if self._current_round > 1 else ""
        self._header(self._container, subtitle=sub)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=36, pady=24)

        card = self._card(content, "CONFIRM YOUR VOTE")
        card.pack(fill="x", pady=(20, 10))

        ctk.CTkLabel(card, text="You are about to cast your vote for:",
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT_SUB).pack(padx=24, pady=(0, 12))

        # Highlighted candidate name in a colored box
        name_frame = ctk.CTkFrame(card, fg_color="#EEF2FF", corner_radius=8,
                                  border_width=1, border_color="#C7D2FE")
        name_frame.pack(fill="x", padx=24, pady=(0, 12))
        ctk.CTkLabel(name_frame, text=candidate,
                     font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
                     text_color=ACCENT).pack(pady=12)

        ctk.CTkLabel(card, text="This action cannot be undone.",
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=WARNING).pack(pady=(0, 16))

        self._confirm_msg = ctk.StringVar()
        ctk.CTkLabel(card, textvariable=self._confirm_msg,
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=TEXT_SUB, wraplength=360
                     ).pack(fill="x", padx=24, pady=(0, 8))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(0, 24))

        # The lambda here passes 'candidate' to the function securely when clicked
        ctk.CTkButton(btn_row, text="Confirm Vote", height=44, corner_radius=8,
                      fg_color=ACCENT, hover_color=ACCENT_HV,
                      font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
                      command=lambda: self._do_cast_vote(candidate)
                      ).pack(side="left", expand=True, fill="x", padx=(0, 4))

        ctk.CTkButton(btn_row, text="Go Back", height=44, corner_radius=8,
                      fg_color=BORDER, hover_color="#D1D5DB", text_color=TEXT,
                      font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
                      command=self._show_voting_page
                      ).pack(side="left", expand=True, fill="x", padx=(4, 0))

        self._fade_in(card)

    def _do_cast_vote(self, candidate):
        self._confirm_msg.set("Encrypting and signing vote ...")
        self.update_idletasks()

        try:
            # Calls the backend function in voter_client.py
            # This connects via TCP to send the vote
            resp = cast_vote(self._voter_name, candidate)
        except KeyError as exc:
            self._show_result("error", str(exc))
            return
        except ConnectionRefusedError:
            self._show_result("error",
                              "Cannot connect to the voting server.\n"
                              "Make sure voting_server.py is running.")
            return
        except Exception as exc:
            self._show_result("error", f"Unexpected error: {exc}")
            return

        st = resp.get("status", "unknown")
        msg = resp.get("message", "No response from server.")
        
        # Determine whether to show the green success tick or the orange rejection warning
        self._show_result("success" if st == "accepted" else "rejected", msg)



    def _show_result(self, kind, message):
        """Displays the final success or error screen."""
        self._clear()
        self._header(self._container)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=36, pady=24)

        card = self._card(content)
        card.pack(fill="x", pady=(20, 10))

        # Python dictionary 'get' method used to quickly pick the right icon/color mapping
        icon, title, color = {
            "success":  ("✓", "VOTE ACCEPTED",  SUCCESS),
            "rejected": ("✗", "VOTE REJECTED",  WARNING),
            "error":    ("!", "ERROR",           ERROR),
        }.get(kind, ("?", "UNKNOWN", TEXT_SUB))

        ctk.CTkLabel(card, text=icon,
                     font=ctk.CTkFont(size=44, weight="bold"),
                     text_color=color).pack(pady=(24, 2))
        ctk.CTkLabel(card, text=title,
                     font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
                     text_color=color).pack(pady=(0, 10))
        ctk.CTkFrame(card, fg_color=BORDER, height=1).pack(fill="x", padx=24, pady=(0, 12))
        ctk.CTkLabel(card, text=message,
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT, wraplength=380, justify="center"
                     ).pack(padx=24, pady=(0, 4))
                     
        if self._voter_name:
            ctk.CTkLabel(card, text=f"Voter: {self._voter_name}",
                         font=ctk.CTkFont(family=FONT, size=11),
                         text_color=TEXT_SUB).pack(pady=(2, 16))

        ctk.CTkButton(card, text="Log Out", height=42, corner_radius=8,
                      fg_color=BORDER, hover_color="#D1D5DB", text_color=TEXT,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=self._show_login_page
                      ).pack(fill="x", padx=24, pady=(0, 24))

        self._fade_in(card)


if __name__ == "__main__":
    app = VoterApp()
    app.mainloop()
