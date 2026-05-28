import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from vcif_core import (
    convert_to_vcif, convert_from_vcif, load_vcif, format_size,
    SUPPORTED_FORMATS, EXPORT_FORMATS, COMPRESSION_MODES, COLOR_MODES,
    COLOR_SHORT, COMP_NAMES
)


class VCIFConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VCIF Converter")
        self.root.geometry("680x780")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"),
                             foreground="#cdd6f4", background="#1e1e2e")
        self.style.configure("Sub.TLabel", font=("Segoe UI", 10),
                             foreground="#6c7086", background="#1e1e2e")
        self.style.configure("Action.TButton", font=("Segoe UI", 11, "bold"),
                             padding=(20, 10))
        self.style.configure("Quick.TButton", font=("Segoe UI", 10, "bold"),
                             padding=(15, 8))
        self.style.configure("P.Horizontal.TProgressbar",
                             troughcolor="#313244", background="#89b4fa",
                             thickness=18)
        self.busy = False
        self.build_ui()

    def build_ui(self):
        # Header
        hf = tk.Frame(self.root, bg="#1e1e2e")
        hf.pack(pady=(12, 3))
        ttk.Label(hf, text="🖼️ VCIF Converter", style="Title.TLabel").pack()
        ttk.Label(hf, text="V1 (64col) • V2 (256col) • V3 (512col) • RLE/ZLIB",
                  style="Sub.TLabel").pack(pady=(2, 0))

        self._sep()

        # === Obraz → VCIF ===
        s1 = self._section("📥  Obraz → VCIF",
                           "Konwertuj obraz do formatu VCIF")

        r1 = tk.Frame(s1, bg="#1e1e2e")
        r1.pack(fill="x", pady=(0, 4))
        tk.Label(r1, text="Kolory:", font=("Segoe UI", 10, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack(side="left")
        self.color_var = tk.StringVar(value=list(COLOR_MODES.keys())[1])
        ttk.Combobox(r1, textvariable=self.color_var,
                     values=list(COLOR_MODES.keys()),
                     state="readonly", width=30).pack(side="left", padx=(8, 0))

        r2 = tk.Frame(s1, bg="#1e1e2e")
        r2.pack(fill="x", pady=(0, 8))
        tk.Label(r2, text="Kompresja:", font=("Segoe UI", 10, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack(side="left")
        self.comp_var = tk.StringVar(value="Auto (najmniejszy)")
        ttk.Combobox(r2, textvariable=self.comp_var,
                     values=list(COMPRESSION_MODES.keys()),
                     state="readonly", width=30).pack(side="left", padx=(8, 0))

        self.btn_to = ttk.Button(s1, text="Wybierz obraz → zapisz jako .vcif",
                                 style="Action.TButton", command=self.act_to)
        self.btn_to.pack(fill="x")

        self._sep()

        # === VCIF → Obraz ===
        s2 = self._section("📤  VCIF → Obraz",
                           "Automatycznie wykrywa wersję (V1/V2/V3)")

        r3 = tk.Frame(s2, bg="#1e1e2e")
        r3.pack(fill="x", pady=(0, 8))
        tk.Label(r3, text="Format:", font=("Segoe UI", 10, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack(side="left")
        self.exp_var = tk.StringVar(value="PNG (.png)")
        ttk.Combobox(r3, textvariable=self.exp_var,
                     values=list(EXPORT_FORMATS.keys()),
                     state="readonly", width=15).pack(side="left", padx=(8, 0))

        self.btn_from = ttk.Button(s2, text="Wybierz .vcif → zapisz jako obraz",
                                   style="Action.TButton", command=self.act_from)
        self.btn_from.pack(fill="x")

        self._sep()

        # === Szybka konwersja ===
        s3 = self._section("⚡  Szybka konwersja",
                           "Obraz → konwersja przez VCIF → zapisz jako obraz (PNG/JPG/BMP)")

        r4 = tk.Frame(s3, bg="#1e1e2e")
        r4.pack(fill="x", pady=(0, 8))
        tk.Label(r4, text="Format wyniku:", font=("Segoe UI", 10, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack(side="left")
        self.quick_fmt = tk.StringVar(value="PNG (.png)")
        ttk.Combobox(r4, textvariable=self.quick_fmt,
                     values=list(EXPORT_FORMATS.keys()),
                     state="readonly", width=15).pack(side="left", padx=(8, 0))

        tk.Label(s3,
                 text="  ℹ️  Używa wybranych ustawień kolorów i kompresji powyżej",
                 font=("Segoe UI", 9), fg="#6c7086", bg="#1e1e2e",
                 anchor="w").pack(fill="x", pady=(0, 8))

        self.btn_quick = ttk.Button(
            s3, text="Wybierz obraz → zapisz przekonwertowany",
            style="Quick.TButton", command=self.act_quick)
        self.btn_quick.pack(fill="x")

        # Progress
        pf = tk.Frame(self.root, bg="#1e1e2e")
        pf.pack(fill="x", padx=40, pady=(12, 4))
        self.progress = ttk.Progressbar(pf, style="P.Horizontal.TProgressbar",
                                        mode="determinate", maximum=100)
        self.progress.pack(fill="x")

        # Stats
        sf = tk.Frame(self.root, bg="#313244",
                      highlightbackground="#45475a", highlightthickness=1)
        sf.pack(fill="x", padx=40, pady=(6, 12))
        self.stats_var = tk.StringVar(value="  Gotowy")
        tk.Label(sf, textvariable=self.stats_var,
                 font=("Consolas", 9), fg="#a6adc8", bg="#313244",
                 anchor="w", justify="left",
                 padx=10, pady=8).pack(fill="x")

    def _sep(self):
        tk.Frame(self.root, bg="#45475a", height=1).pack(fill="x", padx=40, pady=8)

    def _section(self, title, desc):
        f = tk.Frame(self.root, bg="#1e1e2e")
        f.pack(fill="x", padx=40, pady=(0, 4))
        tk.Label(f, text=title, font=("Segoe UI", 12, "bold"),
                 fg="#a6e3a1", bg="#1e1e2e", anchor="w").pack(fill="x")
        tk.Label(f, text=desc, font=("Segoe UI", 9),
                 fg="#6c7086", bg="#1e1e2e", anchor="w").pack(fill="x", pady=(1, 6))
        return f

    def _set_busy(self, busy):
        self.busy = busy
        st = "disabled" if busy else "normal"
        self.btn_to.configure(state=st)
        self.btn_from.configure(state=st)
        self.btn_quick.configure(state=st)

    def _upd(self, v):
        self.progress["value"] = v
        self.root.update_idletasks()

    def _thread(self, fn):
        if self.busy: return
        self._set_busy(True)
        threading.Thread(target=fn, daemon=True).start()

    def _done(self, txt, msg):
        self.busy = False
        self._set_busy(False)
        self.stats_var.set(txt)
        messagebox.showinfo("Sukces", msg)

    def _err(self, e):
        self.busy = False
        self._set_busy(False)
        self.progress["value"] = 0
        self.stats_var.set(f"  ❌ {e}")
        messagebox.showerror("Błąd", str(e))

    def _get_color(self):
        return COLOR_MODES[self.color_var.get()]

    def _get_comp(self):
        return COMPRESSION_MODES[self.comp_var.get()]

    # === Obraz → VCIF ===
    def act_to(self):
        inp = filedialog.askopenfilename(title="Wybierz obraz",
                                         filetypes=SUPPORTED_FORMATS)
        if not inp: return
        out = filedialog.asksaveasfilename(
            title="Zapisz VCIF", defaultextension=".vcif",
            initialfile=os.path.splitext(os.path.basename(inp))[0] + ".vcif",
            filetypes=[("VCIF", "*.vcif")])
        if not out: return

        cv, cm = self._get_color(), self._get_comp()

        def task():
            try:
                self.root.after(0, lambda: self.stats_var.set("  ⏳ Konwertowanie..."))
                s = convert_to_vcif(inp, out, cv, cm,
                                    lambda v: self.root.after(0, self._upd, v))
                sav = 100 - s["ratio"]
                txt = (f"  ✅ Sukces!\n"
                       f"  {s['width']}×{s['height']} ({s['pixels']:,} px)\n"
                       f"  Wersja: {s['color_name']}  |  Kompresja: {s['comp_name']}\n"
                       f"  Oryginał: {format_size(s['original_size'])}\n"
                       f"  VCIF surowe: {format_size(s['raw_size'])} ({s['bpp']:.1f} bpp)\n"
                       f"  VCIF final: {format_size(s['compressed_size'])} "
                       f"({s['ratio']:.1f}%, oszcz: {sav:.1f}%)\n"
                       f"  Plik: {format_size(s['file_size'])}")
                self.root.after(0, self._done, txt,
                                f"{s['color_name']} | {s['comp_name']} | "
                                f"{format_size(s['file_size'])}")
            except Exception as e:
                self.root.after(0, self._err, e)

        self._thread(task)

    # === VCIF → Obraz ===
    def act_from(self):
        inp = filedialog.askopenfilename(
            title="Wybierz VCIF",
            filetypes=[("VCIF", "*.vcif"), ("Wszystkie", "*.*")])
        if not inp: return

        ext = EXPORT_FORMATS[self.exp_var.get()]
        base = os.path.splitext(os.path.basename(inp))[0]
        out = filedialog.asksaveasfilename(
            title="Zapisz jako", defaultextension=ext,
            initialfile=base + ext,
            filetypes=[({".png": "PNG", ".jpg": "JPEG", ".bmp": "BMP"}[ext],
                        f"*{ext}")])
        if not out: return

        def task():
            try:
                self.root.after(0, lambda: self.stats_var.set("  ⏳ Dekodowanie..."))
                s = convert_from_vcif(inp, out,
                                      lambda v: self.root.after(0, self._upd, v))
                vs = os.path.getsize(inp)
                txt = (f"  ✅ Sukces!\n"
                       f"  {s['width']}×{s['height']} ({s['pixels']:,} px)\n"
                       f"  Wykryto: {s['color_name']}  |  Kompresja: {s['comp_name']}\n"
                       f"  VCIF: {format_size(vs)} → Wynik: {format_size(s['file_size'])}")
                self.root.after(0, self._done, txt, f"Zapisano: {out}")
            except Exception as e:
                self.root.after(0, self._err, e)

        self._thread(task)

    # === Szybka konwersja ===
    def act_quick(self):
        inp = filedialog.askopenfilename(
            title="Wybierz obraz do szybkiej konwersji",
            filetypes=SUPPORTED_FORMATS)
        if not inp: return

        ext = EXPORT_FORMATS[self.quick_fmt.get()]
        base = os.path.splitext(os.path.basename(inp))[0]

        out = filedialog.asksaveasfilename(
            title="Zapisz przekonwertowany obraz",
            defaultextension=ext,
            initialfile=base + "_vcif" + ext,
            filetypes=[({".png": "PNG", ".jpg": "JPEG", ".bmp": "BMP"}[ext],
                        f"*{ext}")])
        if not out: return

        cv, cm = self._get_color(), self._get_comp()

        def task():
            try:
                self.root.after(0, lambda: self.stats_var.set(
                    "  ⚡ Szybka konwersja: obraz → VCIF → obraz..."))

                # Krok 1: Obraz → VCIF (w pamięci przez plik tymczasowy)
                import tempfile
                tmp = tempfile.mktemp(suffix=".vcif")

                self.root.after(0, lambda: self._upd(5))

                s = convert_to_vcif(inp, tmp, cv, cm,
                                    lambda v: self.root.after(0, self._upd, 5 + v * 0.4))

                # Krok 2: VCIF → obraz wynikowy
                self.root.after(0, lambda: self._upd(50))

                img, st = load_vcif(tmp,
                                    lambda v: self.root.after(0, self._upd, 50 + v * 0.4))

                self.root.after(0, lambda: self._upd(90))

                img.save(out)

                # Usuń tymczasowy VCIF
                try:
                    os.remove(tmp)
                except OSError:
                    pass

                self.root.after(0, lambda: self._upd(100))

                out_size = os.path.getsize(out)
                sav = 100 - s["ratio"]

                txt = (f"  ✅ Szybka konwersja zakończona!\n"
                       f"  {s['width']}×{s['height']} ({s['pixels']:,} px)\n"
                       f"  Wersja: {s['color_name']}  |  Kompresja: {s['comp_name']}\n"
                       f"  Oryginał:     {format_size(s['original_size'])}\n"
                       f"  VCIF (temp):  {format_size(s['file_size'])} "
                       f"({s['bpp']:.1f} bpp, {sav:.1f}% kompresji)\n"
                       f"  Wynik:        {format_size(out_size)}\n"
                       f"  Zapisano: {os.path.basename(out)}")

                self.root.after(0, self._done, txt,
                                f"Szybka konwersja zakończona!\n\n"
                                f"Wersja: {s['color_name']}\n"
                                f"Oryginał: {format_size(s['original_size'])}\n"
                                f"Wynik: {format_size(out_size)}\n\n"
                                f"Zapisano: {out}")

            except Exception as e:
                # Cleanup
                try:
                    os.remove(tmp)
                except (OSError, UnboundLocalError):
                    pass
                self.root.after(0, self._err, e)

        self._thread(task)


if __name__ == "__main__":
    root = tk.Tk()
    VCIFConverterApp(root)
    root.mainloop()