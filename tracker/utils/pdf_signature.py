from __future__ import annotations

import math
from io import BytesIO
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

from PIL import Image, ImageOps, ImageFilter, ImageEnhance
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


class SignatureEmbedError(Exception):
    """Raised when a signature cannot be embedded into the provided PDF."""


def _scale_dimensions(
    page_width: float,
    page_height: float,
    image_width: int,
    image_height: int,
    max_width_ratio: float = 0.35,
    max_height_ratio: float = 0.12,
) -> Tuple[float, float]:
    """Compute scaled signature dimensions preserving aspect ratio within limits."""
    if image_width <= 0 or image_height <= 0:
        raise SignatureEmbedError("Signature image has invalid dimensions.")

    target_width = page_width * max_width_ratio
    target_height = page_height * max_height_ratio

    width_ratio = target_width / float(image_width)
    height_ratio = target_height / float(image_height)
    scale = min(width_ratio, height_ratio)

    scaled_width = float(image_width) * scale
    scaled_height = float(image_height) * scale

    return scaled_width, scaled_height


def _calculate_signature_position(
    page_width: float, 
    page_height: float,
    signature_width: float,
    signature_height: float,
    position_type: str = "customer"
) -> Tuple[float, float]:
    """
    Calculate position for signature based on the form layout.
    """
    if position_type == "customer":
        x = page_width * 0.60
        y = page_height * 0.18
    elif position_type == "service_advisor":
        x = page_width * 0.60
        y = page_height * 0.12
    else:
        x = page_width * 0.60
        y = page_height * 0.06
    
    return x, y


def _convert_to_blue_ink(signature_image: Image.Image) -> Image.Image:
    """Convert signature to look like real blue ink pen writing."""
    # Convert to RGBA if not already
    if signature_image.mode != 'RGBA':
        signature_image = signature_image.convert('RGBA')
    
    # Create a new image for blue ink effect
    width, height = signature_image.size
    blue_ink_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    
    # Get pixel data
    sig_pixels = signature_image.load()
    blue_pixels = blue_ink_image.load()
    
    # Blue ink color variations (like real pen ink)
    blue_colors = [
        (0, 50, 200, 255),    # Dark blue
        (30, 80, 220, 230),   # Medium blue
        (60, 120, 255, 200),  # Light blue
    ]
    
    for x in range(width):
        for y in range(height):
            r, g, b, a = sig_pixels[x, y]
            
            # If this is part of the signature (has some opacity)
            if a > 30:
                # Calculate intensity to create natural ink variation
                intensity = (r + g + b) / 3
                
                # Choose blue color based on intensity
                if intensity < 85:
                    blue_color = blue_colors[0]  # Dark blue for strong lines
                elif intensity < 170:
                    blue_color = blue_colors[1]  # Medium blue
                else:
                    blue_color = blue_colors[2]  # Light blue for faint areas
                
                # Preserve the alpha but use blue color
                new_alpha = min(255, int(a * 1.2))  # Slightly enhance visibility
                blue_pixels[x, y] = (blue_color[0], blue_color[1], blue_color[2], new_alpha)
    
    return blue_ink_image


def _enhance_signature_for_pen_effect(signature_image: Image.Image) -> Image.Image:
    """Enhance signature to make it look more like pen writing."""
    # Increase contrast to make signature more defined
    if signature_image.mode == 'RGBA':
        # Separate alpha channel
        r, g, b, a = signature_image.split()
        
        # Enhance the RGB channels
        rgb_image = Image.merge('RGB', (r, g, b))
        enhancer = ImageEnhance.Contrast(rgb_image)
        enhanced_rgb = enhancer.enhance(2.0)  # Increase contrast
        
        # Convert back to RGBA
        r_enhanced, g_enhanced, b_enhanced = enhanced_rgb.split()
        signature_image = Image.merge('RGBA', (r_enhanced, g_enhanced, b_enhanced, a))
    
    # Apply slight sharpening to make lines more defined
    signature_image = signature_image.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
    
    return signature_image


