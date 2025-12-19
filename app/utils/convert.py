from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConvertResult:
    pdf_path: Path
    png_paths: list[Path]


class ConvertError(RuntimeError):
    pass


def pptx_to_pdf(*, pptx_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "soffice",
        "--headless",
        "--norestore",
        "--nolockcheck",
        "--convert-to",
        "pdf",
        "--outdir",
        str(out_dir),
        str(pptx_path),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise ConvertError(f"LibreOffice conversion failed: {p.stderr or p.stdout}")

    # LibreOffice outputs <basename>.pdf
    pdf_path = out_dir / (pptx_path.stem + ".pdf")
    if not pdf_path.exists():
        raise ConvertError(f"PDF not found after conversion: {pdf_path}")
    return pdf_path


def pdf_to_pngs(*, pdf_path: Path, out_dir: Path, prefix: str = "slide") -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_prefix = out_dir / prefix
    cmd = [
        "pdftoppm",
        "-png",
        str(pdf_path),
        str(out_prefix),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise ConvertError(f"pdftoppm failed: {p.stderr or p.stdout}")

    # pdftoppm emits files like prefix-1.png, prefix-2.png ...
    created = sorted(out_dir.glob(f"{prefix}-*.png"))
    if not created:
        raise ConvertError("No PNGs produced by pdftoppm")

    # Normalize names: slide-001.png etc
    normalized: list[Path] = []
    for src in created:
        m = re.search(r"-(\\d+)\\.png$", src.name)
        idx = int(m.group(1)) if m else len(normalized) + 1
        dst = out_dir / f"slide-{idx:03d}.png"
        if dst.exists():
            dst.unlink()
        src.rename(dst)
        normalized.append(dst)
    return normalized


def pptx_to_pngs(*, pptx_path: Path, out_dir: Path) -> ConvertResult:
    pdf_dir = out_dir
    pdf_path = pptx_to_pdf(pptx_path=pptx_path, out_dir=pdf_dir)
    png_paths = pdf_to_pngs(pdf_path=pdf_path, out_dir=out_dir, prefix="page")
    return ConvertResult(pdf_path=pdf_path, png_paths=png_paths)


