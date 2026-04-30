#!/usr/bin/env python3
"""
json-e: a simple GUI editor for any JSON file.

What it does:
- Opens any valid JSON.
- Displays JSON as nested rows.
- Keeps columns aligned: Field | Type | Value | Actions.
- Lets you edit leaf values.
- + duplicates the selected value/branch.
- Add Child adds inside an object or array.
- - deletes the selected value/branch.
- Rename changes object keys.
- Collapse All / Expand All work reliably.

Run:
    python3 json-e.py
"""

import json
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from pathlib import Path
from copy import deepcopy


APP_TITLE = "json-e"


class JsonE:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1280x780")

        self.data = {}
        self.file_path: Path | None = None
        self.collapsed = set()

        self._build_ui()
        self._new_empty()

    # -------------------------
    # UI shell
    # -------------------------

    def _build_ui(self):
        self.topbar = tk.Frame(self.root)
        self.topbar.pack(fill="x", padx=8, pady=6)

        tk.Button(self.topbar, text="New", command=self.new_file).pack(side="left", padx=2)
        tk.Button(self.topbar, text="Open JSON", command=self.open_json).pack(side="left", padx=2)
        tk.Button(self.topbar, text="Save", command=self.save_json).pack(side="left", padx=2)
        tk.Button(self.topbar, text="Save As", command=self.save_as_json).pack(side="left", padx=2)

        tk.Button(self.topbar, text="Expand All", command=self.expand_all).pack(side="left", padx=(16, 2))
        tk.Button(self.topbar, text="Collapse All", command=self.collapse_all).pack(side="left", padx=2)

        self.title_label = tk.Label(self.topbar, text="untitled", anchor="w")
        self.title_label.pack(side="left", padx=18)

        shell = tk.Frame(self.root)
        shell.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(shell, borderwidth=0)
        self.scroll_y = tk.Scrollbar(shell, orient="vertical", command=self.canvas.yview)
        self.scroll_x = tk.Scrollbar(self.root, orient="horizontal", command=self.canvas.xview)

        self.body = tk.Frame(self.canvas)

        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scroll_y.set, xscrollcommand=self.scroll_x.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll_y.pack(side="right", fill="y")
        self.scroll_x.pack(side="bottom", fill="x")

        self.canvas.bind("<MouseWheel>", self._mousewheel)
        self.canvas.bind("<Button-4>", self._mousewheel_linux)
        self.canvas.bind("<Button-5>", self._mousewheel_linux)

    def _on_body_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-3, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(3, "units")

    # -------------------------
    # File handling
    # -------------------------

    def _new_empty(self):
        self.data = {
            "schema": {
                "name": "json-e.document",
                "version": "0.1.0"
            }
        }
        self.file_path = None
        self.collapsed.clear()
        self.render()

    def new_file(self):
        if messagebox.askyesno("New JSON", "Create a new JSON document? Unsaved changes will be lost."):
            self._new_empty()

    def open_json(self):
        path = filedialog.askopenfilename(
            title="Open JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                self.data = json.load(f)

            self.file_path = Path(path)
            self.collapsed.clear()
            self.render()

        except Exception as e:
            messagebox.showerror("Open error", str(e))

    def save_json(self):
        if self.file_path is None:
            self.save_as_json()
            return

        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
                f.write("\n")

            messagebox.showinfo("Saved", f"Saved:\n{self.file_path}")
            self._update_title()

        except Exception as e:
            messagebox.showerror("Save error", str(e))

    def save_as_json(self):
        path = filedialog.asksaveasfilename(
            title="Save JSON As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return

        self.file_path = Path(path)
        self.save_json()

    # -------------------------
    # JSON helpers
    # -------------------------

    def path_key(self, path):
        return tuple(path)

    def get_by_path(self, path):
        current = self.data
        for part in path:
            current = current[part]
        return current

    def get_parent_key(self, path):
        if not path:
            return None, None
        return self.get_by_path(path[:-1]), path[-1]

    def set_by_path(self, path, value):
        if not path:
            self.data = value
            return

        parent, key = self.get_parent_key(path)
        parent[key] = value

    def json_type(self, value):
        if isinstance(value, dict):
            return "object"
        if isinstance(value, list):
            return "array"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int) and not isinstance(value, bool):
            return "integer"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "string"
        if value is None:
            return "null"
        return "unknown"

    def display_value(self, value):
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (dict, list)):
            return ""
        return str(value)

    def parse_value(self, raw):
        raw = raw.strip()
        if raw == "":
            return ""

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    # -------------------------
    # Mutations
    # -------------------------

    def make_copy_key(self, parent: dict, key):
        key = str(key)
        base = f"{key}_copy"
        candidate = base
        n = 2

        while candidate in parent:
            candidate = f"{base}_{n}"
            n += 1

        return candidate

    def duplicate_at_path(self, path):
        if not path:
            if not messagebox.askyesno("Duplicate root", "Duplicate root into a wrapper object?"):
                return

            old = deepcopy(self.data)
            self.data = {
                "root": old,
                "root_copy": deepcopy(old)
            }
            self.render()
            return

        parent, key = self.get_parent_key(path)
        clone = deepcopy(parent[key])

        if isinstance(parent, list):
            parent.insert(key + 1, clone)
        elif isinstance(parent, dict):
            parent[self.make_copy_key(parent, key)] = clone
        else:
            messagebox.showerror("Cannot duplicate", "Parent is not editable.")
            return

        self.render()

    def delete_at_path(self, path):
        if not path:
            messagebox.showerror("Cannot delete", "Cannot delete root.")
            return

        parent, key = self.get_parent_key(path)

        if isinstance(parent, list):
            del parent[key]
        elif isinstance(parent, dict):
            del parent[key]
        else:
            messagebox.showerror("Cannot delete", "Parent is not editable.")
            return

        self.render()

    def choose_new_value(self):
        kind = simpledialog.askstring(
            "New child type",
            "Choose type: string, number, boolean, null, object, array",
            initialvalue="string"
        )

        if kind is None:
            return None, False

        kind = kind.strip().lower()

        if kind == "object":
            return {}, True

        if kind == "array":
            return [], True

        if kind == "null":
            return None, True

        if kind == "boolean":
            raw = simpledialog.askstring("Boolean", "Value: true or false", initialvalue="true")
            if raw is None:
                return None, False
            return raw.strip().lower() == "true", True

        if kind == "number":
            raw = simpledialog.askstring("Number", "Value:", initialvalue="0")
            if raw is None:
                return None, False
            try:
                return float(raw) if "." in raw else int(raw), True
            except ValueError:
                messagebox.showerror("Invalid number", "That was not a valid number.")
                return None, False

        raw = simpledialog.askstring("String", "Value:", initialvalue="")
        if raw is None:
            return None, False

        return raw, True

    def add_child_at_path(self, path):
        target = self.get_by_path(path)

        if isinstance(target, dict):
            key = simpledialog.askstring("Add field", "Field name:")
            if not key:
                return

            if key in target:
                messagebox.showerror("Duplicate field", "That field already exists.")
                return

            value, ok = self.choose_new_value()
            if not ok:
                return

            target[key] = value

        elif isinstance(target, list):
            value, ok = self.choose_new_value()
            if not ok:
                return

            target.append(value)

        else:
            messagebox.showinfo("Cannot add child", "Add Child works only on objects and arrays.")
            return

        self.render()

    def apply_entry_value(self, path, entry):
        self.set_by_path(path, self.parse_value(entry.get()))
        self.render()

    def rename_key(self, path):
        if not path:
            messagebox.showinfo("Cannot rename", "Cannot rename root.")
            return

        parent, key = self.get_parent_key(path)

        if not isinstance(parent, dict):
            messagebox.showinfo("Cannot rename", "Array items do not have names.")
            return

        new_key = simpledialog.askstring("Rename field", "New field name:", initialvalue=str(key))
        if not new_key or new_key == key:
            return

        if new_key in parent:
            messagebox.showerror("Duplicate field", "That field already exists.")
            return

        new_parent = {}
        for old_key, value in parent.items():
            if old_key == key:
                new_parent[new_key] = value
            else:
                new_parent[old_key] = value

        parent.clear()
        parent.update(new_parent)
        self.render()

    # -------------------------
    # Collapse / expand
    # -------------------------

    def collect_container_paths(self, value, path=None, out=None):
        if path is None:
            path = []
        if out is None:
            out = []

        if isinstance(value, dict):
            out.append(tuple(path))
            for key, child in value.items():
                self.collect_container_paths(child, path + [key], out)

        elif isinstance(value, list):
            out.append(tuple(path))
            for index, child in enumerate(value):
                self.collect_container_paths(child, path + [index], out)

        return out

    def collapse_all(self):
        self.collapsed = set(self.collect_container_paths(self.data))
        self.collapsed.discard(tuple())  # keep root visible
        self.render()

    def expand_all(self):
        self.collapsed.clear()
        self.render()

    def toggle_collapse(self, path):
        key = self.path_key(path)

        if key in self.collapsed:
            self.collapsed.remove(key)
        else:
            self.collapsed.add(key)

        self.render()

    # -------------------------
    # Rendering
    # -------------------------

    def render(self):
        for child in self.body.winfo_children():
            child.destroy()

        self._update_title()
        self.render_header()
        self.render_node("root", self.data, [], 0)

    def _update_title(self):
        if self.file_path:
            self.title_label.config(text=str(self.file_path))
        else:
            self.title_label.config(text="untitled")

    def render_header(self):
        row = tk.Frame(self.body)
        row.pack(fill="x", padx=8, pady=(4, 8))

        tk.Label(row, text="", width=3).grid(row=0, column=0, sticky="w")
        tk.Label(row, text="Field", width=42, anchor="w", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=1, sticky="w")
        tk.Label(row, text="Type", width=12, anchor="w", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=2, sticky="w")
        tk.Label(row, text="Value", width=72, anchor="w", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=3, sticky="w")
        tk.Label(row, text="Actions", width=36, anchor="w", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=4, sticky="w")

    def render_node(self, label, value, path, depth):
        row = tk.Frame(self.body)
        row.pack(fill="x", padx=8, pady=2)

        is_container = isinstance(value, (dict, list))
        is_collapsed = self.path_key(path) in self.collapsed

        indent_px = depth * 24

        field_cell = tk.Frame(row, width=360, height=26)
        field_cell.grid(row=0, column=1, sticky="w")
        field_cell.grid_propagate(False)

        if is_container:
            symbol = "▶" if is_collapsed else "▼"
            tk.Button(
                row,
                text=symbol,
                width=2,
                command=lambda p=path: self.toggle_collapse(p)
            ).grid(row=0, column=0, sticky="w")
        else:
            tk.Label(row, text="", width=3).grid(row=0, column=0, sticky="w")

        indent = tk.Frame(field_cell, width=indent_px)
        indent.pack(side="left")

        tk.Label(field_cell, text=str(label), anchor="w").pack(side="left", fill="x")

        tk.Label(row, text=self.json_type(value), width=12, anchor="w").grid(row=0, column=2, sticky="w")

        value_cell = tk.Frame(row, width=620, height=26)
        value_cell.grid(row=0, column=3, sticky="w")
        value_cell.grid_propagate(False)

        actions = tk.Frame(row, width=300, height=26)
        actions.grid(row=0, column=4, sticky="w")
        actions.grid_propagate(False)

        if is_container:
            summary = f"{len(value)} field(s)" if isinstance(value, dict) else f"{len(value)} item(s)"
            tk.Label(value_cell, text=summary, anchor="w").pack(side="left", fill="x")

            tk.Button(
                actions,
                text="+ duplicate",
                width=11,
                command=lambda p=path: self.duplicate_at_path(p)
            ).pack(side="left", padx=1)

            tk.Button(
                actions,
                text="Add Child",
                width=9,
                command=lambda p=path: self.add_child_at_path(p)
            ).pack(side="left", padx=1)

            tk.Button(
                actions,
                text="Rename",
                width=7,
                command=lambda p=path: self.rename_key(p)
            ).pack(side="left", padx=1)

            tk.Button(
                actions,
                text="-",
                width=3,
                command=lambda p=path: self.delete_at_path(p)
            ).pack(side="left", padx=1)

            if not is_collapsed:
                if isinstance(value, dict):
                    for key, child in value.items():
                        self.render_node(key, child, path + [key], depth + 1)
                else:
                    for index, child in enumerate(value):
                        self.render_node(f"[{index}]", child, path + [index], depth + 1)

        else:
            entry = tk.Entry(value_cell, width=84)
            entry.insert(0, self.display_value(value))
            entry.pack(side="left", fill="x")

            tk.Button(
                actions,
                text="✓",
                width=3,
                command=lambda p=path, e=entry: self.apply_entry_value(p, e)
            ).pack(side="left", padx=1)

            tk.Button(
                actions,
                text="+ duplicate",
                width=11,
                command=lambda p=path: self.duplicate_at_path(p)
            ).pack(side="left", padx=1)

            tk.Button(
                actions,
                text="Rename",
                width=7,
                command=lambda p=path: self.rename_key(p)
            ).pack(side="left", padx=1)

            tk.Button(
                actions,
                text="-",
                width=3,
                command=lambda p=path: self.delete_at_path(p)
            ).pack(side="left", padx=1)


def main():
    root = tk.Tk()
    JsonE(root)
    root.mainloop()


if __name__ == "__main__":
    main()