def embed_signature_in_pdf(
    pdf_bytes: bytes,
    signature_bytes: bytes,
    *,
    position_type: str = "customer",
    margin: float = 36.0,
    max_width_ratio: float = 0.35,
    max_height_ratio: float = 0.12,
    preset: Optional[str] = None,
) -> bytes:
    """Return a PDF with blue ink signature embedded."""
    if not pdf_bytes:
        raise SignatureEmbedError("No PDF content provided.")
    if not signature_bytes:
        raise SignatureEmbedError("No signature content provided.")

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception as exc:
        raise SignatureEmbedError("Could not read the provided PDF document.") from exc

    if len(reader.pages) == 0:
        raise SignatureEmbedError("The PDF has no pages to sign.")

    try:
        signature_image = Image.open(BytesIO(signature_bytes))
        signature_image = signature_image.convert("RGBA")
        
        # Enhance signature for better pen effect
        signature_image = _enhance_signature_for_pen_effect(signature_image)
        
        # Convert to blue ink
        signature_image = _convert_to_blue_ink(signature_image)
        
    except Exception as exc:
        raise SignatureEmbedError("Could not decode the signature image.") from exc

    last_page = reader.pages[-1]
    page_width = float(last_page.mediabox.width)
    page_height = float(last_page.mediabox.height)

    # Scale signature
    scaled_width, scaled_height = _scale_dimensions(
        page_width,
        page_height,
        signature_image.width,
        signature_image.height,
        max_width_ratio=max_width_ratio,
        max_height_ratio=max_height_ratio,
    )

    # Determine effective position type (supports legacy 'preset' argument like 'job_card')
    eff_position_type = (position_type or "customer").strip().lower()
    if preset:
        p = (str(preset) or "").strip().lower()
        if p in {"job_card", "jobcard", "job card"}:
            # Place slightly lower for job cards
            eff_position_type = "service_advisor"
    # Calculate position
    x_position, y_position = _calculate_signature_position(
        page_width, page_height, scaled_width, scaled_height, eff_position_type
    )

    overlay_stream = BytesIO()
    signature_buffer = BytesIO()
    signature_image.save(signature_buffer, format="PNG")
    signature_buffer.seek(0)

    overlay_canvas = canvas.Canvas(overlay_stream, pagesize=(page_width, page_height))
    
    # Draw the blue ink signature
    overlay_canvas.drawImage(
        ImageReader(signature_buffer),
        x_position,
        y_position,
        width=scaled_width,
        height=scaled_height,
        mask='auto',
    )
    
    overlay_canvas.save()
    overlay_stream.seek(0)

    overlay_reader = PdfReader(overlay_stream)
    overlay_page = overlay_reader.pages[0]

    writer = PdfWriter()
    total_pages = len(reader.pages)
    for index, page in enumerate(reader.pages):
        if index == total_pages - 1:
            page.merge_page(overlay_page)
        writer.add_page(page)

    output_stream = BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)
    return output_stream.read()


def embed_signature_in_image(
    image_bytes: bytes,
    signature_bytes: bytes,
    *,
    position_type: str = "customer",
    margin: int = 12,
    max_width_ratio: float = 0.35,
    max_height_ratio: float = 0.12,
    output_format: Optional[str] = None,
    preset: Optional[str] = None,
) -> bytes:
    """Overlay blue ink signature onto the image."""
    if not image_bytes:
        raise SignatureEmbedError("No image content provided.")
    if not signature_bytes:
        raise SignatureEmbedError("No signature content provided.")

    try:
        base_img = Image.open(BytesIO(image_bytes))
    except Exception as exc:
        raise SignatureEmbedError("Could not read the provided image document.") from exc

    try:
        sig_img = Image.open(BytesIO(signature_bytes)).convert("RGBA")
        
        # Enhance signature for better pen effect
        sig_img = _enhance_signature_for_pen_effect(sig_img)
        
        # Convert to blue ink
        sig_img = _convert_to_blue_ink(sig_img)
        
    except Exception as exc:
        raise SignatureEmbedError("Could not decode the signature image.") from exc

    base_mode = base_img.mode
    base_format = (base_img.format or "").upper() or None
    base_img = base_img.convert("RGBA")

    page_w, page_h = float(base_img.width), float(base_img.height)
    
    # Scale signature
    scaled_w, scaled_h = _scale_dimensions(
        page_w, page_h, sig_img.width, sig_img.height,
        max_width_ratio=max_width_ratio, max_height_ratio=max_height_ratio,
    )

    # Resize signature
    sig_resized = sig_img.resize((int(max(1, scaled_w)), int(max(1, scaled_h))), Image.LANCZOS)

    # Determine effective position type (supports legacy 'preset' like 'job_card')
    eff_position_type = (position_type or "customer").strip().lower()
    if preset:
        p = (str(preset) or "").strip().lower()
        if p in {"job_card", "jobcard", "job card"}:
            eff_position_type = "service_advisor"

    # Calculate position
    if eff_position_type == "customer":
        x = page_w * 0.60
        y = page_h * 0.18
    elif eff_position_type == "service_advisor":
        x = page_w * 0.60
        y = page_h * 0.12
    else:
        x = page_w * 0.60
        y = page_h * 0.06

    composed = Image.new("RGBA", base_img.size)
    composed.paste(base_img, (0, 0))
    composed.paste(sig_resized, (int(x), int(y)), mask=sig_resized)

    # Convert back if original was not RGBA
    if base_mode != "RGBA":
        if base_mode in ("RGB", "L"):
            composed = composed.convert(base_mode)
        else:
            composed = composed.convert("RGB")
            base_format = base_format or "PNG"

    out = BytesIO()
    fmt = (output_format or base_format or "PNG").upper()
    if fmt == "JPG":
        fmt = "JPEG"
    composed.save(out, format=fmt)
    out.seek(0)
    return out.read()


def build_signed_filename(original_name: str, suffix: str = "signed") -> str:
    """Return a descriptive filename for the signed PDF."""
    base = Path(original_name or "document").stem or "document"
    return f"{base}-{suffix}.pdf"


def build_signed_name(original_name: str, suffix: str = "signed", preferred_ext: Optional[str] = None) -> str:
    """Return a descriptive filename preserving extension when possible."""
    p = Path(original_name or "document")
    base = p.stem or "document"
    if preferred_ext:
        ext = preferred_ext if preferred_ext.startswith(".") else f".{preferred_ext}"
    else:
        ext = p.suffix or ".bin"
    return f"{base}-{suffix}{ext}"
