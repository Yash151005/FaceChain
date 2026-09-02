"""
main.py — FaceChain Desktop Application

A professional CustomTkinter UI for the Face ID + Blockchain Verification pipeline.
Features a drag-and-drop image panel, animated step-by-step progress tracker,
and a glassmorphism results card with clickable Polygonscan links.
"""

import os
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# ── Load environment variables ───────────────────────────────────────────────
load_dotenv()

# ── CustomTkinter global config ──────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ── Color Palette ────────────────────────────────────────────────────────────
COLORS = {
    "bg_primary":     "#0d0f1a",
    "bg_secondary":   "#141729",
    "bg_card":        "#1a1e35",
    "bg_card_glass":  "#1e2240",
    "accent":         "#6c5ce7",
    "accent_light":   "#a29bfe",
    "success":        "#00cec9",
    "success_dark":   "#00b894",
    "error":          "#ff6b6b",
    "error_dark":     "#ee5a24",
    "warning":        "#feca57",
    "text_primary":   "#f0f0f5",
    "text_secondary": "#8892b0",
    "text_dim":       "#5a6380",
    "border":         "#2d325a",
    "border_glow":    "#6c5ce7",
    "drop_zone":      "#1e2240",
    "drop_hover":     "#252b4d",
}

# ── Fonts (will be set after root is created) ────────────────────────────────
FONTS = {}


def init_fonts():
    """Initialize font objects after root window exists."""
    global FONTS
    FONTS = {
        "title":      ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
        "subtitle":   ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        "body":       ctk.CTkFont(family="Segoe UI", size=13),
        "body_small": ctk.CTkFont(family="Segoe UI", size=11),
        "mono":       ctk.CTkFont(family="Consolas", size=12),
        "mono_small": ctk.CTkFont(family="Consolas", size=11),
        "step_label": ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        "step_desc":  ctk.CTkFont(family="Segoe UI", size=11),
        "big_icon":   ctk.CTkFont(family="Segoe UI", size=36),
        "btn":        ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  ERROR DIALOG
# ═══════════════════════════════════════════════════════════════════════════

class ErrorDialog(ctk.CTkToplevel):
    """Modal error dialog with a dark themed card."""

    def __init__(self, parent, title: str, message: str, on_retry=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("460x260")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_primary"])
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 460) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 260) // 2
        self.geometry(f"+{x}+{y}")

        # Icon
        icon_label = ctk.CTkLabel(self, text="⚠️", font=FONTS["big_icon"],
                                   text_color=COLORS["error"])
        icon_label.pack(pady=(24, 8))

        # Title
        title_label = ctk.CTkLabel(self, text=title, font=FONTS["subtitle"],
                                    text_color=COLORS["text_primary"])
        title_label.pack(pady=(0, 4))

        # Message
        msg_label = ctk.CTkLabel(self, text=message, font=FONTS["body_small"],
                                  text_color=COLORS["text_secondary"],
                                  wraplength=400, justify="center")
        msg_label.pack(pady=(0, 20))

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))

        ctk.CTkButton(
            btn_frame, text="Dismiss", width=120,
            fg_color=COLORS["bg_card"], hover_color=COLORS["border"],
            text_color=COLORS["text_secondary"], font=FONTS["body"],
            command=self.destroy,
        ).pack(side="left", padx=8)

        if on_retry:
            ctk.CTkButton(
                btn_frame, text="Retry", width=120,
                fg_color=COLORS["accent"], hover_color=COLORS["accent_light"],
                text_color="white", font=FONTS["btn"],
                command=lambda: (self.destroy(), on_retry()),
            ).pack(side="left", padx=8)


# ═══════════════════════════════════════════════════════════════════════════
#  STEP TRACKER WIDGET
# ═══════════════════════════════════════════════════════════════════════════

