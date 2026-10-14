"""
Video Synthesizer Service for FOTOSTREAM.
Synthesizes up to 49 images into 30fps MP4 video supporting:
- Multi-resolution: 720p (minimum), 1080p (standard default), 1440p, 1920p (maximum)
- Hybrid Resolution Zoom: Seamless crossfade to 100% original high-resolution image during zoom-in
- Dynamic NxM grid layout (M=N or N=M±1)
- Zoom-in -> Hold inspection (High-Res) -> Zoom-out sliding transition sequence
- BGM audio mixing (loop + fade out)
- FFmpeg streaming encoding via rawvideo pipe
- Progress reporting callback
"""

import math
import subprocess
from pathlib import Path
from typing import List, Optional, Callable, Dict, Tuple
from PIL import Image, ImageOps, ImageDraw, ImageFilter
from app.core.config import settings
from app.services.grid_calculator import compute_grid_layout, CellBox
from app.services.audio_mixer import build_audio_ffmpeg_args

FPS = 30

RESOLUTION_PROFILES: Dict[str, Dict[str, int | str]] = {
    "720p": {"width": 1280, "height": 720, "maxrate": "2500k", "bufsize": "5000k"},
    "1080p": {"width": 1920, "height": 1080, "maxrate": "4500k", "bufsize": "9000k"}, # Standard Default
    "1440p": {"width": 2560, "height": 1440, "maxrate": "7000k", "bufsize": "14000k"},
    "1920p": {"width": 3414, "height": 1920, "maxrate": "10000k", "bufsize": "20000k"} # Maximum Ultra-HD
}

def get_resolution_spec(resolution: str) -> Tuple[int, int, str, str]:
    res_key = resolution.lower().strip() if resolution else "1080p"
    profile = RESOLUTION_PROFILES.get(res_key, RESOLUTION_PROFILES["1080p"])
    return int(profile["width"]), int(profile["height"]), str(profile["maxrate"]), str(profile["bufsize"])

