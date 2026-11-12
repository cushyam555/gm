from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from .core import convert_file


class Application:
    def __init__(self, root):
        self.root = root
        self.paths = []
        self.messages = queue.Queue()
        self.busy = False
        root.title("GM1 MIDI Reset")
        root.geometry("880x600")
        root.minsize(720, 480)
        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="GM1 MIDI Reset", font=("Tahoma", 22, "bold")).pack(anchor="w")
        ttk.Label(frame, text="รีเซ็ตเสียง • แพนกลาง • น้ำหนักโน้ตเท่ากัน • บันทึกเป็นไฟล์ใหม่").pack(anchor="w", pady=(4, 16))
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x")
        self.buttons = []
        for label, command in [("เพิ่มไฟล์ MIDI", self.add_files), ("เพิ่มโฟลเดอร์", self.add_folder), ("ล้างรายการ", self.clear)]:
            button = ttk.Button(toolbar, text=label, command=command)
            button.pack(side="left", padx=(0, 8))
            self.buttons.append(button)
        self.table = ttk.Treeview(frame, columns=("file", "status"), show="headings")
        self.table.heading("file", text="ไฟล์ต้นฉบับ")
        self.table.heading("status", text="ผลการทำงาน")
        self.table.column("file", width=520)
        self.table.column("status", width=240)
        self.table.pack(fill="both", expand=True, pady=12)
        scroll = ttk.Scrollbar(self.table, orient="vertical", command=self.table.yview)
        scroll.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scroll.set)
        options = ttk.Frame(frame)
        options.pack(fill="x")
        ttk.Label(options, text="น้ำหนักโน้ต (1–127)").pack(side="left")
        self.velocity = tk.StringVar(value="100")
        self.spin = ttk.Spinbox(options, from_=1, to=127, width=6, textvariable=self.velocity)
        self.spin.pack(side="left", padx=8)
        self.folder = tk.StringVar()
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=12)
        ttk.Label(row, text="ปลายทาง").pack(side="left")
        self.entry = ttk.Entry(row, textvariable=self.folder)
        self.entry.pack(side="left", fill="x", expand=True, padx=8)
        choose = ttk.Button(row, text="เลือกโฟลเดอร์", command=self.choose_folder)
        choose.pack(side="left")
        self.buttons.append(choose)
        ttk.Label(frame, text="ล้าง SysEx และ Controller เดิม รวมถึง Sustain; เสียง GS/XG อาจเปลี่ยนไป", wraplength=800).pack(anchor="w")
        self.progress = ttk.Progressbar(frame)
        self.progress.pack(fill="x", pady=10)
        self.status = tk.StringVar(value="เพิ่มไฟล์เพื่อเริ่มต้น — รองรับ .mid และ .midi")
        ttk.Label(frame, textvariable=self.status).pack(anchor="w")
        self.run_button = ttk.Button(frame, text="รีเซ็ตและบันทึกไฟล์ใหม่", command=self.start)
        self.run_button.pack(anchor="e", pady=(8, 0))
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(100, self.poll)

    def add(self, paths):
        for path in paths:
            path = Path(path).resolve()
            if path.suffix.lower() in {".mid", ".midi"} and path not in self.paths:
                self.table.insert("", "end", iid=str(len(self.paths)), values=(str(path), "รอทำงาน"))
                self.paths.append(path)
        self.status.set(f"ทั้งหมด {len(self.paths)} ไฟล์")

    def add_files(self):
        self.add(filedialog.askopenfilenames(filetypes=[("MIDI", "*.mid *.midi *.MID *.MIDI")]))

    def add_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.add(sorted(p for p in Path(folder).iterdir() if p.is_file()))

    def clear(self):
        self.table.delete(*self.table.get_children())
        self.paths.clear()
        self.status.set("ล้างรายการแล้ว")

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder.set(folder)

    def start(self):
        try:
            velocity = int(self.velocity.get())
            if not 1 <= velocity <= 127:
                raise ValueError()
        except ValueError:
            messagebox.showerror("ตรวจสอบค่า", "น้ำหนักโน้ตต้องเป็นจำนวนเต็ม 1–127")
            return
        if not self.paths or not self.folder.get().strip():
            messagebox.showerror("ข้อมูลไม่ครบ", "กรุณาเพิ่มไฟล์และเลือกโฟลเดอร์ปลายทาง")
            return
        self.busy = True
        for widget in self.buttons + [self.run_button, self.spin, self.entry]:
            widget.configure(state="disabled")
        self.progress.configure(value=0, maximum=len(self.paths))
        self.status.set("กำลังทำงาน…")
        threading.Thread(target=self.process, args=(list(self.paths), Path(self.folder.get()), velocity), daemon=True).start()

    def process(self, paths, folder, velocity):
        successes = 0
        for index, source in enumerate(paths):
            counter = 0
            try:
                while True:
                    suffix = f"_{counter}" if counter else ""
                    target = folder / f"{source.stem}_GM1{suffix}.mid"
                    try:
                        convert_file(source, target, velocity)
                        break
                    except FileExistsError:
                        counter += 1
                successes += 1
                result = f"สำเร็จ: {target.name}"
            except Exception as exc:
                result = f"ผิดพลาด: {exc}"
            self.messages.put(("file", index, result))
        self.messages.put(("done", successes, len(paths)))

    def poll(self):
        try:
            while True:
                kind, first, second = self.messages.get_nowait()
                if kind == "file":
                    self.table.set(str(first), "status", second)
                    self.progress.configure(value=first + 1)
                else:
                    self.busy = False
                    for widget in self.buttons + [self.run_button, self.spin, self.entry]:
                        widget.configure(state="normal")
                    self.status.set(f"เสร็จแล้ว: สำเร็จ {first} / {second} ไฟล์ — ผิดพลาด {second - first} ไฟล์")
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def close(self):
        if self.busy:
            messagebox.showinfo("กำลังทำงาน", "กรุณารอให้บันทึกไฟล์ครบก่อนปิดโปรแกรม")
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    Application(root)
    root.mainloop()
