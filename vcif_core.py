from PIL import Image
import numpy as np
import struct
import os
import zlib

# ==================== FORMAT VCIF ====================
# V1: RR GG BB XX  — 2-2-2 bit, 64 kolorów, 1 bajt/piksel
# V2: RRR GGG BB   — 3-3-2 bit, 256 kolorów, 1 bajt/piksel
# V3: RRR GGG BBB  — 3-3-3 bit, 512 kolorów, 9 bit/piksel (8px = 9 bajtów)

# Wersje kolorów
COLOR_V1 = 1  # 64 kolorów
COLOR_V2 = 2  # 256 kolorów
COLOR_V3 = 3  # 512 kolorów

COLOR_NAMES = {
    COLOR_V1: "V1 (64 kolorów, 2-2-2)",
    COLOR_V2: "V2 (256 kolorów, 3-3-2)",
    COLOR_V3: "V3 (512 kolorów, 3-3-3)"
}

COLOR_SHORT = {
    COLOR_V1: "V1 64col",
    COLOR_V2: "V2 256col",
    COLOR_V3: "V3 512col"
}

# Kompresja
COMP_RAW = 0
COMP_RLE = 1
COMP_ZLIB = 2

COMP_NAMES = {
    COMP_RAW: "Brak",
    COMP_RLE: "RLE",
    COMP_ZLIB: "ZLIB"
}

COMPRESSION_MODES = {
    "Brak kompresji": COMP_RAW,
    "RLE": COMP_RLE,
    "ZLIB": COMP_ZLIB,
    "Auto (najmniejszy)": -1
}

COLOR_MODES = {
    "V1 — 64 kolorów (2-2-2)": COLOR_V1,
    "V2 — 256 kolorów (3-3-2)": COLOR_V2,
    "V3 — 512 kolorów (3-3-3)": COLOR_V3
}

SUPPORTED_FORMATS = [
    ("Obrazy", "*.png *.jpg *.jpeg *.bmp"),
    ("PNG", "*.png"),
    ("JPEG", "*.jpg *.jpeg"),
    ("BMP", "*.bmp"),
    ("Wszystkie", "*.*")
]

EXPORT_FORMATS = {
    "PNG (.png)": ".png",
    "JPEG (.jpg)": ".jpg",
    "BMP (.bmp)": ".bmp"
}

# ==================== LOOKUP TABLES ====================

# V1: 2 bity = 4 poziomy
_V1_LEVELS = np.array([0, 85, 170, 255], dtype=np.uint8)
_V1_ENC = np.zeros(256, dtype=np.uint8)
for _v in range(256):
    _V1_ENC[_v] = round(_v * 3 / 255)

# V2: R,G 3 bity = 8 poziomów; B 2 bity = 4 poziomy
_V2_LEVELS_RG = np.array([round(i * 255 / 7) for i in range(8)], dtype=np.uint8)
_V2_LEVELS_B = np.array([0, 85, 170, 255], dtype=np.uint8)
_V2_ENC_RG = np.zeros(256, dtype=np.uint8)
_V2_ENC_B = np.zeros(256, dtype=np.uint8)
for _v in range(256):
    _V2_ENC_RG[_v] = round(_v * 7 / 255)
    _V2_ENC_B[_v] = round(_v * 3 / 255)

# V3: 3 bity = 8 poziomów na każdy kanał
_V3_LEVELS = np.array([round(i * 255 / 7) for i in range(8)], dtype=np.uint8)
_V3_ENC = np.zeros(256, dtype=np.uint8)
for _v in range(256):
    _V3_ENC[_v] = round(_v * 7 / 255)


# ==================== KONWERSJA PIKSELI ====================

def encode_v1(img: Image.Image) -> bytes:
    arr = np.array(img.convert("RGB"), dtype=np.uint8)
    r = _V1_ENC[arr[:, :, 0]]
    g = _V1_ENC[arr[:, :, 1]]
    b = _V1_ENC[arr[:, :, 2]]
    return bytes(((r << 6) | (g << 4) | (b << 2)).flatten())


