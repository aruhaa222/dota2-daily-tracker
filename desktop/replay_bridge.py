"""DotaPulse Replay Bridge 5.0: local, standard-library Windows replay catalog.
Does not decode Valve DEM internals or upload replay files.
"""
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP = "DotaPulse Replay Bridge 5.0"
DEFAULT_DIR = Path.home() / "Documents" / "DotaPulse"
REPLAY_PATTERN = re.compile(r"(?<!\d)(\d{9,12})(?!\d)")

def collect(folder):
    results = []
    for path in Path(folder).rglob("*.dem"):
        try:
            st = path.stat()
            found = REPLAY_PATTERN.search(path.stem)
            results.append({
                "file": str(path),
                "name": path.name,
                "match_id": found.group(1) if found else None,
                "size_mb": round(st.st_size / 1048576, 2),
                "modified_utc": dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).isoformat(),
            })
        except (OSError, PermissionError):
            continue
    return sorted(results, key=lambda x: x["modified_utc"], reverse=True)

class Window:
    def __init__(self, root):
        self.root = root
        root.title(APP)
        root.geometry("960x560")
        self.folder = tk.StringVar(value=str(DEFAULT_DIR))
        self.status = tk.StringVar(value="Выберите папку с реплеями .dem")
        self.rows = []
        top = ttk.Frame(root, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="Папка с реплеями:").pack(anchor="w")
        line = ttk.Frame(top)
        line.pack(fill="x", pady=6)
        ttk.Entry(line, textvariable=self.folder).pack(side="left", fill="x", expand=True)
        ttk.Button(line, text="Выбрать", command=self.choose).pack(side="left", padx=5)
        ttk.Button(line, text="Сканировать", command=self.scan).pack(side="left")
        cols = ("name", "match_id", "size_mb", "modified_utc")
        self.table = ttk.Treeview(root, columns=cols, show="headings")
        for col, label, width in [("name","Файл",350),("match_id","ID матча",130),("size_mb","МБ",80),("modified_utc","Изменён UTC",240)]:
            self.table.heading(col, text=label)
            self.table.column(col, width=width)
        self.table.pack(fill="both", expand=True, padx=12, pady=6)
        bottom = ttk.Frame(root, padding=12)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Открыть матч в OpenDota", command=self.open_match).pack(side="left")
        ttk.Button(bottom, text="Экспорт JSON", command=self.export).pack(side="left", padx=8)
        ttk.Label(bottom, textvariable=self.status).pack(side="right")
        ttk.Label(root, text="Локальный каталог: содержимое .dem не разбирается, файлы не отправляются в сеть.", padding=(12,0,12,12)).pack(anchor="w")
    def choose(self):
        folder = filedialog.askdirectory(initialdir=str(Path.home()))
        if folder: self.folder.set(folder)
    def scan(self):
        folder = Path(self.folder.get())
        if not folder.is_dir():
            messagebox.showerror(APP, "Папка не найдена.")
            return
        self.rows = collect(folder)
        for item in self.table.get_children(): self.table.delete(item)
        for i, row in enumerate(self.rows):
            self.table.insert("", "end", iid=str(i), values=tuple(row[k] or "—" for k in ("name","match_id","size_mb","modified_utc")))
        self.status.set(f"Найдено {len(self.rows)} реплеев")
    def open_match(self):
        sel = self.table.selection()
        if not sel: return
        match_id = self.rows[int(sel[0])]["match_id"]
        if not match_id:
            messagebox.showinfo(APP, "ID матча не найден в имени файла.")
            return
        import webbrowser
        webbrowser.open("https://www.opendota.com/matches/" + match_id)
    def export(self):
        if not self.rows:
            messagebox.showinfo(APP, "Сначала просканируйте папку.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="dotapulse-replays.json")
        if not path: return
        Path(path).write_text(json.dumps({"format":"dotapulse-replay-index-v1","generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"replays":self.rows}, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status.set("Каталог сохранён локально")

if __name__ == "__main__":
    root = tk.Tk()
    Window(root)
    root.mainloop()
