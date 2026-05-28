import tkinter as tk
from tkinter import ttk
from vcif_core import (
    get_v1_colors, get_v1_levels,
    get_v2_levels_rg, get_v2_levels_b,
    get_v3_levels,
    COLOR_V1, COLOR_V2, COLOR_V3
)


class VCIFPalette:
    def __init__(self, root):
        self.root = root
        self.root.title("VCIF Palette")
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(False, False)

        self.sel = None
        self.ver = tk.IntVar(value=COLOR_V2)
        self.blue_idx = tk.IntVar(value=0)

        self.build_ui()
        self.draw()

    def build_ui(self):
        hf = tk.Frame(self.root, bg="#1e1e2e")
        hf.pack(fill="x", padx=15, pady=(10, 5))
        tk.Label(hf, text="🎨 VCIF Palette", font=("Segoe UI", 16, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack(side="left")

        # Wersja
        vf = tk.Frame(self.root, bg="#313244")
        vf.pack(fill="x", padx=15, pady=5)
        tk.Label(vf, text="  Wersja:", font=("Segoe UI", 10, "bold"),
                 fg="#cdd6f4", bg="#313244").pack(side="left", pady=5)

        for val, txt in [(COLOR_V1, "V1 — 64 kolorów (2-2-2)"),
                         (COLOR_V2, "V2 — 256 kolorów (3-3-2)"),
                         (COLOR_V3, "V3 — 512 kolorów (3-3-3)")]:
            tk.Radiobutton(vf, text=txt, variable=self.ver, value=val,
                           font=("Consolas", 9), fg="#cdd6f4", bg="#313244",
                           selectcolor="#45475a", activebackground="#313244",
                           command=self.on_ver_change).pack(side="left", padx=6, pady=5)

        # Filtr Blue
        self.bf = tk.Frame(self.root, bg="#313244")
        self.bf.pack(fill="x", padx=15, pady=3)
        self.blue_widgets = []

        # Podgląd
        pv = tk.Frame(self.root, bg="#313244",
                      highlightbackground="#45475a", highlightthickness=1)
        pv.pack(fill="x", padx=15, pady=5)
        pi = tk.Frame(pv, bg="#313244")
        pi.pack(fill="x", padx=10, pady=8)

        self.cbig = tk.Frame(pi, width=55, height=55, bg="#1e1e2e",
                             highlightbackground="#585b70", highlightthickness=2)
        self.cbig.pack(side="left", padx=(0, 12))
        self.cbig.pack_propagate(False)

        info = tk.Frame(pi, bg="#313244")
        info.pack(side="left", fill="both", expand=True)

        self.vars = {}
        for lbl, key in [("HEX", "hex"), ("RGB", "rgb"),
                         ("Bity", "bits"), ("Bajt/Kod", "code")]:
            row = tk.Frame(info, bg="#313244")
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{lbl}:", font=("Consolas", 10, "bold"),
                     fg="#89b4fa", bg="#313244", width=8, anchor="w").pack(side="left")
            v = tk.StringVar(value="—")
            self.vars[key] = v
            tk.Entry(row, textvariable=v, font=("Consolas", 10),
                     fg="#cdd6f4", bg="#45475a", readonlybackground="#45475a",
                     selectbackground="#89b4fa", selectforeground="#1e1e2e",
                     relief="flat", state="readonly", width=38).pack(side="left", padx=5)
            tk.Button(row, text="📋", font=("Segoe UI", 8),
                      fg="#cdd6f4", bg="#585b70", activebackground="#6c7086",
                      relief="flat", padx=3, cursor="hand2",
                      command=lambda vr=v, n=lbl: self.copy(vr, n)).pack(side="left")

        # Siatka
        self.gf = tk.Frame(self.root, bg="#1e1e2e")
        self.gf.pack(padx=15, pady=5)

        # Status
        self.stv = tk.StringVar(value="  Kliknij kolor")
        tk.Label(self.root, textvariable=self.stv,
                 font=("Consolas", 9), fg="#a6adc8", bg="#313244",
                 anchor="w", padx=10, pady=5).pack(fill="x", side="bottom")

    def on_ver_change(self):
        self.blue_idx.set(0)
        self.draw()

    def draw(self):
        # Wyczyść
        for w in self.gf.winfo_children(): w.destroy()
        for w in self.bf.winfo_children(): w.destroy()
        self.sel = None

        ver = self.ver.get()

        if ver == COLOR_V1:
            self._draw_blue_filter(get_v1_levels(), "2-bit")
            self._draw_v1()
        elif ver == COLOR_V2:
            self._draw_blue_filter(get_v2_levels_b(), "2-bit")
            self._draw_v2()
        else:
            self._draw_blue_filter(get_v3_levels(), "3-bit")
            self._draw_v3()

    def _draw_blue_filter(self, b_levels, bits):
        tk.Label(self.bf, text=f"  Blue ({bits}):",
                 font=("Segoe UI", 10, "bold"),
                 fg="#cdd6f4", bg="#313244").pack(side="left", pady=5)
        for i, bv in enumerate(b_levels):
            tk.Radiobutton(self.bf, text=f"{bv}",
                           variable=self.blue_idx, value=i,
                           font=("Consolas", 9), fg="#cdd6f4", bg="#313244",
                           selectcolor="#45475a", activebackground="#313244",
                           command=self.draw).pack(side="left", padx=3, pady=5)

    def _draw_v1(self):
        levels = get_v1_levels()
        bi = self.blue_idx.get()
        bv = levels[bi]
        self._draw_grid(levels, levels, bv,
                        lambda r, g, b: (levels.index(r), levels.index(g), levels.index(b)),
                        lambda rc, gc, bc: f"{rc}{gc}{bc}",
                        lambda rc, gc, bc: (rc << 6) | (gc << 4) | (bc << 2),
                        lambda rc, gc, bc: f"R={rc:02b} G={gc:02b} B={bc:02b}",
                        8, "V1")

    def _draw_v2(self):
        rg = get_v2_levels_rg()
        bl = get_v2_levels_b()
        bi = self.blue_idx.get()
        bv = bl[bi]
        self._draw_grid(rg, rg, bv,
                        lambda r, g, b: (rg.index(r), rg.index(g), bl.index(b)),
                        lambda rc, gc, bc: f"{rc:X}{gc:X}{bc:X}",
                        lambda rc, gc, bc: (rc << 5) | (gc << 2) | bc,
                        lambda rc, gc, bc: f"R={rc:03b} G={gc:03b} B={bc:02b}",
                        8, "V2")

    def _draw_v3(self):
        levels = get_v3_levels()
        bi = self.blue_idx.get()
        bv = levels[bi]
        self._draw_grid(levels, levels, bv,
                        lambda r, g, b: (levels.index(r), levels.index(g), levels.index(b)),
                        lambda rc, gc, bc: f"{rc:o}{gc:o}{bc:o}",
                        lambda rc, gc, bc: (rc << 6) | (gc << 3) | bc,
                        lambda rc, gc, bc: f"R={rc:03b} G={gc:03b} B={bc:03b}",
                        9, "V3")

    def _draw_grid(self, r_levels, g_levels, b_val,
                   get_codes, fmt_short, calc_byte, fmt_bits, bits_total, ver_name):
        n_r = len(r_levels)
        n_g = len(g_levels)
        sz = 38 if n_r <= 4 else 34

        tk.Label(self.gf, text=f"{ver_name}: Blue={b_val} — {n_r}×{n_g} kolorów",
                 font=("Consolas", 9), fg="#6c7086", bg="#1e1e2e").grid(
            row=0, column=0, columnspan=n_g + 1, sticky="w", pady=(0, 3))

        for gi in range(n_g):
            tk.Label(self.gf, text=f"G{gi}", font=("Consolas", 7),
                     fg="#585b70", bg="#1e1e2e").grid(row=1, column=gi + 1)

        for ri, rv in enumerate(r_levels):
            tk.Label(self.gf, text=f"R{ri}", font=("Consolas", 8),
                     fg="#585b70", bg="#1e1e2e", width=3).grid(row=ri + 2, column=0)

            for gi, gv in enumerate(g_levels):
                hx = f"#{rv:02x}{gv:02x}{b_val:02x}"
                br = rv * 0.299 + gv * 0.587 + b_val * 0.114
                tc = "#000" if br > 100 else "#fff"

                rc, gc, bc = get_codes(rv, gv, b_val)
                short = fmt_short(rc, gc, bc)

                cell = tk.Frame(self.gf, width=sz, height=sz - 4, bg=hx,
                                highlightbackground="#45475a",
                                highlightthickness=1, cursor="hand2")
                cell.grid(row=ri + 2, column=gi + 1, padx=1, pady=1)
                cell.pack_propagate(False)

                lbl = tk.Label(cell, text=short, font=("Consolas", 7),
                               fg=tc, bg=hx, cursor="hand2")
                lbl.pack(expand=True)

                rgb = (rv, gv, b_val)
                meta = (get_codes, calc_byte, fmt_bits, bits_total, ver_name)
                for w in (cell, lbl):
                    w.bind("<Button-1>",
                           lambda e, c=rgb, f=cell, m=meta: self.select(c, f, m))
                    w.bind("<Enter>",
                           lambda e, f=cell: f.configure(
                               highlightbackground="#f9e2af", highlightthickness=2))
                    w.bind("<Leave>",
                           lambda e, f=cell: self._rst(f))

    def _rst(self, f):
        if self.sel is f:
            f.configure(highlightbackground="#a6e3a1", highlightthickness=2)
        else:
            f.configure(highlightbackground="#45475a", highlightthickness=1)

    def select(self, rgb, frame, meta):
        if self.sel:
            self.sel.configure(highlightbackground="#45475a", highlightthickness=1)
        self.sel = frame
        frame.configure(highlightbackground="#a6e3a1", highlightthickness=2)

        r, g, b = rgb
        get_codes, calc_byte, fmt_bits, bits_total, ver_name = meta
        rc, gc, bc = get_codes(r, g, b)
        byte_val = calc_byte(rc, gc, bc)
        bits_str = fmt_bits(rc, gc, bc)

        self.cbig.configure(bg=f"#{r:02x}{g:02x}{b:02x}")
        self.vars["hex"].set(f"#{r:02x}{g:02x}{b:02x}")
        self.vars["rgb"].set(f"rgb({r}, {g}, {b})")
        self.vars["bits"].set(f"{bits_str}  [{ver_name}, {bits_total} bit]")

        if bits_total <= 8:
            self.vars["code"].set(
                f"0x{byte_val:02X}  ({byte_val})  0b{byte_val:08b}")
        else:
            self.vars["code"].set(
                f"0x{byte_val:03X}  ({byte_val})  0b{byte_val:09b}")

        self.stv.set(
            f"  {ver_name} | #{r:02x}{g:02x}{b:02x} | "
            f"kod: 0x{byte_val:03X} | 📋 kopiuj")

    def copy(self, var, name):
        val = var.get()
        if val == "—": return
        self.root.clipboard_clear()
        self.root.clipboard_append(val)
        self.stv.set(f"  ✅ Skopiowano {name}: {val}")
        self.root.after(2000, lambda: self.stv.set("  Kliknij kolor"))


if __name__ == "__main__":
    root = tk.Tk()
    VCIFPalette(root)
    root.mainloop()