def decode_v1(data: bytes, w: int, h: int) -> Image.Image:
    arr = np.frombuffer(data, dtype=np.uint8)[:w * h]
    r = _V1_LEVELS[(arr >> 6) & 0x03]
    g = _V1_LEVELS[(arr >> 4) & 0x03]
    b = _V1_LEVELS[(arr >> 2) & 0x03]
    return Image.fromarray(np.stack([r, g, b], -1).reshape(h, w, 3), "RGB")


def encode_v2(img: Image.Image) -> bytes:
    arr = np.array(img.convert("RGB"), dtype=np.uint8)
    r = _V2_ENC_RG[arr[:, :, 0]]
    g = _V2_ENC_RG[arr[:, :, 1]]
    b = _V2_ENC_B[arr[:, :, 2]]
    return bytes(((r << 5) | (g << 2) | b).flatten())


def decode_v2(data: bytes, w: int, h: int) -> Image.Image:
    arr = np.frombuffer(data, dtype=np.uint8)[:w * h]
    r = _V2_LEVELS_RG[(arr >> 5) & 0x07]
    g = _V2_LEVELS_RG[(arr >> 2) & 0x07]
    b = _V2_LEVELS_B[arr & 0x03]
    return Image.fromarray(np.stack([r, g, b], -1).reshape(h, w, 3), "RGB")


def encode_v3(img: Image.Image) -> bytes:
    arr = np.array(img.convert("RGB"), dtype=np.uint8)
    r = _V3_ENC[arr[:, :, 0]].astype(np.uint16)
    g = _V3_ENC[arr[:, :, 1]].astype(np.uint16)
    b = _V3_ENC[arr[:, :, 2]].astype(np.uint16)
    codes = ((r << 6) | (g << 3) | b).flatten()
    return _pack_9bit(codes)


def decode_v3(data: bytes, w: int, h: int) -> Image.Image:
    codes = _unpack_9bit(data, w * h)
    r = _V3_LEVELS[(codes >> 6) & 0x07]
    g = _V3_LEVELS[(codes >> 3) & 0x07]
    b = _V3_LEVELS[codes & 0x07]
    return Image.fromarray(np.stack([r, g, b], -1).reshape(h, w, 3), "RGB")


# ==================== V3 BIT PACKING ====================

