#!/usr/bin/env python3
"""
DS Typing Trainer
Final version

Features:
- Multi-user profiles
- English / Hindi / Gujarati
- Practice / Speed Test / Exam Mode
- Flexible timer / no timer
- History + Certificate generation
- Unit Converter
- Settings:
  - Theme
  - Font size
  - Per-language font family
  - Per-language font file (.ttf/.otf)
  - Per-language text file (.txt)
- Live typing color:
  - correct = green
  - incorrect = red
"""

import os
import json
import uuid
import ctypes
import datetime
import webbrowser
import tkinter as tk
from ctypes import wintypes
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont

APP_TITLE = "DS Typing Trainer"
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
CERT_DIR = os.path.join(BASE_DIR, "certificates")
APP_DATA_FILE = os.path.join(DATA_DIR, "app_data.json")


# ---------------------- Data Helpers ---------------------- #

def load_app_data():
    if not os.path.exists(APP_DATA_FILE):
        return {"users": {}, "settings": {}}
    try:
        with open(APP_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": {}, "settings": {}}


def save_app_data(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(APP_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_default_settings(data):
    settings = data.get("settings") or {}
    settings.setdefault("exam_thresholds", {
        "en": {"min_wpm": 35, "min_accuracy": 90},
        "hi": {"min_wpm": 30, "min_accuracy": 90},
        "gu": {"min_wpm": 30, "min_accuracy": 90},
    })
    settings.setdefault("theme", "light")
    settings.setdefault("font_size", "medium")

    settings.setdefault("fonts", {
        "en": {"family": "Consolas", "file": ""},
        "hi": {"family": "Mangal", "file": ""},
        "gu": {"family": "Shruti", "file": ""},
    })

    settings.setdefault("text_files", {
        "en": "",
        "hi": "",
        "gu": "",
    })

    data["settings"] = settings
    return data


def load_font_file_windows(font_path):
    if not font_path or not os.path.exists(font_path):
        return False
    FR_PRIVATE = 0x10
    FR_NOT_ENUM = 0x20
    try:
        add_font = ctypes.windll.gdi32.AddFontResourceExW
        add_font.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.PVOID]
        add_font.restype = wintypes.INT
        result = add_font(font_path, FR_PRIVATE | FR_NOT_ENUM, 0)
        return result > 0
    except Exception:
        return False


def get_language_font_settings(app_data, lang_code):
    settings = app_data.get("settings", {})
    fonts = settings.get("fonts", {})
    entry = fonts.get(lang_code, {})
    if isinstance(entry, dict):
        return entry.get("family", ""), entry.get("file", "")
    return str(entry), ""


def get_language_text_file(app_data, lang_code):
    settings = app_data.get("settings", {})
    text_files = settings.get("text_files", {})
    return text_files.get(lang_code, "")


def read_text_file(path):
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="cp1252", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def compute_metrics(target_text, typed_text, duration_seconds):
    target = target_text.replace("\r\n", "\n")
    typed = typed_text.replace("\r\n", "\n")

    total_chars = len(typed)
    min_len = min(len(target), len(typed))
    errors = 0

    for i in range(min_len):
        if target[i] != typed[i]:
            errors += 1

    errors += abs(len(target) - len(typed))

    minutes = max(duration_seconds / 60.0, 0.01)
    gross_wpm = (total_chars / 5.0) / minutes
    error_words = errors / 5.0
    net_wpm = max(gross_wpm - (error_words / minutes), 0)

    accuracy = 0.0
    if total_chars > 0:
        accuracy = max(0.0, 100.0 * (1.0 - (errors / float(total_chars))))

    return {
        "gross_wpm": round(gross_wpm, 2),
        "net_wpm": round(net_wpm, 2),
        "accuracy": round(accuracy, 2),
        "total_chars": total_chars,
        "errors": errors,
    }


def generate_certificate_html(user_name, record, institute_name="DS COMPUTER AND COACHING CLASSES"):
    os.makedirs(CERT_DIR, exist_ok=True)
    cert_id = record.get("cert_id") or str(uuid.uuid4())[:8].upper()
    record["cert_id"] = cert_id
    file_path = os.path.join(CERT_DIR, f"certificate_{cert_id}.html")

    date_str = record.get("date", "")
    lang_label = {"en": "English", "hi": "Hindi", "gu": "Gujarati"}.get(record.get("language", "en"), "English")
    mode = record.get("mode", "Practice")
    wpm = record.get("net_wpm", 0)
    acc = record.get("accuracy", 0)
    duration_min = round(record.get("duration_sec", 0) / 60, 2)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Typing Certificate - {cert_id}</title>
<style>
body {{
    font-family: Arial, sans-serif;
    background: #f2f2f2;
}}
.certificate {{
    width: 800px;
    margin: 40px auto;
    padding: 40px;
    background: #ffffff;
    border: 8px solid #2c3e50;
    box-shadow: 0 0 10px rgba(0,0,0,0.2);
}}
.cert-title {{
    text-align: center;
    font-size: 28px;
    font-weight: bold;
    margin-bottom: 10px;
}}
.cert-subtitle {{
    text-align: center;
    font-size: 18px;
    margin-bottom: 30px;
}}
.cert-body {{
    font-size: 18px;
    line-height: 1.6;
}}
.cert-row {{
    margin: 10px 0;
}}
.bold {{
    font-weight: bold;
}}
.footer {{
    margin-top: 40px;
    display: flex;
    justify-content: space-between;
}}
.footer div {{
    width: 45%;
    text-align: center;
}}
</style>
</head>
<body>
<div class="certificate">
    <div class="cert-title">Certificate of Typing Proficiency</div>
    <div class="cert-subtitle">{institute_name}</div>
    <div class="cert-body">
        <p class="cert-row">This is to certify that <span class="bold">{user_name}</span> has successfully completed a typing test in <span class="bold">{lang_label}</span>.</p>
        <p class="cert-row">Test Mode: <span class="bold">{mode}</span></p>
        <p class="cert-row">Net Speed: <span class="bold">{wpm} WPM</span> &nbsp;&nbsp; Accuracy: <span class="bold">{acc}%</span></p>
        <p class="cert-row">Test Duration: <span class="bold">{duration_min} minutes</span></p>
        <p class="cert-row">Date of Test: <span class="bold">{date_str}</span></p>
        <p class="cert-row">Certificate ID: <span class="bold">{cert_id}</span></p>
    </div>
    <div class="footer">
        <div>
            ___________________________<br>
            Candidate Signature
        </div>
        <div>
            ___________________________<br>
            Authorized Signature
        </div>
    </div>
</div>
</body>
</html>"""

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)
    return file_path, cert_id


LESSONS = {
    "en": {
        "beginner": [
            "asdf jkl; asdf jkl; asdf jkl;",
            "asdf asdf jkl; jkl; asdf jkl;",
        ],
        "words": [
            "home row typing practice speed accuracy keyboard",
        ],
        "paragraphs": [
            "Typing is a very important skill for students and office workers.\nWith regular practice, you can increase your speed and accuracy.",
        ],
        "numbers": [
            "12345 67890 11223 44556 77889 99001",
        ],
    },
    "hi": {
        "beginner": [
            "क ख ग घ क ख ग घ",
            "अ आ इ ई अ आ इ ई",
        ],
        "words": [
            "कंप्यूटर टाइपिंग अभ्यास गति सटीकता",
        ],
        "paragraphs": [
            "नियमित प्रैक्टिस से टाइपिंग स्पीड और सटीकता दोनों बढ़ती हैं।\nसरल शब्दों और वाक्यों से शुरुआत करना अच्छा रहता है।",
        ],
        "numbers": [
            "१२३४५ ६७८९० ११२२३ ४४५५६ ७७८८९",
        ],
    },
    "gu": {
        "beginner": [
            "ક ખ ગ ઘ ક ખ ગ ઘ",
            "અ આ ઇ ઈ અ આ ઇ ઈ",
        ],
        "words": [
            "કમ્પ્યુટર ટાઈપિંગ પ્રેક્ટિસ ઝડપ ચોકસાઈ",
        ],
        "paragraphs": [
            "દરરોજ ટાઈપિંગ પ્રેક્ટિસ કરવાથી ઝડપ અને ચોકસાઈ બન્ને સુધરે છે.\nટાઈપિંગ કૌશલ્યથી સરકારી તેમજ ખાનગી નોકરીમાં મદદ મળે છે.",
        ],
        "numbers": [
            "૧૨૩૪૫ ૬૭૮૯૦ ૧૧૨૨૩ ૪૪૫૫૬ ૭૭૮૮૯",
        ],
    },
}

LANG_LABELS = {"en": "English", "hi": "Hindi", "gu": "Gujarati"}


# ---------------------- Main App ---------------------- #

class TypingTrainerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x700")
        self.minsize(950, 620)

        self.app_data = ensure_default_settings(load_app_data())
        self.current_user = None
        self.current_user_profile = None

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (LoginFrame, MainMenuFrame, PracticeSetupFrame, TypingSessionFrame, HistoryFrame, SettingsFrame):
            frame = F(parent=container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("LoginFrame")

        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Unit Converter", command=self.open_unit_converter)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="Tools", menu=file_menu)

        user_menu = tk.Menu(menubar, tearoff=0)
        user_menu.add_command(label="Settings", command=lambda: self.show_frame("SettingsFrame"))
        user_menu.add_command(label="History & Certificates", command=lambda: self.show_frame("HistoryFrame"))
        user_menu.add_separator()
        user_menu.add_command(label="Logout", command=self.logout)
        menubar.add_cascade(label="User", menu=user_menu)

        self.config(menu=menubar)

    def show_frame(self, name):
        frame = self.frames.get(name)
        if frame:
            frame.tkraise()
            if hasattr(frame, "on_show"):
                frame.on_show()

    def logout(self):
        self.current_user = None
        self.current_user_profile = None
        self.show_frame("LoginFrame")

    def get_user_profile(self, username):
        return self.app_data.get("users", {}).get(username)

    def save_user_profile(self, username, profile):
        self.app_data.setdefault("users", {})
        self.app_data["users"][username] = profile
        save_app_data(self.app_data)

    def login_user(self, username):
        self.current_user = username
        self.current_user_profile = self.get_user_profile(username)
        self.show_frame("MainMenuFrame")

    def add_history_record(self, record):
        if not self.current_user:
            return
        profile = self.current_user_profile or {}
        history = profile.get("history") or []
        history.append(record)
        profile["history"] = history
        self.current_user_profile = profile
        self.save_user_profile(self.current_user, profile)

    def open_certificate(self, record):
        if not self.current_user:
            return
        file_path, cert_id = generate_certificate_html(self.current_user, record)
        self.save_user_profile(self.current_user, self.current_user_profile)
        try:
            webbrowser.open(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open certificate file.\n{e}")

    def open_unit_converter(self):
        UnitConverterWindow(self)


# ---------------------- Login ---------------------- #

class LoginFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text=APP_TITLE, font=("Arial", 22, "bold")).grid(row=0, column=0, pady=(40, 10))
        ttk.Label(self, text="English / Hindi / Gujarati Typing Trainer", font=("Arial", 12)).grid(row=1, column=0, pady=(0, 25))

        card = ttk.Frame(self)
        card.grid(row=2, column=0, pady=10)

        ttk.Label(card, text="Username:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(card, textvariable=self.username_var, width=25)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(card, text="PIN (optional):").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.pin_var = tk.StringVar()
        self.pin_entry = ttk.Entry(card, textvariable=self.pin_var, show="*", width=25)
        self.pin_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(card, text="Default Language:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.lang_var = tk.StringVar(value="en - English")
        self.lang_combo = ttk.Combobox(card, textvariable=self.lang_var, state="readonly",
                                       values=["en - English", "hi - Hindi", "gu - Gujarati"], width=22)
        self.lang_combo.grid(row=2, column=1, padx=5, pady=5)
        self.lang_combo.current(0)

        ttk.Button(card, text="Login / Create Profile", command=self.login_or_create).grid(row=3, column=0, columnspan=2, pady=12)

    def on_show(self):
        self.username_var.set("")
        self.pin_var.set("")
        self.username_entry.focus_set()

    def login_or_create(self):
        username = self.username_var.get().strip()
        pin = self.pin_var.get().strip()

        if not username:
            messagebox.showwarning("Input Required", "Please enter a username.")
            return

        users = self.controller.app_data.get("users", {})
        if username in users:
            profile = users[username]
            saved_pin = profile.get("pin", "")
            if saved_pin and saved_pin != pin:
                messagebox.showerror("Incorrect PIN", "Wrong PIN.")
                return
            self.controller.login_user(username)
        else:
            lang_code = self.lang_var.get().split(" - ")[0]
            profile = {
                "pin": pin,
                "default_language": lang_code,
                "history": []
            }
            self.controller.save_user_profile(username, profile)
            self.controller.login_user(username)


# ---------------------- Main Menu ---------------------- #

class MainMenuFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text="Main Menu", font=("Arial", 20, "bold")).grid(row=0, column=0, pady=(35, 10))
        self.user_label = ttk.Label(self, text="", font=("Arial", 12))
        self.user_label.grid(row=1, column=0, pady=(0, 20))

        btns = ttk.Frame(self)
        btns.grid(row=2, column=0, pady=10)

        items = [
            ("Practice Mode", lambda: self.open_mode("practice")),
            ("Speed Test", lambda: self.open_mode("speed")),
            ("Exam Mode (Govt Style)", lambda: self.open_mode("exam")),
            ("History & Certificates", lambda: self.controller.show_frame("HistoryFrame")),
            ("Unit Converter", self.controller.open_unit_converter),
            ("Settings", lambda: self.controller.show_frame("SettingsFrame")),
            ("Logout", self.controller.logout),
        ]

        for i, (txt, cmd) in enumerate(items):
            ttk.Button(btns, text=txt, width=32, command=cmd).grid(row=i, column=0, pady=5)

    def on_show(self):
        if self.controller.current_user:
            profile = self.controller.current_user_profile or {}
            lang = profile.get("default_language", "en")
            self.user_label.config(text=f"Logged in as: {self.controller.current_user} | Default language: {LANG_LABELS.get(lang)}")

    def open_mode(self, mode):
        frame = self.controller.frames["PracticeSetupFrame"]
        frame.set_mode(mode)
        self.controller.show_frame("PracticeSetupFrame")


# ---------------------- Practice Setup ---------------------- #

class PracticeSetupFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.mode = "practice"
        self.loaded_file_text = ""

        self.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(self, text="Setup", font=("Arial", 18, "bold"))
        self.title_label.grid(row=0, column=0, pady=(20, 10))

        form = ttk.Frame(self)
        form.grid(row=1, column=0, pady=10)

        ttk.Label(form, text="Language:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.lang_var = tk.StringVar(value="en - English")
        self.lang_combo = ttk.Combobox(form, textvariable=self.lang_var, state="readonly",
                                       values=["en - English", "hi - Hindi", "gu - Gujarati"], width=25)
        self.lang_combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form, text="Content Type:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.content_var = tk.StringVar(value="paragraphs")
        self.content_combo = ttk.Combobox(form, textvariable=self.content_var, state="readonly",
                                          values=["beginner", "words", "paragraphs", "numbers", "custom", "text_file"], width=25)
        self.content_combo.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        self.content_combo.bind("<<ComboboxSelected>>", self.on_content_change)

        ttk.Label(form, text="Duration (minutes):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.duration_var = tk.StringVar(value="5")
        self.duration_entry = ttk.Entry(form, textvariable=self.duration_var, width=12)
        self.duration_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        self.no_timer_var = tk.BooleanVar(value=False)
        self.no_timer_check = ttk.Checkbutton(form, text="No timer (unlimited)", variable=self.no_timer_var, command=self.toggle_timer)
        self.no_timer_check.grid(row=3, column=1, sticky="w", padx=5, pady=5)

        self.exam_info_label = ttk.Label(form, text="", foreground="darkred", font=("Arial", 9, "italic"))
        self.exam_info_label.grid(row=4, column=0, columnspan=2, pady=(5, 0))

        self.custom_label = ttk.Label(self, text="Custom Text:")
        self.custom_text = tk.Text(self, height=8, wrap="word")

        self.file_btn = ttk.Button(self, text="Choose .txt file", command=self.choose_text_file)
        self.file_label_var = tk.StringVar(value="No .txt file selected")
        self.file_label = ttk.Label(self, textvariable=self.file_label_var)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=5, column=0, pady=15)
        ttk.Button(btn_frame, text="Start", command=self.start_session).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Back", command=lambda: self.controller.show_frame("MainMenuFrame")).grid(row=0, column=1, padx=5)

    def on_show(self):
        profile = self.controller.current_user_profile or {}
        lang = profile.get("default_language", "en")
        mapping = {"en": 0, "hi": 1, "gu": 2}
        self.lang_combo.current(mapping.get(lang, 0))

        self.loaded_file_text = ""
        self.file_label_var.set("No .txt file selected")

        if self.mode == "practice":
            self.duration_var.set("5")
        elif self.mode == "speed":
            self.duration_var.set("5")
        else:
            self.duration_var.set("10")

        self.no_timer_var.set(False)
        self.toggle_timer()
        self.update_exam_info()
        self.on_content_change()

    def set_mode(self, mode):
        self.mode = mode
        titles = {
            "practice": "Practice Setup",
            "speed": "Speed Test Setup",
            "exam": "Exam Mode Setup"
        }
        self.title_label.config(text=titles.get(mode, "Setup"))
        self.update_exam_info()

    def toggle_timer(self):
        if self.no_timer_var.get():
            self.duration_entry.configure(state="disabled")
        else:
            self.duration_entry.configure(state="normal")

    def update_exam_info(self):
        if self.mode == "exam":
            thresholds = self.controller.app_data.get("settings", {}).get("exam_thresholds", {})
            txt = []
            for code, label in LANG_LABELS.items():
                t = thresholds.get(code, {})
                txt.append(f"{label}: {t.get('min_wpm', 0)} WPM, {t.get('min_accuracy', 0)}%")
            self.exam_info_label.config(text="Exam pass criteria: " + " | ".join(txt))
        else:
            self.exam_info_label.config(text="")

    def on_content_change(self, event=None):
        self.custom_label.grid_forget()
        self.custom_text.grid_forget()
        self.file_btn.grid_forget()
        self.file_label.grid_forget()

        ct = self.content_var.get()
        if ct == "custom":
            self.custom_label.grid(row=2, column=0, pady=(5, 0))
            self.custom_text.grid(row=3, column=0, padx=20, sticky="nsew")
        elif ct == "text_file":
            self.file_btn.grid(row=2, column=0, pady=(5, 0))
            self.file_label.grid(row=3, column=0, padx=20, sticky="w")

    def choose_text_file(self):
        path = filedialog.askopenfilename(title="Select text file", filetypes=[("Text files", "*.txt")])
        if path:
            self.loaded_file_text = read_text_file(path)
            self.file_label_var.set(os.path.basename(path))

    def start_session(self):
        lang_code = self.lang_var.get().split(" - ")[0]
        content_type = self.content_var.get()

        if content_type == "custom":
            selected_text = self.custom_text.get("1.0", "end-1c")
            if not selected_text.strip():
                messagebox.showwarning("Custom Text", "Please enter text.")
                return

        elif content_type == "text_file":
            if self.loaded_file_text.strip():
                selected_text = self.loaded_file_text
            else:
                saved_file = get_language_text_file(self.controller.app_data, lang_code)
                selected_text = read_text_file(saved_file)
                if not selected_text.strip():
                    messagebox.showwarning("Text File", "Please choose a .txt file here or set one in Settings.")
                    return
        else:
            if content_type == "paragraphs":
                saved_file = get_language_text_file(self.controller.app_data, lang_code)
                selected_text = read_text_file(saved_file)
                if not selected_text.strip():
                    lessons = LESSONS.get(lang_code, {}).get(content_type) or []
                    if not lessons:
                        messagebox.showerror("No Content", "No paragraph found.")
                        return
                    selected_text = lessons[0]
            else:
                lessons = LESSONS.get(lang_code, {}).get(content_type) or []
                if not lessons:
                    messagebox.showerror("No Content", "No lesson content found.")
                    return
                selected_text = lessons[0]

        duration_minutes = 0
        if not self.no_timer_var.get():
            try:
                duration_minutes = int(self.duration_var.get())
                if duration_minutes <= 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Invalid Duration", "Enter valid minutes.")
                return

        session_frame = self.controller.frames["TypingSessionFrame"]
        session_frame.start_new_session(
            mode=self.mode,
            language=lang_code,
            target_text=selected_text,
            duration_minutes=duration_minutes if not self.no_timer_var.get() else 0,
            no_timer=self.no_timer_var.get(),
            content_type=content_type
        )
        self.controller.show_frame("TypingSessionFrame")


# ---------------------- Typing Session ---------------------- #

class TypingSessionFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.mode = "practice"
        self.language = "en"
        self.target_text = ""
        self.duration_seconds = 0
        self.no_timer = False
        self.content_type = ""
        self.start_time = None
        self.timer_id = None
        self.backspace_disabled = False

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self.header_label = ttk.Label(self, text="Typing Session", font=("Arial", 18, "bold"))
        self.header_label.grid(row=0, column=0, pady=(15, 5))

        self.info_label = ttk.Label(self, text="", font=("Arial", 10))
        self.info_label.grid(row=1, column=0, pady=(0, 5))

        stats = ttk.Frame(self)
        stats.grid(row=2, column=0, pady=5)

        self.time_var = tk.StringVar(value="Time: 00:00")
        self.wpm_var = tk.StringVar(value="Net WPM: 0")
        self.acc_var = tk.StringVar(value="Accuracy: 0%")

        ttk.Label(stats, textvariable=self.time_var, width=18).grid(row=0, column=0, padx=5)
        ttk.Label(stats, textvariable=self.wpm_var, width=18).grid(row=0, column=1, padx=5)
        ttk.Label(stats, textvariable=self.acc_var, width=18).grid(row=0, column=2, padx=5)

        self.target_box = tk.Text(self, height=10, wrap="word", state="disabled", bg="#f4f4f4")
        self.target_box.grid(row=3, column=0, padx=20, pady=(5, 5), sticky="nsew")

        self.input_box = tk.Text(self, height=12, wrap="word")
        self.input_box.grid(row=4, column=0, padx=20, pady=(5, 5), sticky="nsew")

        self.input_box.tag_configure("correct", foreground="green")
        self.input_box.tag_configure("incorrect", foreground="red")

        btns = ttk.Frame(self)
        btns.grid(row=5, column=0, pady=10)
        ttk.Button(btns, text="Finish", command=self.finish_session).grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="Cancel", command=self.cancel_session).grid(row=0, column=1, padx=5)

        self.input_box.bind("<KeyRelease>", self.on_key_release)
        self.input_box.bind("<Key>", self.on_key_press)

    def on_show(self):
        self.input_box.focus_set()

    def apply_font(self):
        settings = self.controller.app_data.get("settings", {})
        size_name = settings.get("font_size", "medium")
        size_map = {"small": 11, "medium": 14, "large": 18}
        size = size_map.get(size_name, 14)

        family, font_file = get_language_font_settings(self.controller.app_data, self.language)
        if font_file:
            load_font_file_windows(font_file)

        if not family:
            family = {"en": "Consolas", "hi": "Mangal", "gu": "Shruti"}.get(self.language, "Consolas")

        try:
            f = tkfont.Font(family=family, size=size)
        except Exception:
            f = tkfont.Font(size=size)

        self.target_box.configure(font=f)
        self.input_box.configure(font=f)

    def start_new_session(self, mode, language, target_text, duration_minutes, no_timer, content_type):
        self.mode = mode
        self.language = language
        self.target_text = target_text
        self.duration_seconds = duration_minutes * 60
        self.no_timer = no_timer
        self.content_type = content_type
        self.start_time = datetime.datetime.now()
        self.backspace_disabled = (mode == "exam")

        self.header_label.config(text=f"{mode.capitalize()} - {LANG_LABELS.get(language, 'English')}")
        if self.backspace_disabled:
            self.info_label.config(text="Backspace disabled (Exam mode).")
        else:
            self.info_label.config(text="")

        self.target_box.configure(state="normal")
        self.target_box.delete("1.0", "end")
        self.target_box.insert("1.0", self.target_text)
        self.target_box.configure(state="disabled")

        self.input_box.delete("1.0", "end")
        self.time_var.set("Time: 00:00")
        self.wpm_var.set("Net WPM: 0")
        self.acc_var.set("Accuracy: 0%")

        self.apply_font()

        if self.timer_id:
            self.after_cancel(self.timer_id)
        self.timer_id = self.after(1000, self.update_timer)

    def update_timer(self):
        if not self.start_time:
            return

        elapsed = (datetime.datetime.now() - self.start_time).total_seconds()
        remaining = max(self.duration_seconds - elapsed, 0) if self.duration_seconds > 0 else 0

        if self.duration_seconds > 0:
            m = int(remaining) // 60
            s = int(remaining) % 60
            self.time_var.set(f"Time left: {m:02d}:{s:02d}")
        else:
            m = int(elapsed) // 60
            s = int(elapsed) % 60
            self.time_var.set(f"Time: {m:02d}:{s:02d}")

        typed = self.input_box.get("1.0", "end-1c")
        metrics = compute_metrics(self.target_text, typed, max(elapsed, 1))
        self.wpm_var.set(f"Net WPM: {metrics['net_wpm']}")
        self.acc_var.set(f"Accuracy: {metrics['accuracy']}%")

        if self.duration_seconds > 0 and remaining <= 0:
            self.finish_session()
            return

        self.timer_id = self.after(1000, self.update_timer)

    def highlight_typed_text(self):
        typed = self.input_box.get("1.0", "end-1c")
        target = self.target_text

        self.input_box.tag_remove("correct", "1.0", "end")
        self.input_box.tag_remove("incorrect", "1.0", "end")

        for i, ch in enumerate(typed):
            start = f"1.0+{i}c"
            end = f"1.0+{i+1}c"
            if i < len(target) and ch == target[i]:
                self.input_box.tag_add("correct", start, end)
            else:
                self.input_box.tag_add("incorrect", start, end)

    def on_key_release(self, event):
        self.highlight_typed_text()

    def on_key_press(self, event):
        if self.backspace_disabled and event.keysym == "BackSpace":
            return "break"

    def finish_session(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None

        if not self.start_time:
            self.controller.show_frame("MainMenuFrame")
            return

        end_time = datetime.datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        if self.duration_seconds > 0:
            duration = min(duration, self.duration_seconds)

        typed = self.input_box.get("1.0", "end-1c")
        metrics = compute_metrics(self.target_text, typed, max(duration, 1))
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        passed = None
        if self.mode == "exam":
            thresholds = self.controller.app_data.get("settings", {}).get("exam_thresholds", {})
            t = thresholds.get(self.language, {"min_wpm": 0, "min_accuracy": 0})
            passed = metrics["net_wpm"] >= t.get("min_wpm", 0) and metrics["accuracy"] >= t.get("min_accuracy", 0)

        record = {
            "id": str(uuid.uuid4()),
            "date": now_str,
            "language": self.language,
            "mode": self.mode,
            "content_type": self.content_type,
            "gross_wpm": metrics["gross_wpm"],
            "net_wpm": metrics["net_wpm"],
            "accuracy": metrics["accuracy"],
            "total_chars": metrics["total_chars"],
            "errors": metrics["errors"],
            "duration_sec": duration,
            "passed": passed,
            "cert_id": None,
        }

        self.controller.add_history_record(record)
        ResultDialog(self, self.controller, record)
        self.start_time = None

    def cancel_session(self):
        if messagebox.askyesno("Cancel", "Cancel this session?"):
            if self.timer_id:
                self.after_cancel(self.timer_id)
                self.timer_id = None
            self.start_time = None
            self.controller.show_frame("MainMenuFrame")


# ---------------------- History ---------------------- #

class HistoryFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        ttk.Label(self, text="History & Certificates", font=("Arial", 18, "bold")).grid(row=0, column=0, pady=(20, 5))
        self.info_label = ttk.Label(self, text="", font=("Arial", 10))
        self.info_label.grid(row=1, column=0, pady=(0, 5))

        columns = ("date", "language", "mode", "net_wpm", "accuracy", "duration", "passed", "cert")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        self.tree.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")

        headings = {
            "date": "Date/Time",
            "language": "Lang",
            "mode": "Mode",
            "net_wpm": "Net WPM",
            "accuracy": "Accuracy",
            "duration": "Minutes",
            "passed": "Result",
            "cert": "Certificate",
        }
        for col, txt in headings.items():
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=110, anchor="center")

        btns = ttk.Frame(self)
        btns.grid(row=3, column=0, pady=10)
        ttk.Button(btns, text="View Details", command=self.view_details).grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="Generate/View Certificate", command=self.view_certificate).grid(row=0, column=1, padx=5)
        ttk.Button(btns, text="Back", command=lambda: self.controller.show_frame("MainMenuFrame")).grid(row=0, column=2, padx=5)

    def on_show(self):
        self.reload_history()

    def reload_history(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        if not self.controller.current_user:
            self.info_label.config(text="No user selected.")
            return

        history = (self.controller.current_user_profile or {}).get("history", [])
        self.info_label.config(text=f"User: {self.controller.current_user} | Total sessions: {len(history)}")

        for rec in history:
            lang = LANG_LABELS.get(rec.get("language", "en"), "English")[:3]
            mode = rec.get("mode", "practice").capitalize()
            duration = round(rec.get("duration_sec", 0) / 60, 2)
            passed = rec.get("passed")
            if passed is True:
                result = "Pass"
            elif passed is False:
                result = "Fail"
            else:
                result = "-"
            cert = rec.get("cert_id") or "-"
            self.tree.insert("", "end", iid=rec.get("id"), values=(
                rec.get("date", ""),
                lang,
                mode,
                rec.get("net_wpm", 0),
                rec.get("accuracy", 0),
                duration,
                result,
                cert
            ))

    def get_selected_record(self):
        sel = self.tree.focus()
        if not sel:
            return None
        history = (self.controller.current_user_profile or {}).get("history", [])
        for rec in history:
            if rec.get("id") == sel:
                return rec
        return None

    def view_details(self):
        rec = self.get_selected_record()
        if not rec:
            messagebox.showinfo("Select", "Please select a record.")
            return
        ResultDialog(self, self.controller, rec, from_history=True)

    def view_certificate(self):
        rec = self.get_selected_record()
        if not rec:
            messagebox.showinfo("Select", "Please select a record.")
            return
        self.controller.open_certificate(rec)
        self.reload_history()


# ---------------------- Settings ---------------------- #

class SettingsFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.columnconfigure(0, weight=1)

        ttk.Label(self, text="Settings", font=("Arial", 18, "bold")).grid(row=0, column=0, pady=(20, 10))
        self.info_label = ttk.Label(self, text="", font=("Arial", 10))
        self.info_label.grid(row=1, column=0, pady=(0, 10))

        form = ttk.Frame(self)
        form.grid(row=2, column=0, pady=10)

        row = 0
        ttk.Label(form, text="Theme:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.theme_var = tk.StringVar(value="light")
        self.theme_combo = ttk.Combobox(form, textvariable=self.theme_var, state="readonly",
                                        values=["light", "dark"], width=18)
        self.theme_combo.grid(row=row, column=1, sticky="w", padx=5, pady=5)

        row += 1
        ttk.Label(form, text="Font size:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.font_size_var = tk.StringVar(value="medium")
        self.font_combo = ttk.Combobox(form, textvariable=self.font_size_var, state="readonly",
                                       values=["small", "medium", "large"], width=18)
        self.font_combo.grid(row=row, column=1, sticky="w", padx=5, pady=5)

        row += 1
        ttk.Separator(form, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)

        row += 1
        ttk.Label(form, text="Language settings:", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=3, pady=(4, 8))

        row += 1
        ttk.Label(form, text="Choose language:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.lang_select_var = tk.StringVar(value="en")
        self.lang_select_combo = ttk.Combobox(form, textvariable=self.lang_select_var, state="readonly",
                                              values=["en", "hi", "gu"], width=18)
        self.lang_select_combo.grid(row=row, column=1, sticky="w", padx=5, pady=5)
        self.lang_select_combo.bind("<<ComboboxSelected>>", self.load_language_specific_settings)

        row += 1
        ttk.Label(form, text="Font family:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.lang_font_family_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.lang_font_family_var, width=35).grid(row=row, column=1, sticky="w", padx=5, pady=5)

        row += 1
        ttk.Label(form, text="Font file:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.lang_font_file_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.lang_font_file_var, width=35).grid(row=row, column=1, sticky="w", padx=5, pady=5)
        ttk.Button(form, text="Browse Font", command=self.browse_font_file).grid(row=row, column=2, sticky="w", padx=5, pady=5)

        row += 1
        ttk.Label(form, text="Text file (.txt):").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.lang_text_file_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.lang_text_file_var, width=35).grid(row=row, column=1, sticky="w", padx=5, pady=5)
        ttk.Button(form, text="Browse Text", command=self.browse_text_file).grid(row=row, column=2, sticky="w", padx=5, pady=5)

        row += 1
        ttk.Button(form, text="Apply Language Settings", command=self.apply_language_settings).grid(row=row, column=0, columnspan=3, pady=(5, 10))

        row += 1
        ttk.Separator(form, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)

        row += 1
        ttk.Label(form, text="Exam thresholds (Net WPM / Accuracy%)").grid(row=row, column=0, columnspan=3, pady=(10, 5))

        row += 1
        self.exam_entries = {}
        for code, label in LANG_LABELS.items():
            ttk.Label(form, text=f"{label}:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
            frame = ttk.Frame(form)
            frame.grid(row=row, column=1, sticky="w", padx=5, pady=2, columnspan=2)
            wpm_var = tk.StringVar()
            acc_var = tk.StringVar()
            ttk.Entry(frame, textvariable=wpm_var, width=5).grid(row=0, column=0)
            ttk.Label(frame, text="WPM").grid(row=0, column=1, padx=3)
            ttk.Entry(frame, textvariable=acc_var, width=5).grid(row=0, column=2)
            ttk.Label(frame, text="%").grid(row=0, column=3, padx=3)
            self.exam_entries[code] = (wpm_var, acc_var)
            row += 1

        btns = ttk.Frame(self)
        btns.grid(row=3, column=0, pady=15)
        ttk.Button(btns, text="Save Settings", command=self.save_settings).grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="Back", command=lambda: self.controller.show_frame("MainMenuFrame")).grid(row=0, column=1, padx=5)

    def on_show(self):
        settings = self.controller.app_data.get("settings", {})
        self.theme_var.set(settings.get("theme", "light"))
        self.font_size_var.set(settings.get("font_size", "medium"))

        thresholds = settings.get("exam_thresholds", {})
        for code in LANG_LABELS:
            t = thresholds.get(code, {})
            self.exam_entries[code][0].set(str(t.get("min_wpm", 0)))
            self.exam_entries[code][1].set(str(t.get("min_accuracy", 0)))

        self.lang_select_var.set("en")
        self.load_language_specific_settings()

        if self.controller.current_user:
            self.info_label.config(text=f"User: {self.controller.current_user}")
        else:
            self.info_label.config(text="No user logged in.")

    def load_language_specific_settings(self, event=None):
        lang = self.lang_select_var.get()
        family, font_file = get_language_font_settings(self.controller.app_data, lang)
        text_file = get_language_text_file(self.controller.app_data, lang)
        self.lang_font_family_var.set(family)
        self.lang_font_file_var.set(font_file)
        self.lang_text_file_var.set(text_file)

    def browse_font_file(self):
        path = filedialog.askopenfilename(title="Choose font file", filetypes=[("Font files", "*.ttf *.otf")])
        if path:
            self.lang_font_file_var.set(path)

    def browse_text_file(self):
        path = filedialog.askopenfilename(title="Choose text file", filetypes=[("Text files", "*.txt")])
        if path:
            self.lang_text_file_var.set(path)

    def apply_language_settings(self):
        data = self.controller.app_data
        settings = data.get("settings", {})
        fonts = settings.get("fonts", {})
        text_files = settings.get("text_files", {})

        lang = self.lang_select_var.get()
        fonts[lang] = {
            "family": self.lang_font_family_var.get().strip(),
            "file": self.lang_font_file_var.get().strip(),
        }
        text_files[lang] = self.lang_text_file_var.get().strip()

        settings["fonts"] = fonts
        settings["text_files"] = text_files
        data["settings"] = settings
        save_app_data(data)
        self.controller.app_data = data

        messagebox.showinfo("Saved", f"{LANG_LABELS.get(lang, lang)} language settings saved.")

    def save_settings(self):
        data = self.controller.app_data
        settings = data.get("settings", {})
        settings["theme"] = self.theme_var.get()
        settings["font_size"] = self.font_size_var.get()

        thresholds = {}
        for code in LANG_LABELS:
            try:
                min_wpm = int(self.exam_entries[code][0].get())
                min_acc = int(self.exam_entries[code][1].get())
            except Exception:
                messagebox.showerror("Invalid Input", "Enter valid exam threshold numbers.")
                return
            thresholds[code] = {"min_wpm": min_wpm, "min_accuracy": min_acc}

        settings["exam_thresholds"] = thresholds
        data["settings"] = settings
        save_app_data(data)
        self.controller.app_data = data
        messagebox.showinfo("Saved", "Settings saved successfully.")


# ---------------------- Result Dialog ---------------------- #

class ResultDialog(tk.Toplevel):
    def __init__(self, parent, controller, record, from_history=False):
        super().__init__(parent)
        self.controller = controller
        self.record = record

        self.title("Session Result")
        self.geometry("430x340")
        self.resizable(False, False)

        ttk.Label(self, text=f"{record.get('mode', 'practice').capitalize()} Result - {LANG_LABELS.get(record.get('language', 'en'))}",
                  font=("Arial", 14, "bold")).pack(pady=(10, 5))

        frame = ttk.Frame(self)
        frame.pack(padx=10, pady=5, fill="x")

        def add_row(label, value):
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=label + ":", width=18).pack(side="left")
            ttk.Label(row, text=str(value)).pack(side="left")

        add_row("Date/Time", record.get("date", ""))
        add_row("Gross WPM", record.get("gross_wpm", 0))
        add_row("Net WPM", record.get("net_wpm", 0))
        add_row("Accuracy", f"{record.get('accuracy', 0)}%")
        add_row("Total Chars", record.get("total_chars", 0))
        add_row("Errors", record.get("errors", 0))
        add_row("Duration (min)", round(record.get("duration_sec", 0) / 60, 2))

        passed = record.get("passed")
        if passed is not None:
            add_row("Exam Result", "PASS" if passed else "FAIL")

        btns = ttk.Frame(self)
        btns.pack(pady=12)
        ttk.Button(btns, text="Close", command=self.destroy).grid(row=0, column=0, padx=5)

        if record.get("mode") in ("speed", "exam"):
            ttk.Button(btns, text="Generate/View Certificate", command=self.open_certificate).grid(row=0, column=1, padx=5)

        if not from_history:
            ttk.Button(btns, text="Back to Main Menu", command=self.back_to_menu).grid(row=1, column=0, columnspan=2, pady=(6, 0))

    def open_certificate(self):
        self.controller.open_certificate(self.record)

    def back_to_menu(self):
        self.destroy()
        self.controller.show_frame("MainMenuFrame")


# ---------------------- Unit Converter ---------------------- #

class UnitConverterWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Unit Converter")
        self.geometry("430x270")
        self.resizable(False, False)

        ttk.Label(self, text="Unit Converter", font=("Arial", 14, "bold")).pack(pady=(10, 5))

        self.category_var = tk.StringVar(value="Length")
        self.from_unit_var = tk.StringVar()
        self.to_unit_var = tk.StringVar()
        self.value_var = tk.StringVar()
        self.result_var = tk.StringVar()

        main = ttk.Frame(self)
        main.pack(padx=10, pady=5, fill="x")

        ttk.Label(main, text="Category:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.category_combo = ttk.Combobox(main, textvariable=self.category_var, state="readonly",
                                           values=["Length", "Weight", "Temperature", "Time", "Area", "Volume", "Data Size"], width=18)
        self.category_combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.category_combo.bind("<<ComboboxSelected>>", self.update_units)

        ttk.Label(main, text="From:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.from_combo = ttk.Combobox(main, textvariable=self.from_unit_var, state="readonly", width=18)
        self.from_combo.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(main, text="To:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.to_combo = ttk.Combobox(main, textvariable=self.to_unit_var, state="readonly", width=18)
        self.to_combo.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(main, text="Value:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(main, textvariable=self.value_var, width=20).grid(row=3, column=1, sticky="w", padx=5, pady=5)

        btns = ttk.Frame(main)
        btns.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Convert", command=self.convert).grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="Swap", command=self.swap_units).grid(row=0, column=1, padx=5)

        ttk.Label(main, text="Result:").grid(row=5, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(main, textvariable=self.result_var, font=("Arial", 11, "bold")).grid(row=5, column=1, sticky="w", padx=5, pady=5)

        self.unit_maps = self.build_unit_maps()
        self.update_units()

    def build_unit_maps(self):
        return {
            "Length": {"units": {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0, "inch": 0.0254, "foot": 0.3048, "yard": 0.9144, "mile": 1609.34}},
            "Weight": {"units": {"mg": 1e-6, "g": 1e-3, "kg": 1.0, "tonne": 1000.0, "ounce": 0.0283495, "pound": 0.453592}},
            "Time": {"units": {"sec": 1.0, "min": 60.0, "hour": 3600.0, "day": 86400.0}},
            "Area": {"units": {"sq.m": 1.0, "sq.ft": 0.092903, "sq.inch": 0.00064516, "hectare": 10000.0, "acre": 4046.86}},
            "Volume": {"units": {"ml": 0.001, "liter": 1.0, "cubic m": 1000.0}},
            "Data Size": {"units": {"byte": 1.0, "KB": 1024.0, "MB": 1024.0**2, "GB": 1024.0**3, "TB": 1024.0**4}},
        }

    def update_units(self, event=None):
        cat = self.category_var.get()
        if cat == "Temperature":
            units = ["Celsius", "Fahrenheit", "Kelvin"]
        else:
            units = list(self.unit_maps[cat]["units"].keys())
        self.from_combo["values"] = units
        self.to_combo["values"] = units
        if units:
            self.from_unit_var.set(units[0])
            self.to_unit_var.set(units[1] if len(units) > 1 else units[0])

    def swap_units(self):
        a = self.from_unit_var.get()
        b = self.to_unit_var.get()
        self.from_unit_var.set(b)
        self.to_unit_var.set(a)

    def convert(self):
        try:
            value = float(self.value_var.get())
        except Exception:
            messagebox.showerror("Invalid Input", "Enter valid number.")
            return

        cat = self.category_var.get()
        frm = self.from_unit_var.get()
        to = self.to_unit_var.get()

        if frm == to:
            self.result_var.set(str(value))
            return

        if cat == "Temperature":
            result = self.convert_temperature(value, frm, to)
        else:
            units = self.unit_maps[cat]["units"]
            base = value * units[frm]
            result = base / units[to]

        self.result_var.set(str(round(result, 6)))

    def convert_temperature(self, value, frm, to):
        if frm == "Celsius":
            c = value
        elif frm == "Fahrenheit":
            c = (value - 32) * 5 / 9
        else:
            c = value - 273.15

        if to == "Celsius":
            return c
        elif to == "Fahrenheit":
            return c * 9 / 5 + 32
        return c + 273.15


def main():
    app = TypingTrainerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
