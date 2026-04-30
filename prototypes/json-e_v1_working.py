#!/usr/bin/env python3
"""
json-e: a simple GUI editor for any JSON file.

Core idea:
- JSON objects/lists are shown as nested expandable-looking rows.
- Leaf values are editable in text boxes.
- + beside any row duplicates that exact node/branch.
- - beside any row deletes that exact node/branch.
- Add Child beside objects/arrays creates a fresh nested value inside that container.
- Save writes valid formatted JSON.

No schema knowledge required.
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
        self.root.geometry("1250x760")

        self.data = {}
        self.file_path: Path | None = None
        self.collapsed = set()

        self._build_ui()
        self._new_empty()

    # -------------------------
    # UI
    # -------------------------

    def _build_ui(self):
        self.topbar = tk.Frame(self.root)
        self.topbar.pack(fill="x", padx=8, pady=6)

        tk.Button(self.topbar, text="New", command=self.new_file).pack(side="left", padx=2)
        tk.Button(self.topbar, text="Open JSON", command=self.open_json).pack(side="left", padx=2)
        tk.Button(self.topbar, text="Save", command=self.save_json).pack(side="left", padx=2)
        tk.Button(self.topbar, text="Save As", command=self.save_as_json).pack(side="left", padx=2)
        tk.Button(self.topbar, text="Expand All", command=self.expand_all).pack(side="left", padx=10)
        tk.Button(self.topbar, text="Collapse All", command=self.collapse_all).pack(side="left", padx=2)

        self.title_label = tk.Label(self.topbar, text="untitled", anchor="w")
        self.title_label.pack(side="left", padx=16)

        self.canvas = tk.Canvas(self.root, borderwidth=0)
        self.scroll_y = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
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
    # JSON path helpers
    # -------------------------

    def path_key(self, path):
        return tuple(path)

    def get_by_path(self, path):
        cur = self.data
        for part in path:
            cur = cur[part]
        return cur

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

    def delete_at_path(self, path):
        if not path:
            messagebox.showerror("Cannot delete", "Cannot delete root.")
            return

        parent, key = self.get_parent_key(path)
        del parent[key]
        self.render()

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
        """
        + beside any row duplicates the selected branch/value.
        - If parent is a list, insert clone immediately after selected index.
        - If parent is an object, create key_copy, key_copy_2, etc.
        - If root, duplicate root into {"root_copy": ...} only if user confirms.
        """
        if not path:
            if not messagebox.askyesno("Duplicate root", "Duplicate root into a new wrapper object?"):
                return
            self.data = {
                "root": self.data,
                "root_copy": deepcopy(self.data)
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

    # -------------------------
    # Value parsing / creation
    # -------------------------

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
        """
        User-friendly:
        - true/false/null/numbers/arrays/objects parse as JSON
        - everything else becomes a string
        """
        raw = raw.strip()

        if raw == "":
            return ""

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

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

    # -------------------------
    # Add / edit
    # -------------------------

    def add_child_at_path(self, path):
        """
        Add Child means:
        - object: ask for field name, then value type/value
        - array: append a new item
        """
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
        raw = entry.get()
        self.set_by_path(path, self.parse_value(raw))
        self.render()

    def rename_key(self, path):
        """
        Rename object fields.
        Array indexes cannot be renamed.
        """
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

        items = list(parent.items())
        parent.clear()

        for old_key, value in items:
            if old_key == key:
                parent[new_key] = value
            else:
                parent[old_key] = value

        self.render()

    # -------------------------
    # Collapse / expand
    # -------------------------

    def toggle_collapse(self, path):
        pk = self.path_key(path)
        if pk in self.collapsed:
            self.collapsed.remove(pk)
        else:
            self.collapsed.add(pk)
        self.render()

    def expand_all(self):
        self.collapsed.clear()
        self.render()

    def collect_container_paths(self, value=None, path=None, out=None):
        if value is None:
            value = self.data
        if path is None:
            path = []
        if out is None:
            out = []

        if isinstance(value, dict):
            out.append(tuple(path))
            for k, v in value.items():
                self.collect_container_paths(v, path + [k], out)
        elif isinstance(value, list):
            out.append(tuple(path))
            for i, v in enumerate(value):
                self.collect_container_paths(v, path + [i], out)

        return out

    def collapse_all(self):
        self.collapsed = set(self.collect_container_paths())
        self.collapsed.discard(tuple([]))
        self.render()

    # -------------------------
    # Rendering
    # -------------------------

    def render(self):
        for child in self.body.winfo_children():
            child.destroy()

        self._update_title()

        header = tk.Frame(self.body)
        header.pack(fill="x", padx=8, pady=(4, 8))

        tk.Label(header, text="Field", width=34, anchor="w", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        tk.Label(header, text="Type", width=10, anchor="w", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        tk.Label(header, text="Value", width=70, anchor="w", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        tk.Label(header, text="Actions", width=28, anchor="w", font=("TkDefaultFont", 10, "bold")).pack(side="left")

        self.render_node(self.body, "root", self.data, [], 0)

    def _update_title(self):
        if self.file_path:
            self.title_label.config(text=str(self.file_path))
        else:
            self.title_label.config(text="untitled")

    def render_node(self, parent_frame, label, value, path, depth):
        row = tk.Frame(parent_frame)
        row.pack(fill="x", anchor="w", padx=(8 + depth * 24, 8), pady=2)

        is_container = isinstance(value, (dict, list))
        is_collapsed = self.path_key(path) in self.collapsed

        if is_container:
            symbol = "▶" if is_collapsed else "▼"
            tk.Button(
                row,
                text=symbol,
                width=2,
                command=lambda p=path: self.toggle_collapse(p)
            ).pack(side="left")
        else:
            tk.Label(row, text="", width=2).pack(side="left")

        tk.Label(row, text=str(label), width=32, anchor="w").pack(side="left")
        tk.Label(row, text=self.json_type(value), width=10, anchor="w").pack(side="left")

        if is_container:
            if isinstance(value, dict):
                summary = f"{len(value)} field(s)"
            else:
                summary = f"{len(value)} item(s)"

            tk.Label(row, text=summary, width=70, anchor="w").pack(side="left")

            tk.Button(
                row,
                text="+ duplicate",
                command=lambda p=path: self.duplicate_at_path(p)
            ).pack(side="left", padx=1)

            tk.Button(
                row,
                text="Add Child",
                command=lambda p=path: self.add_child_at_path(p)
            ).pack(side="left", padx=1)

            tk.Button(
                row,
                text="Rename",
                command=lambda p=path: self.rename_key(p)
            ).pack(side="left", padx=1)

            tk.Button(
                row,
                text="- delete",
                command=lambda p=path: self.delete_at_path(p)
            ).pack(side="left", padx=1)

            if not is_collapsed:
                if isinstance(value, dict):
                    for key, child in value.items():
                        self.render_node(parent_frame, key, child, path + [key], depth + 1)
                else:
                    for index, child in enumerate(value):
                        self.render_node(parent_frame, f"[{index}]", child, path + [index], depth + 1)

        else:
            entry = tk.Entry(row, width=70)
            entry.insert(0, self.display_value(value))
            entry.pack(side="left")

            tk.Button(
                row,
                text="✓ apply",
                command=lambda p=path, e=entry: self.apply_entry_value(p, e)
            ).pack(side="left", padx=1)

            tk.Button(
                row,
                text="+ duplicate",
                command=lambda p=path: self.duplicate_at_path(p)
            ).pack(side="left", padx=1)

            tk.Button(
                row,
                text="Rename",
                command=lambda p=path: self.rename_key(p)
            ).pack(side="left", padx=1)

            tk.Button(
                row,
                text="- delete",
                command=lambda p=path: self.delete_at_path(p)
            ).pack(side="left", padx=1)


def main():
    root = tk.Tk()
    JsonE(root)
    root.mainloop()


if __name__ == "__main__":
    main()