def _pack_9bit(codes: np.ndarray) -> bytes:
    n = len(codes)
    pad = (8 - n % 8) % 8
    if pad:
        codes = np.concatenate([codes, np.zeros(pad, dtype=np.uint16)])
    total = len(codes)
    out = bytearray((total // 8) * 9)
    idx = 0
    for i in range(0, total, 8):
        bits = 0
        for j in range(8):
            bits = (bits << 9) | int(codes[i + j])
        for j in range(8, -1, -1):
            out[idx + j] = bits & 0xFF
            bits >>= 8
        idx += 9
    return bytes(out)


def _unpack_9bit(data: bytes, num_pixels: int) -> np.ndarray:
    codes = np.zeros(num_pixels, dtype=np.uint16)
    blocks = len(data) // 9
    px = 0
    for bl in range(blocks):
        off = bl * 9
        bits = 0
        for j in range(9):
            bits = (bits << 8) | data[off + j]
        for j in range(7, -1, -1):
            if px + j < num_pixels:
                codes[px + j] = bits & 0x1FF
            bits >>= 9
        px += 8
    return codes[:num_pixels]


def _raw_size(color_ver: int, num_pixels: int) -> int:
    if color_ver == COLOR_V3:
        return ((num_pixels + 7) // 8) * 9
    return num_pixels


# ==================== KOMPRESJA ====================

def _rle_enc(data: bytes) -> bytes:
    n = len(data)
    if n == 0:
        return b""
    arr = np.frombuffer(data, dtype=np.uint8)
    out = bytearray()
    i = 0
    while i < n:
        v = arr[i]
        rl = 1
        while i + rl < n and arr[i + rl] == v and rl < 128:
            rl += 1
        if rl >= 3:
            out.append(0x80 | (rl - 1))
            out.append(int(v))
            i += rl
        else:
            ls = i
            lc = 0
            while i < n and lc < 128:
                pv = arr[i]
                pl = 1
                while i + pl < n and arr[i + pl] == pv and pl < 3:
                    pl += 1
                if pl >= 3 and lc > 0:
                    break
                i += 1
                lc += 1
            out.append(lc - 1)
            out.extend(arr[ls:ls + lc].tobytes())
    return bytes(out)


def _rle_dec(data: bytes, expected: int) -> bytes:
    out = bytearray()
    i = 0
    n = len(data)
    while i < n and len(out) < expected:
        h = data[i]; i += 1
        if h & 0x80:
            c = (h & 0x7F) + 1
            if i >= n: break
            v = data[i]; i += 1
            c = min(c, expected - len(out))
            out.extend(bytes([v]) * c)
        else:
            c = (h & 0x7F) + 1
            c = min(c, expected - len(out), n - i)
            out.extend(data[i:i + c])
            i += c
    return bytes(out[:expected])


def _compress(raw: bytes, mode: int) -> tuple:
    sz = len(raw)
    if mode == COMP_RAW:
        return COMP_RAW, raw
    if mode == COMP_RLE:
        c = _rle_enc(raw)
        return (COMP_RLE, c) if len(c) < sz else (COMP_RAW, raw)
    if mode == COMP_ZLIB:
        c = zlib.compress(raw, 9)
        return (COMP_ZLIB, c) if len(c) < sz else (COMP_RAW, raw)
    # Auto
    bv, bd, bs = COMP_RAW, raw, sz
    r = _rle_enc(raw)
    if len(r) < bs: bv, bd, bs = COMP_RLE, r, len(r)
    z = zlib.compress(raw, 9)
    if len(z) < bs: bv, bd = COMP_ZLIB, z
    return bv, bd


def _decompress(data: bytes, comp: int, expected: int) -> bytes:
    if comp == COMP_RAW: return data
    if comp == COMP_RLE: return _rle_dec(data, expected)
    if comp == COMP_ZLIB: return zlib.decompress(data)
    raise ValueError(f"Nieznana kompresja: {comp}")


# ==================== PLIK I/O ====================
# Header: "VCIF" (4B) + color_ver (1B) + comp (1B) + width (4B) + height (4B) + data_size (4B)
# Total header: 18 bajtów

HEADER_SIZE = 18


def _write(path, color_ver, comp, w, h, data):
    with open(path, "wb") as f:
        f.write(b"VCIF")
        f.write(struct.pack("<BB", color_ver, comp))
        f.write(struct.pack("<III", w, h, len(data)))
        f.write(data)


def _read(path):
    with open(path, "rb") as f:
        content = f.read()
    if len(content) < HEADER_SIZE:
        raise ValueError("Plik za mały!")
    magic = content[:4]
    if magic != b"VCIF":
        raise ValueError("Nie jest plikiem VCIF!")
    color_ver, comp = struct.unpack_from("<BB", content, 4)
    w, h, ds = struct.unpack_from("<III", content, 6)
    if color_ver not in (COLOR_V1, COLOR_V2, COLOR_V3):
        raise ValueError(f"Nieznana wersja kolorów: {color_ver}")
    if comp not in (COMP_RAW, COMP_RLE, COMP_ZLIB):
        raise ValueError(f"Nieznana kompresja: {comp}")
    fd = content[HEADER_SIZE:HEADER_SIZE + ds]
    expected = _raw_size(color_ver, w * h)
    raw = _decompress(fd, comp, expected)
    return color_ver, comp, w, h, raw, ds


# ==================== API ====================

ENCODERS = {COLOR_V1: encode_v1, COLOR_V2: encode_v2, COLOR_V3: encode_v3}
DECODERS = {COLOR_V1: decode_v1, COLOR_V2: decode_v2, COLOR_V3: decode_v3}


def convert_to_vcif(input_path, output_path, color_ver=COLOR_V2,
                    comp_mode=-1, progress_cb=None):
    if progress_cb: progress_cb(5)
    img = Image.open(input_path).convert("RGB")
    w, h = img.size
    total = w * h
    if progress_cb: progress_cb(15)

    raw = ENCODERS[color_ver](img)
    raw_sz = len(raw)
    if progress_cb: progress_cb(40)

    comp, final = _compress(raw, comp_mode)
    if progress_cb: progress_cb(80)

    _write(output_path, color_ver, comp, w, h, final)
    if progress_cb: progress_cb(100)

    rgb_raw = total * 3
    bpp = raw_sz * 8 / total if total else 0

    return {
        "width": w, "height": h, "pixels": total,
        "color_ver": color_ver,
        "color_name": COLOR_SHORT.get(color_ver, "?"),
        "comp": comp,
        "comp_name": COMP_NAMES.get(comp, "?"),
        "raw_size": raw_sz,
        "compressed_size": len(final),
        "file_size": os.path.getsize(output_path),
        "original_size": os.path.getsize(input_path),
        "ratio": len(final) / raw_sz * 100 if raw_sz else 100,
        "bpp": bpp,
        "savings_rgb": (1 - raw_sz / rgb_raw) * 100 if rgb_raw else 0
    }


def load_vcif(path, progress_cb=None):
    if progress_cb: progress_cb(5)
    color_ver, comp, w, h, raw, ds = _read(path)
    if progress_cb: progress_cb(30)

    img = DECODERS[color_ver](raw, w, h)
    if progress_cb: progress_cb(100)

    total = w * h
    rs = _raw_size(color_ver, total)
    fs = os.path.getsize(path)
    bpp = rs * 8 / total if total else 0

    return img, {
        "width": w, "height": h, "pixels": total,
        "color_ver": color_ver,
        "color_name": COLOR_SHORT.get(color_ver, "?"),
        "comp": comp,
        "comp_name": COMP_NAMES.get(comp, "?"),
        "file_size": fs, "data_size": ds,
        "raw_size": rs,
        "ratio": ds / rs * 100 if rs else 100,
        "bpp": bpp,
        "filename": os.path.basename(path),
        "path": path
    }


def convert_from_vcif(input_path, output_path, progress_cb=None):
    if progress_cb: progress_cb(5)
    img, stats = load_vcif(input_path)
    if progress_cb: progress_cb(60)
    img.save(output_path)
    if progress_cb: progress_cb(100)
    stats["file_size"] = os.path.getsize(output_path)
    return stats


def quick_convert(input_path, output_dir=None, color_ver=COLOR_V2,
                  comp_mode=-1, progress_cb=None):
    """Obraz → VCIF → PNG, zwraca (vcif_stats, output_path)"""
    base = os.path.splitext(os.path.basename(input_path))[0]
    if output_dir is None:
        output_dir = os.path.dirname(input_path)

    vcif_path = os.path.join(output_dir, base + ".vcif")
    out_path = os.path.join(output_dir, base + "_vcif.png")

    if progress_cb: progress_cb(5)
    stats = convert_to_vcif(input_path, vcif_path, color_ver, comp_mode,
                            lambda v: progress_cb(5 + v * 0.45) if progress_cb else None)
    if progress_cb: progress_cb(55)
    img, _ = load_vcif(vcif_path)
    if progress_cb: progress_cb(80)
    img.save(out_path)
    if progress_cb: progress_cb(100)

    stats["vcif_path"] = vcif_path
    stats["output_path"] = out_path
    stats["output_size"] = os.path.getsize(out_path)
    return stats


def format_size(b):
    if b < 1024: return f"{b} B"
    if b < 1048576: return f"{b/1024:.1f} KB"
    return f"{b/1048576:.2f} MB"


# Dane palet dla palette viewer
def get_v1_colors():
    lvl = [0, 85, 170, 255]
    return [(r, g, b) for r in lvl for g in lvl for b in lvl]


def get_v2_colors():
    rl = [round(i*255/7) for i in range(8)]
    gl = rl
    bl = [0, 85, 170, 255]
    return [(r, g, b) for r in rl for g in gl for b in bl]


def get_v3_colors():
    lvl = [round(i*255/7) for i in range(8)]
    return [(r, g, b) for r in lvl for g in lvl for b in lvl]


def get_v1_levels():
    return [0, 85, 170, 255]

def get_v2_levels_rg():
    return [round(i*255/7) for i in range(8)]

def get_v2_levels_b():
    return [0, 85, 170, 255]

def get_v3_levels():
    return [round(i*255/7) for i in range(8)]