class StepItem(ctk.CTkFrame):
    """A single step in the progress tracker."""

    STATES = {
        "pending":     ("○", "#5a6380", COLORS["text_dim"]),
        "active":      ("◉", COLORS["accent_light"], COLORS["text_primary"]),
        "success":     ("✓", COLORS["success"], COLORS["success"]),
        "error":       ("✗", COLORS["error"], COLORS["error"]),
    }

    def __init__(self, parent, number: int, title: str, description: str):
        super().__init__(parent, fg_color="transparent")
        self.number = number
        self.step_title = title
        self.description = description
        self._state = "pending"
        self._pulse_id = None

        # Layout: [icon] [text block]
        self.icon_label = ctk.CTkLabel(
            self, text="○", width=36, font=FONTS["title"],
            text_color=COLORS["text_dim"],
        )
        self.icon_label.pack(side="left", padx=(0, 12))

        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True)

        self.title_label = ctk.CTkLabel(
            text_frame, text=f"Step {number}: {title}",
            font=FONTS["step_label"], text_color=COLORS["text_dim"],
            anchor="w",
        )
        self.title_label.pack(anchor="w")

        self.desc_label = ctk.CTkLabel(
            text_frame, text=description,
            font=FONTS["step_desc"], text_color=COLORS["text_dim"],
            anchor="w",
        )
        self.desc_label.pack(anchor="w")

        # Status text on the right
        self.status_label = ctk.CTkLabel(
            self, text="Pending", font=FONTS["body_small"],
            text_color=COLORS["text_dim"], width=90,
        )
        self.status_label.pack(side="right", padx=(8, 0))

    def set_state(self, state: str, status_text: str = ""):
        """Update step state: pending, active, success, error."""
        self._state = state
        icon, icon_color, text_color = self.STATES.get(state, self.STATES["pending"])

        self.icon_label.configure(text=icon, text_color=icon_color)
        self.title_label.configure(text_color=text_color)
        self.desc_label.configure(text_color=text_color if state != "pending" else COLORS["text_dim"])

        if status_text:
            self.status_label.configure(text=status_text, text_color=icon_color)
        else:
            defaults = {
                "pending": "Pending",
                "active":  "Processing…",
                "success": "Complete ✓",
                "error":   "Failed ✗",
            }
            self.status_label.configure(
                text=defaults.get(state, ""), text_color=icon_color
            )

        # Pulse animation for active state
        if state == "active":
            self._start_pulse()
        else:
            self._stop_pulse()

    def _start_pulse(self):
        """Subtle pulsing animation for the active step icon."""
        self._pulse_step = 0

        def pulse():
            if self._state != "active":
                return
            symbols = ["◉", "◎", "○", "◎"]
            self._pulse_step = (self._pulse_step + 1) % len(symbols)
            self.icon_label.configure(text=symbols[self._pulse_step])
            self._pulse_id = self.after(400, pulse)

        pulse()

    def _stop_pulse(self):
        if self._pulse_id is not None:
            self.after_cancel(self._pulse_id)
            self._pulse_id = None


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════

class FaceChainApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        init_fonts()

        # ── Window setup ─────────────────────────────────────────────────
        self.title("FaceChain — Face ID + Blockchain Verification")
        self.geometry("1060x720")
        self.minsize(960, 660)
        self.configure(fg_color=COLORS["bg_primary"])

        self._selected_image_path = None
        self._pipeline_running = False

        # ── Header ───────────────────────────────────────────────────────
        self._build_header()

        # ── Main content area (three panels) ─────────────────────────────
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=2)
        content.grid_columnconfigure(2, weight=3)

        self._build_image_panel(content)
        self._build_progress_panel(content)
        self._build_results_panel(content)

    # ─── Header ──────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], height=70,
                               corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        # Left: logo + title
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=24, fill="y")

        ctk.CTkLabel(
            left, text="⛓️", font=ctk.CTkFont(size=28),
        ).pack(side="left", padx=(0, 10), pady=16)

        title_block = ctk.CTkFrame(left, fg_color="transparent")
        title_block.pack(side="left", fill="y", pady=12)

        ctk.CTkLabel(
            title_block, text="FaceChain",
            font=FONTS["title"], text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_block, text="Face ID + Blockchain Verification Pipeline",
            font=FONTS["body_small"], text_color=COLORS["text_secondary"],
            anchor="w",
        ).pack(anchor="w")

        # Right: network badge
        badge = ctk.CTkFrame(header, fg_color=COLORS["bg_card"], corner_radius=8)
        badge.pack(side="right", padx=24, pady=20)

        ctk.CTkLabel(
            badge, text="● Polygon Amoy Testnet",
            font=FONTS["body_small"], text_color=COLORS["success"],
            padx=12, pady=4,
        ).pack()

    # ─── Image Panel (left) ──────────────────────────────────────────────

    def _build_image_panel(self, parent):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"],
                             corner_radius=16, border_width=1,
                             border_color=COLORS["border"])
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        ctk.CTkLabel(
            card, text="📸  Input Face Image",
            font=FONTS["subtitle"], text_color=COLORS["text_primary"],
        ).pack(pady=(20, 12), padx=20, anchor="w")

        # ── Drop zone ────────────────────────────────────────────────────
        self.drop_zone = ctk.CTkFrame(
            card, fg_color=COLORS["drop_zone"], corner_radius=12,
            border_width=2, border_color=COLORS["border"], height=220,
        )
        self.drop_zone.pack(fill="x", padx=20, pady=(0, 12))
        self.drop_zone.pack_propagate(False)

        self.drop_content = ctk.CTkFrame(self.drop_zone, fg_color="transparent")
        self.drop_content.place(relx=0.5, rely=0.5, anchor="center")

        self.drop_icon = ctk.CTkLabel(
            self.drop_content, text="🖼️",
            font=ctk.CTkFont(size=42),
        )
        self.drop_icon.pack(pady=(0, 8))

        self.drop_text = ctk.CTkLabel(
            self.drop_content, text="Click to browse or\ndrag & drop an image",
            font=FONTS["body"], text_color=COLORS["text_secondary"],
            justify="center",
        )
        self.drop_text.pack()

        self.drop_hint = ctk.CTkLabel(
            self.drop_content, text="Supports JPG, PNG, WebP",
            font=FONTS["body_small"], text_color=COLORS["text_dim"],
        )
        self.drop_hint.pack(pady=(4, 0))

        # Image preview label (hidden initially)
        self.preview_label = ctk.CTkLabel(
            self.drop_zone, text="", fg_color="transparent",
        )

        # Clickable drop zone
        for widget in [self.drop_zone, self.drop_content, self.drop_icon,
                       self.drop_text, self.drop_hint]:
            widget.bind("<Button-1>", self._browse_image)

        # Hover effects on drop zone
        self.drop_zone.bind("<Enter>", lambda e: self.drop_zone.configure(
            border_color=COLORS["accent"], fg_color=COLORS["drop_hover"]))
        self.drop_zone.bind("<Leave>", lambda e: self.drop_zone.configure(
            border_color=COLORS["border"], fg_color=COLORS["drop_zone"]))

        # ── File name display ────────────────────────────────────────────
        self.file_label = ctk.CTkLabel(
            card, text="No file selected",
            font=FONTS["body_small"], text_color=COLORS["text_dim"],
        )
        self.file_label.pack(pady=(0, 8), padx=20, anchor="w")

        # ── Verify button ────────────────────────────────────────────────
        self.verify_btn = ctk.CTkButton(
            card, text="🔍  Verify Identity", font=FONTS["btn"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_light"],
            text_color="white", corner_radius=10, height=44,
            command=self._start_pipeline,
        )
        self.verify_btn.pack(fill="x", padx=20, pady=(4, 20))

        # Try to set up drag and drop
        self._setup_dnd()

    def _setup_dnd(self):
        """Attempt to set up native drag-and-drop via tkinterdnd2."""
        try:
            from tkinterdnd2 import DND_FILES
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)
            self.drop_zone.dnd_bind("<<DragEnter>>", lambda e: self.drop_zone.configure(
                border_color=COLORS["success"], fg_color=COLORS["drop_hover"]))
            self.drop_zone.dnd_bind("<<DragLeave>>", lambda e: self.drop_zone.configure(
                border_color=COLORS["border"], fg_color=COLORS["drop_zone"]))
        except ImportError:
            # tkinterdnd2 not available — click-to-browse still works
            pass

    def _on_drop(self, event):
        """Handle drag-and-drop file."""
        path = event.data.strip().strip("{}")
        if path.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")):
            self._load_image(path)
        else:
            self._show_error("Invalid File", "Please drop a valid image file (JPG, PNG, WebP).")

    def _browse_image(self, event=None):
        """Open file dialog to select an image."""
        path = filedialog.askopenfilename(
            title="Select a Face Image",
            filetypes=[
                ("Image Files", "*.jpg *.jpeg *.png *.webp *.bmp"),
                ("All Files", "*.*"),
            ],
        )
        if path:
            self._load_image(path)

    def _load_image(self, path: str):
        """Load and display the selected image."""
        self._selected_image_path = path

        # Update file label
        filename = Path(path).name
        self.file_label.configure(
            text=f"📎 {filename}", text_color=COLORS["text_primary"]
        )

        # Show thumbnail preview
        try:
            pil_image = Image.open(path)
            pil_image.thumbnail((200, 180), Image.Resampling.LANCZOS)
            ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image,
                                      size=pil_image.size)
            self.drop_content.pack_forget()
            self.preview_label.configure(image=ctk_image, text="")
            self.preview_label.image = ctk_image  # prevent GC
            self.preview_label.place(relx=0.5, rely=0.5, anchor="center")

            # Make preview clickable to re-browse
            self.preview_label.bind("<Button-1>", self._browse_image)
        except Exception:
            self.drop_text.configure(text=f"Selected: {filename}")

        # Reset results and steps
        self._reset_pipeline_ui()

    # ─── Progress Panel (center) ─────────────────────────────────────────

    def _build_progress_panel(self, parent):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"],
                             corner_radius=16, border_width=1,
                             border_color=COLORS["border"])
        card.grid(row=0, column=1, sticky="nsew", padx=10, pady=0)

        ctk.CTkLabel(
            card, text="⚡  Pipeline Progress",
            font=FONTS["subtitle"], text_color=COLORS["text_primary"],
        ).pack(pady=(20, 20), padx=20, anchor="w")

        # Steps
        self.steps = []

        step_data = [
            ("Face Detection", "Detecting & encoding face via dlib CNN"),
            ("Reverse Search", "Google Lens lookup via SerpAPI"),
            ("Blockchain Write", "Storing record on Polygon Amoy"),
        ]

        for i, (title, desc) in enumerate(step_data, start=1):
            step = StepItem(card, i, title, desc)
            step.pack(fill="x", padx=20, pady=(0, 16))
            self.steps.append(step)

            # Separator line (except after last)
            if i < len(step_data):
                sep = ctk.CTkFrame(card, fg_color=COLORS["border"], height=1)
                sep.pack(fill="x", padx=40, pady=(0, 16))

        # Spacer
        ctk.CTkFrame(card, fg_color="transparent", height=10).pack(expand=True)

        # Elapsed time
        self.time_label = ctk.CTkLabel(
            card, text="", font=FONTS["body_small"],
            text_color=COLORS["text_dim"],
        )
        self.time_label.pack(pady=(0, 20), padx=20)

    # ─── Results Panel (right) ───────────────────────────────────────────

    def _build_results_panel(self, parent):
        self.results_card = ctk.CTkFrame(
            parent, fg_color=COLORS["bg_card_glass"], corner_radius=16,
            border_width=1, border_color=COLORS["border"],
        )
        self.results_card.grid(row=0, column=2, sticky="nsew", padx=(10, 0), pady=0)

        ctk.CTkLabel(
            self.results_card, text="📋  Verification Results",
            font=FONTS["subtitle"], text_color=COLORS["text_primary"],
        ).pack(pady=(20, 12), padx=20, anchor="w")

        # Placeholder / empty state
        self.results_placeholder = ctk.CTkFrame(self.results_card, fg_color="transparent")
        self.results_placeholder.pack(expand=True, fill="both")

        placeholder_inner = ctk.CTkFrame(self.results_placeholder, fg_color="transparent")
        placeholder_inner.place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(
            placeholder_inner, text="🔒",
            font=ctk.CTkFont(size=48),
        ).pack(pady=(0, 12))

        ctk.CTkLabel(
            placeholder_inner, text="No verification yet",
            font=FONTS["body"], text_color=COLORS["text_secondary"],
        ).pack()

        ctk.CTkLabel(
            placeholder_inner,
            text="Upload a face image and click\nVerify to start the pipeline",
            font=FONTS["body_small"], text_color=COLORS["text_dim"],
            justify="center",
        ).pack(pady=(4, 0))

        # Results container (hidden initially)
        self.results_content = ctk.CTkScrollableFrame(
            self.results_card, fg_color="transparent",
        )

    def _show_results(self, data: dict):
        """Populate the results panel with pipeline output."""
        self.results_placeholder.pack_forget()
        self.results_content.pack(fill="both", expand=True, padx=4, pady=(0, 12))

        # Clear previous results
        for widget in self.results_content.winfo_children():
            widget.destroy()

        # ── Face Hash ────────────────────────────────────────────────────
        self._add_result_section(
            "🧬  Face Hash (SHA-256)",
            data.get("face_hash", "N/A"),
            mono=True,
        )

        # ── Matched URL ──────────────────────────────────────────────────
        url = data.get("matched_url", "")
        title = data.get("match_title", "")
        domain = data.get("match_domain", "")

        url_section = ctk.CTkFrame(self.results_content, fg_color=COLORS["bg_card"],
                                    corner_radius=10)
        url_section.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(
            url_section, text="🌐  Matched URL",
            font=FONTS["step_label"], text_color=COLORS["accent_light"],
            anchor="w",
        ).pack(padx=14, pady=(12, 4), anchor="w")

        if title:
            ctk.CTkLabel(
                url_section, text=title,
                font=FONTS["body"], text_color=COLORS["text_primary"],
                anchor="w", wraplength=300,
            ).pack(padx=14, anchor="w")

        if domain:
            ctk.CTkLabel(
                url_section, text=f"Source: {domain}",
                font=FONTS["body_small"], text_color=COLORS["text_secondary"],
                anchor="w",
            ).pack(padx=14, anchor="w")

        if url:
            url_btn = ctk.CTkButton(
                url_section, text=url[:60] + ("…" if len(url) > 60 else ""),
                font=FONTS["mono_small"],
                fg_color="transparent", hover_color=COLORS["bg_secondary"],
                text_color=COLORS["accent_light"], anchor="w",
                command=lambda: webbrowser.open(url),
            )
            url_btn.pack(padx=10, pady=(4, 12), anchor="w")

        # ── Transaction Hash ─────────────────────────────────────────────
        tx_hash = data.get("tx_hash", "")
        self._add_result_section(
            "📝  Transaction Hash",
            tx_hash or "N/A",
            mono=True,
        )

        # ── Block & Gas ──────────────────────────────────────────────────
        block = data.get("block_number", "")
        gas = data.get("gas_used", "")
        wallet = data.get("wallet", "")

        if block or gas:
            info_section = ctk.CTkFrame(self.results_content, fg_color=COLORS["bg_card"],
                                         corner_radius=10)
            info_section.pack(fill="x", padx=12, pady=(0, 10))

            ctk.CTkLabel(
                info_section, text="📊  On-Chain Details",
                font=FONTS["step_label"], text_color=COLORS["accent_light"],
                anchor="w",
            ).pack(padx=14, pady=(12, 6), anchor="w")

            details = []
            if block:
                details.append(f"Block:  #{block}")
            if gas:
                details.append(f"Gas:    {gas:,}" if isinstance(gas, int) else f"Gas: {gas}")
            if wallet:
                details.append(f"Wallet: {wallet[:8]}…{wallet[-6:]}")

            ctk.CTkLabel(
                info_section, text="\n".join(details),
                font=FONTS["mono_small"], text_color=COLORS["text_secondary"],
                anchor="w", justify="left",
            ).pack(padx=14, pady=(0, 12), anchor="w")

        # ── Polygonscan Link ─────────────────────────────────────────────
        explorer_url = data.get("explorer_url", "")
        if explorer_url:
            ctk.CTkButton(
                self.results_content,
                text="🔗  View on Polygonscan (Amoy)",
                font=FONTS["btn"], fg_color=COLORS["success_dark"],
                hover_color=COLORS["success"], text_color="white",
                corner_radius=10, height=42,
                command=lambda: webbrowser.open(explorer_url),
            ).pack(fill="x", padx=12, pady=(6, 6))

        # ── Timestamp ────────────────────────────────────────────────────
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        ctk.CTkLabel(
            self.results_content, text=f"Verified at {ts}",
            font=FONTS["body_small"], text_color=COLORS["text_dim"],
        ).pack(pady=(8, 12))

    def _add_result_section(self, label: str, value: str, mono=False):
        """Add a labeled value section to the results panel."""
        section = ctk.CTkFrame(self.results_content, fg_color=COLORS["bg_card"],
                                corner_radius=10)
        section.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(
            section, text=label,
            font=FONTS["step_label"], text_color=COLORS["accent_light"],
            anchor="w",
        ).pack(padx=14, pady=(12, 4), anchor="w")

        display = value
        if len(value) > 50:
            display = value[:24] + "…" + value[-24:]

        val_label = ctk.CTkLabel(
            section, text=display,
            font=FONTS["mono_small"] if mono else FONTS["body"],
            text_color=COLORS["text_primary"], anchor="w",
            wraplength=300,
        )
        val_label.pack(padx=14, pady=(0, 12), anchor="w")

        # Copy-on-click
        val_label.bind("<Button-1>", lambda e, v=value: self._copy_to_clipboard(v))
        val_label.bind("<Enter>", lambda e: val_label.configure(
            text_color=COLORS["accent_light"], cursor="hand2"))
        val_label.bind("<Leave>", lambda e: val_label.configure(
            text_color=COLORS["text_primary"]))

    def _copy_to_clipboard(self, text: str):
        """Copy text to system clipboard and show brief feedback."""
        self.clipboard_clear()
        self.clipboard_append(text)
        self.time_label.configure(text="📋 Copied to clipboard!", text_color=COLORS["success"])
        self.after(2000, lambda: self.time_label.configure(
            text="", text_color=COLORS["text_dim"]))

    # ─── Pipeline Execution ──────────────────────────────────────────────

    def _reset_pipeline_ui(self):
        """Reset progress steps and results to initial state."""
        for step in self.steps:
            step.set_state("pending")
        self.time_label.configure(text="")

        # Reset results
        if self.results_content.winfo_manager():
            self.results_content.pack_forget()
            for widget in self.results_content.winfo_children():
                widget.destroy()
        self.results_placeholder.pack(expand=True, fill="both")

    def _start_pipeline(self):
        """Kick off the verification pipeline in a background thread."""
        if self._pipeline_running:
            return

        if not self._selected_image_path:
            self._show_error("No Image Selected",
                             "Please select or drag-and-drop a face image first.")
            return

        self._pipeline_running = True
        self._reset_pipeline_ui()
        self.verify_btn.configure(state="disabled", text="⏳  Processing…")

        thread = threading.Thread(target=self._run_pipeline, daemon=True)
        thread.start()

    def _run_pipeline(self):
        """Execute the 3-step pipeline (runs in a background thread)."""
        import time
        start_time = time.time()
        result_data = {}

        try:
            # ── Step 1: Face Detection & Encoding ────────────────────────
            self._update_step(0, "active", "Detecting face…")
            self._update_time("Running Step 1 of 3…")

            from face_encoder import detect_and_encode, NoFaceDetectedError
            try:
                face_result = detect_and_encode(self._selected_image_path)
            except NoFaceDetectedError as exc:
                self._update_step(0, "error", "No face found")
                self._pipeline_error(
                    "No Face Detected",
                    str(exc),
                )
                return
            except FileNotFoundError as exc:
                self._update_step(0, "error", "File error")
                self._pipeline_error("File Error", str(exc))
                return
            except Exception as exc:
                self._update_step(0, "error", "Error")
                self._pipeline_error(
                    "Face Detection Failed",
                    f"An unexpected error occurred during face detection:\n{exc}",
                )
                return

            face_hash = face_result["face_hash"]
            face_count = face_result["face_count"]
            result_data["face_hash"] = face_hash

            self._update_step(0, "success",
                              f"{face_count} face{'s' if face_count > 1 else ''} found")

            # ── Step 2: Reverse Image Search ─────────────────────────────
            self._update_step(1, "active", "Searching…")
            self._update_time("Running Step 2 of 3…")

            serpapi_key = os.getenv("SERPAPI_KEY", "")

            from reverse_search import search_face, NoMatchFoundError, SearchAPIError
            try:
                search_result = search_face(self._selected_image_path, serpapi_key)
            except NoMatchFoundError as exc:
                self._update_step(1, "error", "No match")
                self._pipeline_error("No Match Found", str(exc))
                return
            except SearchAPIError as exc:
                self._update_step(1, "error", "API error")
                self._pipeline_error(
                    "Search API Error",
                    f"SerpAPI returned an error:\n{exc}\n\n"
                    "Check that your SERPAPI_KEY in .env is valid.",
                )
                return
            except Exception as exc:
                self._update_step(1, "error", "Error")
                self._pipeline_error(
                    "Reverse Search Failed",
                    f"Unexpected error:\n{exc}",
                )
                return

            result_data["matched_url"] = search_result["url"]
            result_data["match_title"] = search_result["title"]
            result_data["match_domain"] = search_result["domain"]

            self._update_step(1, "success",
                              f"Found on {search_result['domain'][:20]}")

            # ── Step 3: Blockchain Write ─────────────────────────────────
            self._update_step(2, "active", "Connecting…")
            self._update_time("Running Step 3 of 3…")

            rpc_url = os.getenv("ALCHEMY_RPC_URL", "")
            private_key = os.getenv("PRIVATE_KEY", "")
            contract_addr = os.getenv("CONTRACT_ADDRESS", "")

            from blockchain import (
                BlockchainClient, BlockchainConnectionError, TransactionFailedError
            )
            try:
                client = BlockchainClient(rpc_url, private_key, contract_addr)
                client.connect()
                self._update_step(2, "active", "Sending tx…")

                bc_result = client.store_record(face_hash, search_result["url"])
            except BlockchainConnectionError as exc:
                self._update_step(2, "error", "Connection failed")
                self._pipeline_error(
                    "Blockchain Connection Error",
                    f"{exc}\n\nCheck your .env file for ALCHEMY_RPC_URL, "
                    "PRIVATE_KEY, and CONTRACT_ADDRESS.",
                )
                return
            except TransactionFailedError as exc:
                self._update_step(2, "error", "Tx failed")
                self._pipeline_error("Transaction Failed", str(exc))
                return
            except Exception as exc:
                self._update_step(2, "error", "Error")
                self._pipeline_error(
                    "Blockchain Error",
                    f"Unexpected error:\n{exc}",
                )
                return

            result_data["tx_hash"] = bc_result["tx_hash"]
            result_data["block_number"] = bc_result["block_number"]
            result_data["gas_used"] = bc_result["gas_used"]
            result_data["explorer_url"] = bc_result["explorer_url"]
            result_data["wallet"] = bc_result["wallet"]
            result_data["record_id"] = bc_result.get("record_id")

            self._update_step(2, "success", "On-chain ✓")

            # ── Done ─────────────────────────────────────────────────────
            elapsed = time.time() - start_time
            self._update_time(f"✅ Completed in {elapsed:.1f}s")
            self.after(0, lambda: self._show_results(result_data))

        finally:
            self._pipeline_running = False
            self.after(0, lambda: self.verify_btn.configure(
                state="normal", text="🔍  Verify Identity"))

    # ─── Thread-safe UI helpers ──────────────────────────────────────────

    def _update_step(self, index: int, state: str, status_text: str = ""):
        """Thread-safe step state update."""
        self.after(0, lambda: self.steps[index].set_state(state, status_text))

    def _update_time(self, text: str):
        """Thread-safe time label update."""
        self.after(0, lambda: self.time_label.configure(
            text=text, text_color=COLORS["text_secondary"]))

    def _pipeline_error(self, title: str, message: str):
        """Show an error dialog (thread-safe)."""
        self._pipeline_running = False
        self.after(0, lambda: self.verify_btn.configure(
            state="normal", text="🔍  Verify Identity"))
        self.after(0, lambda: self._show_error(title, message))

    def _show_error(self, title: str, message: str):
        """Display a modal error dialog."""
        ErrorDialog(self, title, message, on_retry=self._start_pipeline)


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    app = FaceChainApp()
    app.mainloop()


if __name__ == "__main__":
    main()
