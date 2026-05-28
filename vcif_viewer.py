from PIL import Image, ImageTk
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

from vcif_core import load_vcif, format_size


class VCIFViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("VCIF Viewer")
        self.root.geometry("900x700")
        self.root.minsize(600, 500)
        self.root.configure(bg="#1e1e2e")

        self.img = None
        self.photo = None
        self.zoom = 1.0
        self.dx = self.dy = 0
        self.ox = self.oy = 0
        self.rp = False
        self.loading = False

        self.build_ui()
        self.bind_events()

    def build_ui(self):
        tb = tk.Frame(self.root, bg="#313244", height=50)
        tb.pack(fill="x", side="top")
        tb.pack_propagate(False)

        tk.Button(tb, text="📂 Otwórz", font=("Segoe UI", 11, "bold"),
                  fg="#1e1e2e", bg="#a6e3a1", activebackground="#94e2d5",
                  relief="flat", padx=15, pady=5, cursor="hand2",
                  command=self.open_file).pack(side="left", padx=10, pady=8)

        zf = tk.Frame(tb, bg="#313244")
        zf.pack(side="left", padx=10)
        for t, c in [("🔍+", self.zi), ("🔍−", self.zo),
                     ("⊞", self.zf), ("1:1", self.zr)]:
            tk.Button(zf, text=t, font=("Segoe UI", 10),
                      fg="#cdd6f4", bg="#45475a", activebackground="#585b70",
                      relief="flat", padx=8, pady=3, cursor="hand2",
                      command=c).pack(side="left", padx=2)

        self.zv = tk.StringVar(value="100%")
        tk.Label(tb, textvariable=self.zv, font=("Consolas", 11, "bold"),
                 fg="#f9e2af", bg="#313244").pack(side="left", padx=10)

        self.cv = tk.StringVar(value="")
        tk.Label(tb, textvariable=self.cv, font=("Consolas", 10),
                 fg="#cdd6f4", bg="#313244").pack(side="right", padx=10)

        self.cp = tk.Frame(tb, width=25, height=25, bg="#313244",
                           highlightbackground="#585b70", highlightthickness=1)
        self.cp.pack(side="right", pady=8)
        self.cp.pack_propagate(False)

        self.canvas = tk.Canvas(self.root, bg="#11111b",
                                highlightthickness=0, cursor="fleur")
        self.canvas.pack(fill="both", expand=True, side="top")

        self.wt = self.canvas.create_text(
            0, 0, text="📂 Otwórz plik .vcif\n\nAutomatyczne wykrywanie V1/V2/V3\nCtrl+O • Scroll = Zoom",
            font=("Segoe UI", 16), fill="#45475a", justify="center")

        ib = tk.Frame(self.root, bg="#313244", height=50)
        ib.pack(fill="x", side="bottom")
        ib.pack_propagate(False)
        self.iv = tk.StringVar(value="  Otwórz plik VCIF")
        tk.Label(ib, textvariable=self.iv, font=("Consolas", 9),
                 fg="#a6adc8", bg="#313244", anchor="w",
                 padx=10, pady=5).pack(fill="both", expand=True)

    def bind_events(self):
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<ButtonPress-1>", self.ds)
        self.canvas.bind("<B1-Motion>", self.dm)
        self.canvas.bind("<MouseWheel>", self.sc)
        self.canvas.bind("<Button-4>", lambda e: self.zi(e))
        self.canvas.bind("<Button-5>", lambda e: self.zo(e))
        self.canvas.bind("<Motion>", self.mm)
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-plus>", lambda e: self.zi())
        self.root.bind("<Control-minus>", lambda e: self.zo())
        self.root.bind("<Control-0>", lambda e: self.zr())
        self.root.bind("<Control-f>", lambda e: self.zf())

    def open_file(self):
        if self.loading: return
        p = filedialog.askopenfilename(
            title="Otwórz VCIF",
            filetypes=[("VCIF", "*.vcif"), ("Wszystkie", "*.*")])
        if p: self.load(p)

    def load(self, path):
        self.loading = True
        self.iv.set("  ⏳ Ładowanie...")

        def task():
            try:
                t = time.perf_counter()
                img, st = load_vcif(path)
                st["time"] = time.perf_counter() - t
                self.root.after(0, self._loaded, img, st)
            except Exception as e:
                self.root.after(0, self._lerr, e)

        threading.Thread(target=task, daemon=True).start()

    def _loaded(self, img, s):
        self.loading = False
        self.img = img
        self.ox = self.oy = 0
        self.canvas.delete(self.wt)
        self.zf()

        sv = 100 - s["ratio"]
        self.iv.set(
            f"  📄 {s['filename']}  "
            f"📐 {s['width']}×{s['height']}  "
            f"🎨 {s['pixels']:,}px  "
            f"🏷️ {s['color_name']}  "
            f"🗜️ {s['comp_name']}  "
            f"📦 {format_size(s['file_size'])}  "
            f"📊 {s['bpp']:.1f}bpp  "
            f"💾 {sv:.1f}%  "
            f"⚡ {s['time']*1000:.0f}ms")
        self.root.title(f"VCIF Viewer — {s['filename']}")

    def _lerr(self, e):
        self.loading = False
        messagebox.showerror("Błąd", str(e))

    def sr(self):
        if not self.rp:
            self.rp = True
            self.root.after(8, self._dr)

    def _dr(self):
        self.rp = False
        if not self.img: return

        self.canvas.delete("img")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        iw, ih = self.img.size

        nw = max(1, int(iw * self.zoom))
        nh = max(1, int(ih * self.zoom))
        il = cw // 2 + self.ox - nw // 2
        it = ch // 2 + self.oy - nh // 2

        x1 = max(0, int(-il / self.zoom))
        y1 = max(0, int(-it / self.zoom))
        x2 = min(iw, int((cw - il) / self.zoom) + 1)
        y2 = min(ih, int((ch - it) / self.zoom) + 1)
        if x2 <= x1 or y2 <= y1: return

        cr = self.img.crop((x1, y1, x2, y2))
        cw2 = max(1, int((x2 - x1) * self.zoom))
        ch2 = max(1, int((y2 - y1) * self.zoom))
        rs = Image.NEAREST if self.zoom >= 1 else Image.LANCZOS
        rz = cr.resize((cw2, ch2), rs)

        self.photo = ImageTk.PhotoImage(rz)
        px = il + int(x1 * self.zoom) + cw2 // 2
        py = it + int(y1 * self.zoom) + ch2 // 2
        self.canvas.create_image(px, py, image=self.photo, anchor="center", tags="img")
        self.zv.set(f"{self.zoom * 100:.0f}%")

    def on_resize(self, e):
        if not self.img:
            w = self.canvas.winfo_width() or 900
            h = self.canvas.winfo_height() or 600
            self.canvas.coords(self.wt, w // 2, h // 2)
        else:
            self.sr()

    def ds(self, e): self.dx, self.dy = e.x, e.y
    def dm(self, e):
        self.ox += e.x - self.dx; self.oy += e.y - self.dy
        self.dx, self.dy = e.x, e.y; self.sr()

    def sc(self, e): (self.zi if e.delta > 0 else self.zo)(e)

    def zi(self, e=None):
        if not self.img: return
        o = self.zoom; self.zoom = min(64, self.zoom * 1.3)
        if e and hasattr(e, 'x'): self._adj(e.x, e.y, o)
        self.sr()

    def zo(self, e=None):
        if not self.img: return
        o = self.zoom; self.zoom = max(0.01, self.zoom / 1.3)
        if e and hasattr(e, 'x'): self._adj(e.x, e.y, o)
        self.sr()

    def _adj(self, mx, my, o):
        cw = self.canvas.winfo_width(); ch = self.canvas.winfo_height()
        cx, cy = cw//2 + self.ox, ch//2 + self.oy
        f = self.zoom / o
        self.ox = int(mx - (mx - cx) * f) - cw // 2
        self.oy = int(my - (my - cy) * f) - ch // 2

    def zr(self):
        if not self.img: return
        self.zoom = 1.0; self.ox = self.oy = 0; self.sr()

    def zf(self):
        if not self.img: return
        cw = self.canvas.winfo_width() or 900
        ch = self.canvas.winfo_height() or 600
        iw, ih = self.img.size
        self.zoom = min((cw-40)/iw, (ch-40)/ih, 8.0)
        self.ox = self.oy = 0; self.sr()

    def mm(self, e):
        if not self.img: return
        cw = self.canvas.winfo_width(); ch = self.canvas.winfo_height()
        iw, ih = self.img.size
        il = cw/2 + self.ox - iw*self.zoom/2
        it = ch/2 + self.oy - ih*self.zoom/2
        px = int((e.x - il) / self.zoom)
        py = int((e.y - it) / self.zoom)
        if 0 <= px < iw and 0 <= py < ih:
            r, g, b = self.img.getpixel((px, py))[:3]
            hx = f"#{r:02x}{g:02x}{b:02x}"
            self.cv.set(f"({px},{py}) RGB({r},{g},{b}) {hx}")
            self.cp.configure(bg=hx)
        else:
            self.cv.set(""); self.cp.configure(bg="#313244")


if __name__ == "__main__":
    root = tk.Tk()
    VCIFViewer(root)
    root.mainloop()