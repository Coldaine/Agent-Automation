from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import io, base64, hashlib

from PIL import Image, ImageOps, ImageFilter

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None  # lazy error on use


@dataclass
class Region:
    x: int
    y: int
    w: int
    h: int
    text: str
    score: float


class OCRTargeter:
    def __init__(self, language: str = "eng", psm: int = 6, oem: int = 3):
        self.language = language
        self.psm = psm
        self.oem = oem
        self._last_hash: Optional[str] = None
        self._last_regions: List[Region] = []

    def _hash_img(self, img: Image.Image) -> str:
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return hashlib.sha1(buf.getvalue()).hexdigest()

    def _preprocess(self, img: Image.Image) -> Image.Image:
        g = ImageOps.grayscale(img)
        g = g.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
        return g

    def extract(self, img: Image.Image) -> List[Region]:
        if pytesseract is None:
            raise RuntimeError("pytesseract not installed. Install 'pytesseract' and Tesseract binary")
        h = self._hash_img(img)
        if h == self._last_hash:
            return self._last_regions

        proc = self._preprocess(img)
        custom = f"--psm {self.psm} --oem {self.oem}"
        data = pytesseract.image_to_data(proc, lang=self.language, config=custom, output_type=pytesseract.Output.DICT)  # type: ignore[attr-defined]
        regs: List[Region] = []
        n = len(data.get("text", []))
        for i in range(n):
            txt = (data["text"][i] or "").strip()
            if not txt:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            regs.append(Region(x=x, y=y, w=w, h=h, text=txt, score=1.0))
        self._last_hash = h
        self._last_regions = regs
        return regs

    @staticmethod
    def _score(query: str, candidate: str) -> float:
        q = query.strip().lower()
        c = (candidate or "").strip().lower()
        if not q or not c:
            return 0.0
        if q == c:
            return 1.0
        if q in c:
            return min(0.95, (len(q) / (len(c) + 1e-5)))
        import difflib
        return difflib.SequenceMatcher(None, q, c).ratio()

    def find_text(self, img: Image.Image, query: str, min_score: float = 0.7, region: Optional[Tuple[int,int,int,int]] = None) -> List[Region]:
        crop = img
        offset_x = offset_y = 0
        if region:
            left, top, width, height = region
            crop = img.crop((left, top, left + width, top + height))
            offset_x, offset_y = left, top

        regs = self.extract(crop)
        scored: List[Region] = []
        for r in regs:
            s = self._score(query, r.text)
            if s >= min_score:
                scored.append(Region(x=r.x + offset_x, y=r.y + offset_y, w=r.w, h=r.h, text=r.text, score=s))
        scored.sort(key=lambda r: (r.score, r.w * r.h), reverse=True)
        return scored