def create_background_canvas(width: int, height: int) -> Image.Image:
    """Create a dark, modern elegant gradient background."""
    bg = Image.new("RGB", (width, height), (18, 20, 26))
    draw = ImageDraw.Draw(bg)
    for y in range(height):
        ratio = y / height
        r = int(18 + 10 * ratio)
        g = int(20 + 12 * ratio)
        b = int(26 + 18 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return bg

def fit_image_contain(
    img: Image.Image,
    target_w: int,
    target_h: int,
    bg_color: Tuple[int, int, int] = (0, 0, 0)
) -> Image.Image:
    """
    Fits image completely inside (target_w, target_h) preserving original aspect ratio.
    The longer dimension of the image is scaled to fit target box bounds so that
    100% of the picture is visible without any cropping:
    - For portrait photos (height > width): scales based on height to show full height.
    - For landscape photos (width > height): scales based on width to show full width.
    Any empty letterbox/pillarbox space is filled with solid black (0, 0, 0).
    """
    im_w, im_h = img.size
    if im_w <= 0 or im_h <= 0:
        return Image.new("RGB", (target_w, target_h), bg_color)

    scale = min(target_w / im_w, target_h / im_h)
    new_w = max(1, int(round(im_w * scale)))
    new_h = max(1, int(round(im_h * scale)))

    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (target_w, target_h), bg_color)
    offset_x = (target_w - new_w) // 2
    offset_y = (target_h - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return canvas

def synthesize_video(
    image_paths: List[Path],
    bgm_path: Optional[Path],
    output_mp4_path: Path,
    thumbnail_path: Optional[Path] = None,
    on_progress: Optional[Callable[[int], None]] = None,
    resolution: str = "1080p"
) -> float:
    """
    Renders video from images and optional BGM at the specified resolution (default 1080p).
    Implements Bento Grid layout and Aspect-Ratio Contain fitting (zero crop, black padding)
    with Hybrid Resolution Zoom to preserve full original high-definition details.
    Returns the total video duration in seconds.
    """
    assert len(image_paths) >= 1, "At least 1 image is required"
    if len(image_paths) > settings.MAX_IMAGES_COUNT:
        image_paths = image_paths[:settings.MAX_IMAGES_COUNT]

    canvas_w, canvas_h, maxrate, bufsize = get_resolution_spec(resolution)
    image_count = len(image_paths)

    # 1. Preload images and extract aspect ratios to compute optimal Bento Grid
    loaded_images: List[Image.Image] = []
    aspect_ratios: List[float] = []

    for img_path in image_paths:
        try:
            with Image.open(img_path) as im:
                im = ImageOps.exif_transpose(im)
                rgb_im = im.convert("RGB")
                w, h = rgb_im.size
                aspect_ratios.append(w / max(1, h))
                loaded_images.append(rgb_im)
        except Exception:
            fallback = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
            aspect_ratios.append(16.0 / 9.0)
            loaded_images.append(fallback)

    # Compute optimal grid layout (dispatches to Bento Grid if mixed aspect ratios exist)
    rows, cols, cells = compute_grid_layout(
        image_count, canvas_w, canvas_h, aspect_ratios=aspect_ratios
    )

    # Preload dual-layer images:
    # Layer A: Base grid canvas (contains thumbnails in cell positions fitted via contain)
    # Layer B: High-res normalized original images (fitted to full canvas with black letterbox/pillarbox)
    base_canvas = create_background_canvas(canvas_w, canvas_h)
    hi_res_images: List[Image.Image] = []

    for idx in range(image_count):
        rgb_im = loaded_images[idx]
        cell = cells[idx]

        # Layer A: Thumbnail in matrix cell (contain, zero cropping, black background)
        thumb = fit_image_contain(rgb_im, cell.width, cell.height, bg_color=(0, 0, 0))
        base_canvas.paste(thumb, (cell.x1, cell.y1))

        # Layer B: High-res image fitted to full canvas (contain, empty area filled with black)
        hi_res = fit_image_contain(rgb_im, canvas_w, canvas_h, bg_color=(0, 0, 0))
        hi_res_images.append(hi_res)

    # Save thumbnail (the full matrix view)
    if thumbnail_path:
        base_canvas.save(thumbnail_path, format="JPEG", quality=85)

    # 2. Timing definition
    intro_frames = 30
    zoom_in_frames = 15
    hold_frames = 45
    zoom_out_frames = 15
    outro_frames = 30

    frames_per_image = zoom_in_frames + hold_frames + zoom_out_frames
    total_frames = intro_frames + (image_count * frames_per_image) + outro_frames
    total_duration = total_frames / FPS

    # 3. Setup FFmpeg encoding command with pipe
    audio_inputs, audio_filters = build_audio_ffmpeg_args(bgm_path, total_duration)

    cmd = [
        str(settings.abs_ffmpeg_path),
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{canvas_w}x{canvas_h}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-"  # Video stdin pipe
    ] + audio_inputs + [
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-maxrate", maxrate,
        "-bufsize", bufsize,
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart"
    ] + audio_filters + [
        "-t", f"{total_duration:.2f}",
        str(output_mp4_path)
    ]

    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        creationflags=creationflags
    )

    base_raw = base_canvas.tobytes()
    current_frame = 0

    def emit_frame(img: Image.Image):
        nonlocal current_frame
        proc.stdin.write(img.tobytes())
        current_frame += 1
        if on_progress and current_frame % 15 == 0:
            pct = min(99, int((current_frame / total_frames) * 100))
            on_progress(pct)

    def emit_raw_bytes(raw_bytes: bytes):
        nonlocal current_frame
        proc.stdin.write(raw_bytes)
        current_frame += 1
        if on_progress and current_frame % 15 == 0:
            pct = min(99, int((current_frame / total_frames) * 100))
            on_progress(pct)

    try:
        # A. Intro (Base matrix view)
        for _ in range(intro_frames):
            emit_raw_bytes(base_raw)

        # B. Image Loop (Hybrid Zoom In -> High-Res Hold -> Hybrid Zoom Out)
        for idx in range(image_count):
            cell = cells[idx]
            cell_cx = cell.center_x
            cell_cy = cell.center_y
            hi_res_img = hi_res_images[idx]
            hi_res_raw = hi_res_img.tobytes()
            im_w, im_h = loaded_images[idx].size
            scale_in_cell = min(cell.width / max(1, im_w), cell.height / max(1, im_h))
            scale_in_canvas = min(canvas_w / max(1, im_w), canvas_h / max(1, im_h))
            target_scale = max(1.0, scale_in_canvas / max(1e-6, scale_in_cell))

            # --- Zoom In (with smooth crossfade to High-Res original from midway) ---
            for f in range(zoom_in_frames):
                t = f / zoom_in_frames
                alpha = 0.5 * (1.0 - math.cos(math.pi * t))

                scale = 1.0 + (target_scale - 1.0) * alpha
                cx = (canvas_w / 2.0) + (cell_cx - (canvas_w / 2.0)) * alpha
                cy = (canvas_h / 2.0) + (cell_cy - (canvas_h / 2.0)) * alpha

                crop_w = canvas_w / scale
                crop_h = canvas_h / scale
                x1 = max(0, min(canvas_w - crop_w, cx - (crop_w / 2.0)))
                y1 = max(0, min(canvas_h - crop_h, cy - (crop_h / 2.0)))
                x2 = x1 + crop_w
                y2 = y1 + crop_h

                cropped = base_canvas.crop((int(x1), int(y1), int(x2), int(y2)))
                matrix_frame = cropped.resize((canvas_w, canvas_h), Image.Resampling.BILINEAR)

                # Cross-fade strategy:
                # t < 0.35: 100% matrix crop view
                # 0.35 <= t <= 0.70: smooth cosine blend into high-res original
                # t > 0.70: 100% full original high-res view (crystal clear!)
                if t < 0.35:
                    emit_frame(matrix_frame)
                elif t > 0.70:
                    emit_frame(hi_res_img)
                else:
                    blend_t = (t - 0.35) / 0.35
                    weight_hi_res = 0.5 * (1.0 - math.cos(math.pi * blend_t))
                    blended = Image.blend(matrix_frame, hi_res_img, weight_hi_res)
                    emit_frame(blended)

            # --- Hold (100% Original High-Resolution Inspection) ---
            # Guarantees maximum clarity and detail as requested
            for _ in range(hold_frames):
                emit_raw_bytes(hi_res_raw)

            # --- Zoom Out (Seamless crossfade back to matrix canvas) ---
            for f in range(zoom_out_frames):
                t = f / zoom_out_frames
                alpha = 0.5 * (1.0 + math.cos(math.pi * t))

                scale = 1.0 + (target_scale - 1.0) * alpha
                cx = (canvas_w / 2.0) + (cell_cx - (canvas_w / 2.0)) * alpha
                cy = (canvas_h / 2.0) + (cell_cy - (canvas_h / 2.0)) * alpha

                crop_w = canvas_w / scale
                crop_h = canvas_h / scale
                x1 = max(0, min(canvas_w - crop_w, cx - (crop_w / 2.0)))
                y1 = max(0, min(canvas_h - crop_h, cy - (crop_h / 2.0)))
                x2 = x1 + crop_w
                y2 = y1 + crop_h

                cropped = base_canvas.crop((int(x1), int(y1), int(x2), int(y2)))
                matrix_frame = cropped.resize((canvas_w, canvas_h), Image.Resampling.BILINEAR)

                # Reverse cross-fade:
                # t < 0.30: 100% high-res view
                # 0.30 <= t <= 0.65: smooth blend into matrix view
                # t > 0.65: 100% matrix view
                if t < 0.30:
                    emit_frame(hi_res_img)
                elif t > 0.65:
                    emit_frame(matrix_frame)
                else:
                    blend_t = (t - 0.30) / 0.35
                    weight_hi_res = 0.5 * (1.0 + math.cos(math.pi * blend_t))
                    blended = Image.blend(matrix_frame, hi_res_img, weight_hi_res)
                    emit_frame(blended)

        # C. Outro (Matrix view with fade to black)
        for f in range(outro_frames):
            if f < (outro_frames // 2):
                emit_raw_bytes(base_raw)
            else:
                fade_alpha = 1.0 - ((f - outro_frames // 2) / (outro_frames // 2))
                faded = Image.blend(Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0)), base_canvas, fade_alpha)
                emit_frame(faded)

        proc.stdin.close()
        stderr_output = proc.stderr.read()
        proc.wait()

        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg encoding failed with code {proc.returncode}: {stderr_output.decode('utf-8', errors='ignore')}")

        if on_progress:
            on_progress(100)

        return total_duration

    except Exception as e:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
        proc.kill()
        raise e
