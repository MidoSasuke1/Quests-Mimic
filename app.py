import os
import sys
import glob
import json
import shutil
import ctypes
import re
import tempfile
import webbrowser
import subprocess
from pathlib import Path
from PIL import Image
import customtkinter as ctk

# ==============================================================================
# DEVELOPER & DONATION CONFIGURATION
# ==============================================================================
DEVELOPER_NAME = "Mido Sasuke"
APP_VERSION = "v1.0.0"
COPYRIGHT_TEXT = "© 2026 Mido Sasuke. All rights reserved."

# Social Links
LINK_GITHUB = "https://github.com/MidoSasuke1"
LINK_X = "https://x.com/Mido_Sasuke1"
LINK_STEAM = "https://steamcommunity.com/id/Mido_Sasuke/"
LINK_WEBSITE = "https://animeconnectionsquiz.com/"

# Donation settings
DONATION_TOGGLE = "off"   # Set to "on" to display the button
DONATION_TYPE = "crypto"  # "crypto" or "link"
DONATION_TARGET = "0xYourMusewalletAddressHere"
# ==============================================================================

# Locate bundled resources inside PyInstaller single-file bundle
if getattr(sys, 'frozen', False):
    RESOURCE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))

# Store user preferences permanently in AppData
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "QuestsMimic")
os.makedirs(APPDATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APPDATA_DIR, "config.json")

# Bundled assets paths
GAMES_DIR = os.path.join(RESOURCE_DIR, "games")
MASTER_GAMES_FILE = os.path.join(GAMES_DIR, "games.json")
RUNNER_EXE = os.path.join(RESOURCE_DIR, "runner.exe")
SOUND_FILE = os.path.join(RESOURCE_DIR, "effect.mp3")
ICON_FILE = os.path.join(RESOURCE_DIR, "icon.png")

# Tell Windows to treat this as a unique app on the Taskbar
try:
    myappid = "midosasuke.questsmimic.launcher.v1"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

PAGE_SIZE = 50

DEFAULT_CONFIG = {
    "last_game": "Aniimo",
    "last_duration": "15 Minutes"
}

def play_sound_native(file_path):
    """Play effect.mp3 using Windows native MCI API without extra dependencies."""
    if not os.path.exists(file_path):
        return
    winmm = ctypes.windll.winmm
    winmm.mciSendStringW("close quest_sound", None, 0, None)
    res = winmm.mciSendStringW(f'open "{os.path.abspath(file_path)}" type mpegvideo alias quest_sound', None, 0, None)
    if res == 0:
        winmm.mciSendStringW("play quest_sound", None, 0, None)

class QuestsMimicApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Quests Mimic")
        self.geometry("640x740")
        self.resizable(False, False)

        # Load Icon from bundled resource
        if os.path.exists(ICON_FILE):
            try:
                icon_img = Image.open(ICON_FILE)
                self.icon_photo = ctk.CTkImage(light_image=icon_img, dark_image=icon_img, size=(32, 32))
                self.iconphoto(True, self.icon_photo._dark_image)
            except Exception:
                pass

        self.config = self.load_config()
        self.all_games = self.load_games()
        self.current_filtered_games = self.all_games
        self.display_limit = PAGE_SIZE

        self.active_process = None
        self.temp_run_dir = None
        self.timer_running = False

        self.setup_ui()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return {**DEFAULT_CONFIG, **json.load(f)}
            except Exception:
                pass
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def load_games(self):
        external_file = os.path.join(os.path.dirname(sys.executable), "games", "games.json")
        target_file = external_file if os.path.exists(external_file) else MASTER_GAMES_FILE

        if os.path.exists(target_file):
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading master games file: {e}")

        games_list = []
        if os.path.exists(GAMES_DIR):
            batch_files = glob.glob(os.path.join(GAMES_DIR, "*.json"))
            for bf in batch_files:
                try:
                    with open(bf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            games_list.extend(data)
                except Exception:
                    pass

        games_list.sort(key=lambda x: x.get("name", "").lower())
        return games_list

    def setup_ui(self):
        # Header Frame
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(15, 5))

        title_label = ctk.CTkLabel(header, text="Quests Mimic", font=("Segoe UI", 24, "bold"))
        title_label.pack(side="left")

        # Top Buttons (About & Optional Donate)
        right_btns = ctk.CTkFrame(header, fg_color="transparent")
        right_btns.pack(side="right")

        btn_about = ctk.CTkButton(
            right_btns,
            text="ℹ About",
            width=70,
            fg_color="#313338",
            hover_color="#3b3e45",
            command=self.open_about_modal
        )
        btn_about.pack(side="right", padx=(5, 0))

        if DONATION_TOGGLE.lower() == "on":
            btn_donate = ctk.CTkButton(
                right_btns,
                text="☕ Donate",
                width=85,
                fg_color="#ff5f5f",
                hover_color="#e04848",
                command=self.handle_donation
            )
            btn_donate.pack(side="right", padx=5)

        # Search Bar
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.on_search_changed)
        search_entry = ctk.CTkEntry(
            self,
            placeholder_text=f"Search {len(self.all_games)} verified games...",
            textvariable=self.search_var,
            height=38,
            font=("Segoe UI", 12)
        )
        search_entry.pack(fill="x", padx=25, pady=(5, 10))

        # Scrollable Games List
        self.games_scroll = ctk.CTkScrollableFrame(self, height=240, label_text="Verified Games Database")
        self.games_scroll.pack(fill="x", padx=25, pady=5)
        self.game_buttons = []
        self.selected_game = None

        self.render_games_view(reset_scroll=True)

        # Selected Game Status Label
        self.lbl_selected = ctk.CTkLabel(
            self,
            text="Selected: None",
            font=("Segoe UI", 13, "bold"),
            text_color="#5865F2"
        )
        self.lbl_selected.pack(pady=4)

        # Duration Selector Frame
        opt_frame = ctk.CTkFrame(self)
        opt_frame.pack(fill="x", padx=25, pady=8)

        lbl_dur = ctk.CTkLabel(opt_frame, text="Quest Duration:", font=("Segoe UI", 12, "bold"))
        lbl_dur.pack(side="left", padx=15, pady=8)

        self.duration_var = ctk.StringVar(value=self.config.get("last_duration", "15 Minutes"))
        dur_dropdown = ctk.CTkOptionMenu(
            opt_frame,
            values=["5 Minutes", "10 Minutes", "15 Minutes", "20 Minutes", "30 Minutes"],
            variable=self.duration_var,
            command=self.on_duration_change,
            width=150
        )
        dur_dropdown.pack(side="right", padx=15, pady=8)

        # Timer & Progress Display
        self.lbl_timer = ctk.CTkLabel(self, text="00:00 / 15:00", font=("Segoe UI", 24, "bold"))
        self.lbl_timer.pack(pady=(8, 4))

        self.progress_bar = ctk.CTkProgressBar(self, width=590)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=4)

        # Launch / Stop Quest Button
        self.btn_toggle = ctk.CTkButton(
            self,
            text="Launch Quest",
            height=44,
            font=("Segoe UI", 14, "bold"),
            fg_color="#248046",
            hover_color="#1a6334",
            command=self.toggle_quest
        )
        self.btn_toggle.pack(fill="x", padx=25, pady=(10, 8))

        # Developer Branding Footer
        lbl_footer = ctk.CTkLabel(
            self,
            text=f"{APP_VERSION} • Developed by {DEVELOPER_NAME}",
            font=("Segoe UI", 10),
            text_color="#80848e"
        )
        lbl_footer.pack(pady=(0, 6))

        # Restore previously selected game
        last_g = self.config.get("last_game")
        for g in self.all_games:
            if g.get("name") == last_g:
                self.select_game(g)
                break

    def on_search_changed(self, *args):
        query = self.search_var.get().strip()

        # Easter Egg Trigger: Typing /mido opens author proof
        if query.lower() in ["/mido", "/author"]:
            self.search_var.set("")
            self.open_easter_egg()
            return

        if not query:
            self.current_filtered_games = self.all_games
        else:
            q_lower = query.lower()
            self.current_filtered_games = [
                g for g in self.all_games
                if q_lower in g.get("name", "").lower() or q_lower in g.get("category", "").lower()
            ]
        self.display_limit = PAGE_SIZE
        self.render_games_view(reset_scroll=True)

    def render_games_view(self, reset_scroll=False):
        for btn in self.game_buttons:
            btn.destroy()
        self.game_buttons.clear()

        visible_slice = self.current_filtered_games[:self.display_limit]

        for g in visible_slice:
            name = g.get("name", "Unknown")
            cat = g.get("category", "")
            label_text = f"{name}  [{cat}]" if cat else name

            btn = ctk.CTkButton(
                self.games_scroll,
                text=label_text,
                anchor="w",
                fg_color="#2b2d31",
                hover_color="#35373c",
                height=32,
                command=lambda item=g: self.select_game(item)
            )
            btn.pack(fill="x", pady=2, padx=5)
            self.game_buttons.append(btn)

        total_matches = len(self.current_filtered_games)
        if total_matches > self.display_limit:
            remaining = total_matches - self.display_limit
            next_count = min(PAGE_SIZE, remaining)
            btn_more = ctk.CTkButton(
                self.games_scroll,
                text=f"▼ Showing {self.display_limit} of {total_matches} — Click to Load {next_count} More...",
                fg_color="#1e1f22",
                hover_color="#2b2d31",
                text_color="#5865F2",
                font=("Segoe UI", 11, "bold"),
                height=34,
                command=self.load_more_games
            )
            btn_more.pack(fill="x", pady=6, padx=5)
            self.game_buttons.append(btn_more)

        if reset_scroll:
            try:
                self.games_scroll._parent_canvas.yview_moveto(0.0)
            except Exception:
                pass

    def load_more_games(self):
        self.display_limit += PAGE_SIZE
        self.render_games_view(reset_scroll=False)

    def select_game(self, game_obj):
        self.selected_game = game_obj
        self.lbl_selected.configure(text=f"Selected: {game_obj.get('name')}", text_color="#5865F2")
        self.config["last_game"] = game_obj.get("name")
        self.save_config()

    def on_duration_change(self, choice):
        self.config["last_duration"] = choice
        self.save_config()
        if not self.timer_running:
            dur_min = int(choice.split()[0])
            self.lbl_timer.configure(text=f"00:00 / {dur_min:02d}:00")

    def open_about_modal(self):
        """Display the official About / Developer credits modal."""
        about_win = ctk.CTkToplevel(self)
        about_win.title("About Quests Mimic")
        about_win.geometry("450x420")
        about_win.resizable(False, False)
        about_win.attributes("-topmost", True)

        ctk.CTkLabel(about_win, text="Quests Mimic", font=("Segoe UI", 20, "bold")).pack(pady=(20, 2))
        ctk.CTkLabel(about_win, text=f"Version {APP_VERSION}", font=("Segoe UI", 11), text_color="#949ba4").pack(pady=(0, 10))

        ctk.CTkLabel(about_win, text=f"Developed with ❤️ by {DEVELOPER_NAME}", font=("Segoe UI", 13, "bold"), text_color="#5865F2").pack(pady=2)
        ctk.CTkLabel(about_win, text=COPYRIGHT_TEXT, font=("Segoe UI", 10), text_color="#949ba4").pack(pady=(0, 15))

        # Social / Project Buttons
        links_frame = ctk.CTkFrame(about_win, fg_color="transparent")
        links_frame.pack(fill="x", padx=40)

        ctk.CTkButton(links_frame, text="🌐 Official Website", height=34, command=lambda: webbrowser.open(LINK_WEBSITE)).pack(fill="x", pady=4)
        ctk.CTkButton(links_frame, text="💻 GitHub Profile", height=34, command=lambda: webbrowser.open(LINK_GITHUB)).pack(fill="x", pady=4)
        ctk.CTkButton(links_frame, text="🐦 X (Twitter)", height=34, command=lambda: webbrowser.open(LINK_X)).pack(fill="x", pady=4)
        ctk.CTkButton(links_frame, text="🎮 Steam Profile", height=34, command=lambda: webbrowser.open(LINK_STEAM)).pack(fill="x", pady=4)

        ctk.CTkButton(about_win, text="Close", width=120, height=32, fg_color="#313338", hover_color="#3b3e45", command=about_win.destroy).pack(pady=(20, 0))

    def open_easter_egg(self):
        """Hidden developer proof modal."""
        egg_win = ctk.CTkToplevel(self)
        egg_win.title("Authentic Developer Signature")
        egg_win.geometry("420x220")
        egg_win.resizable(False, False)
        egg_win.attributes("-topmost", True)

        ctk.CTkLabel(egg_win, text="🔐 Genuine Build Verified", font=("Segoe UI", 16, "bold"), text_color="#23a55a").pack(pady=(20, 8))
        sig_text = (
            f"Original Author: {DEVELOPER_NAME}\n"
            "Build Fingerprint: QM-MIDO-SASUKE-ORIGINAL\n"
            f"Release Date: 2026 • Status: Authentic"
        )
        ctk.CTkLabel(egg_win, text=sig_text, font=("Consolas", 11), justify="center").pack(pady=10)
        ctk.CTkButton(egg_win, text="Close", width=100, command=egg_win.destroy).pack(pady=10)

    def handle_donation(self):
        if DONATION_TYPE == "link":
            webbrowser.open(DONATION_TARGET)
        elif DONATION_TYPE == "crypto":
            self.open_crypto_modal()

    def open_crypto_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Support the Developer")
        modal.geometry("480x240")
        modal.resizable(False, False)
        modal.attributes("-topmost", True)

        ctk.CTkLabel(modal, text="Crypto Donation (Musewallet / Web3)", font=("Segoe UI", 15, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(modal, text="Send to the following public wallet address:", font=("Segoe UI", 11), text_color="#949ba4").pack(pady=(0, 10))

        entry_wallet = ctk.CTkEntry(modal, width=420, height=36, font=("Segoe UI", 11))
        entry_wallet.insert(0, DONATION_TARGET)
        entry_wallet.configure(state="readonly")
        entry_wallet.pack(pady=5)

        lbl_status = ctk.CTkLabel(modal, text="", font=("Segoe UI", 11, "bold"), text_color="#23a55a")
        lbl_status.pack(pady=2)

        def copy_address():
            self.clipboard_clear()
            self.clipboard_append(DONATION_TARGET)
            self.update()
            lbl_status.configure(text="✓ Address copied to clipboard!")

        btn_copy = ctk.CTkButton(modal, text="📋 Copy Address", width=160, height=36, font=("Segoe UI", 12, "bold"), command=copy_address)
        btn_copy.pack(pady=10)

    def toggle_quest(self):
        if self.timer_running:
            self.stop_quest(user_aborted=True)
        else:
            self.start_quest()

    def start_quest(self):
        if not self.selected_game:
            self.lbl_selected.configure(text="Please select a game first!", text_color="#f23f43")
            return

        if not os.path.exists(RUNNER_EXE):
            self.lbl_selected.configure(text="runner.exe is missing from bundle!", text_color="#f23f43")
            return

        exe_name = self.selected_game.get("exe")
        subfolder = self.selected_game.get("subfolder", "")
        game_name = self.selected_game.get("name")
        dur_min = int(self.duration_var.get().split()[0])

        safe_folder = re.sub(r'[<>:"/\\|?*]', "_", game_name)
        self.temp_run_dir = os.path.join(tempfile.gettempdir(), "QuestsMimic", safe_folder, subfolder)
        os.makedirs(self.temp_run_dir, exist_ok=True)

        target_exe_path = os.path.join(self.temp_run_dir, exe_name)

        try:
            shutil.copyfile(RUNNER_EXE, target_exe_path)
            self.active_process = subprocess.Popen([target_exe_path, game_name, str(dur_min)])
        except Exception as e:
            self.lbl_selected.configure(text=f"Failed to launch: {e}", text_color="#f23f43")
            return

        self.total_seconds = dur_min * 60
        self.elapsed_seconds = 0
        self.timer_running = True

        self.btn_toggle.configure(text="Stop Quest", fg_color="#da373c", hover_color="#a8282c")
        self.tick_timer()

    def tick_timer(self):
        if not self.timer_running:
            return

        self.elapsed_seconds += 1
        mins = self.elapsed_seconds // 60
        secs = self.elapsed_seconds % 60
        tot_mins = self.total_seconds // 60
        tot_secs = self.total_seconds % 60

        self.lbl_timer.configure(text=f"{mins:02d}:{secs:02d} / {tot_mins:02d}:{tot_secs:02d}")
        self.progress_bar.set(self.elapsed_seconds / self.total_seconds)

        if self.elapsed_seconds >= self.total_seconds:
            self.stop_quest(user_aborted=False)
            play_sound_native(SOUND_FILE)
        else:
            self.after(1000, self.tick_timer)

    def stop_quest(self, user_aborted=False):
        self.timer_running = False

        if self.active_process:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.active_process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass
            self.active_process = None

        if self.temp_run_dir and os.path.exists(self.temp_run_dir):
            try:
                shutil.rmtree(Path(self.temp_run_dir).parents[0], ignore_errors=True)
            except Exception:
                pass

        self.btn_toggle.configure(text="Launch Quest", fg_color="#248046", hover_color="#1a6334")

        if not user_aborted:
            self.lbl_timer.configure(text="Completed! 100%")
            self.progress_bar.set(1.0)
        else:
            dur_min = int(self.duration_var.get().split()[0])
            self.lbl_timer.configure(text=f"00:00 / {dur_min:02d}:00")
            self.progress_bar.set(0.0)

if __name__ == "__main__":
    app = QuestsMimicApp()
    app.mainloop()
