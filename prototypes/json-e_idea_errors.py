#!/usr/bin/env python3
import json
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, ttk
from pathlib import Path


class JsonE:
    def __init__(self, root):
        self.root = root
        self.root.title("json-e")
        self.root.geometry("1100x700")

        self.data = {}
        self.file_path = None
        self.node_paths = {}

        self.build_ui()

    def build_ui(self):
        topbar = tk.Frame(self.root)
        topbar.pack(fill="x")

        tk.Button(topbar, text="Open JSON", command=self.open_json).pack(side="left")
        tk.Button(topbar, text="Save", command=self.save_json).pack(side="left")
        tk.Button(topbar, text="Save As", command=self.save_as_json).pack(side="left")

        self.tree = ttk.Treeview(self.root, columns=("type", "value"), show="tree headings")
        self.tree.heading("#0", text="Field")
        self.tree.heading("type", text="Type")
        self.tree.heading("value", text="Value")
        self.tree.column("#0", width=350)
        self.tree.column("type", width=120)
        self.tree.column("value", width=550)
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>", self.edit_selected)

        bottombar = tk.Frame(self.root)
        bottombar.pack(fill="x")

        tk.Button(bottombar, text="+ Add Field / Item", command=self.add_node).pack(side="left")
        tk.Button(bottombar, text="- Delete Selected", command=self.delete_node).pack(side="left")
        tk.Button(bottombar, text="Edit Value", command=self.edit_selected).pack(side="left")

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
            self.refresh_tree()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_json(self):
        if not self.file_path:
            self.save_as_json()
            return

        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
                f.write("\n")

            messagebox.showinfo("Saved", f"Saved {self.file_path}")

        except Exception as e:
            messagebox.showerror("Error", str(e))

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

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.node_paths.clear()
        self.insert_node("", "root", self.data, [])

    def json_type(self, value):
        if isinstance(value, dict):
            return "object"
        if isinstance(value, list):
            return "array"
        if isinstance(value, str):
            return "string"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "float"
        if value is None:
            return "null"
        return "unknown"

    def preview_value(self, value):
        if isinstance(value, (dict, list)):
            return ""
        return str(value)

    def insert_node(self, parent_id, label, value, path):
        node_id = self.tree.insert(
            parent_id,
            "end",
            text=str(label),
            values=(self.json_type(value), self.preview_value(value)),
            open=True
        )

        self.node_paths[node_id] = path

        if isinstance(value, dict):
            for key, child in value.items():
                self.insert_node(node_id, key, child, path + [key])

        elif isinstance(value, list):
            for index, child in enumerate(value):
                self.insert_node(node_id, f"[{index}]", child, path + [index])

    def get_by_path(self, path):
        current = self.data
        for part in path:
            current = current[part]
        return current

    def get_parent_and_key(self, path):
        if not path:
            return None, None

        parent = self.get_by_path(path[:-1])
        key = path[-1]
        return parent, key

    def parse_input_value(self, raw):
        raw = raw.strip()

        if raw == "":
            return ""

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def edit_selected(self, event=None):
        selected = self.tree.selection()

        if not selected:
            return

        node_id = selected[0]
        path = self.node_paths[node_id]
        value = self.get_by_path(path)

        if isinstance(value, (dict, list)):
            messagebox.showinfo("Not a value", "This is a container. Add fields/items inside it.")
            return

        new_raw = simpledialog.askstring(
            "Edit Value",
            f"New value for {self.tree.item(node_id, 'text')}:",
            initialvalue=json.dumps(value) if not isinstance(value, str) else value
        )

        if new_raw is None:
            return

        new_value = self.parse_input_value(new_raw)

        parent, key = self.get_parent_and_key(path)

        if parent is None:
            self.data = new_value
        else:
            parent[key] = new_value

        self.refresh_tree()

    def choose_new_value(self):
        value_type = simpledialog.askstring(
            "Value Type",
            "Type: string, number, boolean, null, object, array",
            initialvalue="string"
        )

        if value_type is None:
            return None

        value_type = value_type.strip().lower()

        if value_type == "object":
            return {}

        if value_type == "array":
            return []

        if value_type == "null":
            return None

        if value_type == "boolean":
            raw = simpledialog.askstring("Boolean", "true or false:", initialvalue="true")
            return raw.strip().lower() == "true"

        if value_type == "number":
            raw = simpledialog.askstring("Number", "Enter number:", initialvalue="0")
            try:
                if "." in raw:
                    return float(raw)
                return int(raw)
            except Exception:
                return 0

        raw = simpledialog.askstring("String", "Enter text:", initialvalue="")
        return "" if raw is None else raw

    def add_node(self):
        selected = self.tree.selection()

        if not selected:
            target = self.data
            path = []
        else:
            node_id = selected[0]
            path = self.node_paths[node_id]
            target = self.get_by_path(path)

        if isinstance(target, dict):
            key = simpledialog.askstring("Add Field", "New field name:")

            if not key:
                return

            if key in target:
                messagebox.showerror("Error", "Field already exists.")
                return

            value = self.choose_new_value()
            target[key] = value

        elif isinstance(target, list):
            value = self.choose_new_value()
            target.append(value)

        else:
            messagebox.showinfo("Not a container", "Select an object or array to add inside it.")
            return

        self.refresh_tree()

    def delete_node(self):
        selected = self.tree.selection()

        if not selected:
            return

        node_id = selected[0]
        path = self.node_paths[node_id]

        if not path:
            messagebox.showerror("Error", "Cannot delete root.")
            return

        parent, key = self.get_parent_and_key(path)

        if isinstance(parent, list):
            del parent[key]
        else:
            del parent[key]

        self.refresh_tree()


def main():
    root = tk.Tk()
    app = JsonE(root)
    root.mainloop()


if __name__ == "__main__":
    main()