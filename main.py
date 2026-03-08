import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyperclip
import re
import json
import os
import datetime
import importlib.util
import sys

# File to store scripts data
SCRIPTS_FILE = "scripts.json"
SETTINGS_FILE = "settings.json"

class ClipboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Clipboard Processor")
        self.root.geometry("900x700")

        self.is_running = False
        self.last_clipboard_text = ""
        self.scripts = {}
        self.current_script_id = None
        self.settings = {}

        # Load scripts & settings
        self.load_scripts()
        self.load_settings()

        # UI Setup
        self._setup_ui()

        # Apply settings after UI is ready
        self.root.after(100, self.apply_settings)

        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Start clipboard monitoring loop
        self.root.after(1000, self.monitor_clipboard)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    self.settings = json.load(f)
            except:
                self.settings = {}

    def save_settings(self):
        # Capture current sash positions
        try:
            self.settings['main_sash'] = self.main_paned.sashpos(0)
            self.settings['v_sash'] = self.v_paned.sashpos(0)
            self.settings['monitor_sash'] = self.monitor_split.sashpos(0)
        except:
            pass # UI might not be ready or closed

        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def apply_settings(self):
        try:
            if 'main_sash' in self.settings:
                self.main_paned.sashpos(0, self.settings['main_sash'])
            if 'v_sash' in self.settings:
                self.v_paned.sashpos(0, self.settings['v_sash'])
            if 'monitor_sash' in self.settings:
                self.monitor_split.sashpos(0, self.settings['monitor_sash'])
        except Exception as e:
            print(f"Failed to apply settings: {e}")

    def on_close(self):
        self.save_settings()
        self.root.destroy()

    def _setup_ui(self):
        # Top Control Panel
        control_frame = ttk.LabelFrame(self.root, text="Control Panel", padding="10")
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Power Button
        self.btn_power = ttk.Button(control_frame, text="Power: OFF", command=self.toggle_power)
        self.btn_power.pack(side=tk.LEFT, padx=5)

        # Regex Input
        ttk.Label(control_frame, text="Regex Filter:").pack(side=tk.LEFT, padx=5)
        self.regex_var = tk.StringVar(value=".*")  # Default to match everything
        self.entry_regex = ttk.Entry(control_frame, textvariable=self.regex_var, width=30)
        self.entry_regex.pack(side=tk.LEFT, padx=5)

        # Main Content Area
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left Side: Script Management
        left_frame = ttk.Frame(self.main_paned, padding="5")
        self.main_paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Scripts Library").pack(anchor=tk.W)

        self.script_listbox = tk.Listbox(left_frame, height=20)
        self.script_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.script_listbox.bind('<<ListboxSelect>>', self.on_script_select)

        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="New", command=self.new_script).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="Save", command=self.save_script).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="Delete", command=self.delete_script).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="Upload", command=self.upload_script).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Right Side: Editor & Monitor Container
        right_frame = ttk.Frame(self.main_paned, padding="0")
        self.main_paned.add(right_frame, weight=4)

        # Vertical Split inside Right Frame
        self.v_paned = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        self.v_paned.pack(fill=tk.BOTH, expand=True)

        # --- Top: Script Editor (Smaller) ---
        editor_frame = ttk.Frame(self.v_paned, padding="5")
        self.v_paned.add(editor_frame, weight=1)

        ttk.Label(editor_frame, text="Python Script Editor (def transform(text): return text)").pack(anchor=tk.W)
        self.script_name_var = tk.StringVar()
        ttk.Entry(editor_frame, textvariable=self.script_name_var).pack(fill=tk.X, pady=2)

        # Editor Text with Scrollbar
        editor_container = ttk.Frame(editor_frame)
        editor_container.pack(fill=tk.BOTH, expand=True, pady=5)

        editor_scroll = ttk.Scrollbar(editor_container)
        editor_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.txt_editor = tk.Text(editor_container, height=8, font=("Consolas", 10))
        self.txt_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.txt_editor.config(yscrollcommand=editor_scroll.set)
        editor_scroll.config(command=self.txt_editor.yview)

        self.lbl_timestamp = ttk.Label(editor_frame, text="Last Updated: Never", font=("Arial", 8, "italic"))
        self.lbl_timestamp.pack(anchor=tk.E)

        # --- Bottom: Clipboard Monitor (Bigger) ---
        monitor_container = ttk.Frame(self.v_paned, padding="5")
        self.v_paned.add(monitor_container, weight=4)

        monitor_frame = ttk.LabelFrame(monitor_container, text="Clipboard Monitor (Scrollable)", padding="5")
        monitor_frame.pack(fill=tk.BOTH, expand=True)

        # Split Monitor into Left (Input) and Right (Output)
        self.monitor_split = ttk.PanedWindow(monitor_frame, orient=tk.HORIZONTAL)
        self.monitor_split.pack(fill=tk.BOTH, expand=True)

        # Input Area
        input_frame = ttk.Frame(self.monitor_split)
        self.monitor_split.add(input_frame, weight=1)
        ttk.Label(input_frame, text="Detected Input:").pack(anchor=tk.W)

        input_scroll = ttk.Scrollbar(input_frame)
        input_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_input = tk.Text(input_frame, height=10, width=30, state='disabled')
        self.txt_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.txt_input.config(yscrollcommand=input_scroll.set)
        input_scroll.config(command=self.txt_input.yview)

        # Output Area
        output_frame = ttk.Frame(self.monitor_split)
        self.monitor_split.add(output_frame, weight=1)
        ttk.Label(output_frame, text="Processed Output:").pack(anchor=tk.W)

        output_scroll = ttk.Scrollbar(output_frame)
        output_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_output = tk.Text(output_frame, height=10, width=30, state='disabled')
        self.txt_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.txt_output.config(yscrollcommand=output_scroll.set)
        output_scroll.config(command=self.txt_output.yview)

        # Populate list
        self.refresh_script_list()

    def load_scripts(self):
        if os.path.exists(SCRIPTS_FILE):
            try:
                with open(SCRIPTS_FILE, 'r') as f:
                    self.scripts = json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load scripts: {e}")
                self.scripts = {}

    def save_scripts_to_file(self):
        with open(SCRIPTS_FILE, 'w') as f:
            json.dump(self.scripts, f, indent=4)

    def refresh_script_list(self):
        self.script_listbox.delete(0, tk.END)
        for name in self.scripts:
            self.script_listbox.insert(tk.END, name)

    def on_script_select(self, event):
        selection = self.script_listbox.curselection()
        if not selection:
            return

        name = self.script_listbox.get(selection[0])
        script_data = self.scripts[name]

        self.current_script_id = name
        self.script_name_var.set(name)
        self.txt_editor.delete("1.0", tk.END)
        self.txt_editor.insert("1.0", script_data['code'])
        self.lbl_timestamp.config(text=f"Last Updated: {script_data['timestamp']}")

    def new_script(self):
        self.current_script_id = None
        self.script_name_var.set("New_Script")
        self.txt_editor.delete("1.0", tk.END)
        self.txt_editor.insert("1.0", "def transform(text):\n    # Modify text here\n    return text.upper()")
        self.lbl_timestamp.config(text="Last Updated: New")

    def save_script(self):
        name = self.script_name_var.get().strip()
        code = self.txt_editor.get("1.0", tk.END).strip()

        if not name:
            messagebox.showwarning("Warning", "Script name cannot be empty")
            return

        timestamp = datetime.datetime.now().astimezone().isoformat()

        # If renaming
        if self.current_script_id and self.current_script_id != name:
            if name in self.scripts:
                if not messagebox.askyesno("Confirm", f"Script '{name}' already exists. Overwrite?"):
                    return
            del self.scripts[self.current_script_id]

        self.scripts[name] = {
            "code": code,
            "timestamp": timestamp
        }

        self.current_script_id = name
        self.save_scripts_to_file()
        self.refresh_script_list()
        self.lbl_timestamp.config(text=f"Last Updated: {timestamp}")
        messagebox.showinfo("Success", "Script saved successfully!")

    def delete_script(self):
        if not self.current_script_id:
            return

        if messagebox.askyesno("Confirm", f"Delete script '{self.current_script_id}'?"):
            del self.scripts[self.current_script_id]
            self.save_scripts_to_file()
            self.refresh_script_list()
            self.new_script()

    def upload_script(self):
        filepath = filedialog.askopenfilename(filetypes=[("Python Files", "*.py"), ("Text Files", "*.txt")])
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    code = f.read()

                filename = os.path.splitext(os.path.basename(filepath))[0]
                self.script_name_var.set(filename)
                self.txt_editor.delete("1.0", tk.END)
                self.txt_editor.insert("1.0", code)
                self.current_script_id = None # Treat as new until saved
                self.lbl_timestamp.config(text="Last Updated: Uploaded (Unsaved)")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to upload: {e}")

    def toggle_power(self):
        self.is_running = not self.is_running
        if self.is_running:
            self.btn_power.config(text="Power: ON", style="Accent.TButton") # Simple visual change
            # Initialize last clipboard to current so we don't trigger immediately on old content
            try:
                self.last_clipboard_text = pyperclip.paste()
            except:
                self.last_clipboard_text = ""
        else:
            self.btn_power.config(text="Power: OFF", style="TButton")

    def monitor_clipboard(self):
        if self.is_running:
            try:
                current_text = pyperclip.paste()
                if current_text != self.last_clipboard_text:
                    self.last_clipboard_text = current_text
                    self.handle_clipboard_change(current_text)
            except Exception as e:
                print(f"Clipboard error: {e}")

        # Check every 1 second
        self.root.after(1000, self.monitor_clipboard)

    def handle_clipboard_change(self, text):
        regex_pattern = self.regex_var.get()
        try:
            if re.match(regex_pattern, text, re.DOTALL):
                self.update_log_ui(self.txt_input, text)
                self.process_text(text)
            else:
                print("Text did not match regex.")
        except re.error:
            print("Invalid Regex")

    def process_text(self, text):
        script_name = self.script_listbox.get(tk.ACTIVE)
        if not script_name or script_name not in self.scripts:
            # If no script selected in list, try current editor content if saved, or just warn
            # For this logic, let's require selecting a script or using the one currently in memory map
            if self.current_script_id in self.scripts:
                script_name = self.current_script_id
            else:
                self.update_log_ui(self.txt_output, "Error: No script selected")
                return

        script_code = self.scripts[script_name]['code']

        # Execute script securely-ish
        local_scope = {}
        try:
            exec(script_code, {}, local_scope)
            if 'transform' in local_scope:
                result = local_scope['transform'](text)
                if isinstance(result, str):
                    pyperclip.copy(result)
                    # Update last clipboard to result so we don't re-trigger loop immediately
                    self.last_clipboard_text = result
                    self.update_log_ui(self.txt_output, result)
                else:
                    self.update_log_ui(self.txt_output, "Error: transform() must return string")
            else:
                self.update_log_ui(self.txt_output, "Error: Script must define 'transform(text)' function")
        except Exception as e:
            self.update_log_ui(self.txt_output, f"Script Error: {e}")

    def update_log_ui(self, widget, text):
        widget.config(state='normal')
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.config(state='disabled')

if __name__ == "__main__":
    root = tk.Tk()
    # Optional: basic styling
    style = ttk.Style()
    style.theme_use('clam')
    app = ClipboardApp(root)
    root.mainloop()
