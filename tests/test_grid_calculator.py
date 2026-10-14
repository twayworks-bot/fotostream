import pytest
from PIL import Image
from app.services.grid_calculator import calculate_best_grid, compute_grid_layout, compute_bento_layout
from app.services.video_synthesizer import fit_image_contain

def test_grid_calculator_conditions_1_to_49():
    """Verify that all image counts 1..49 satisfy M==N or N==M±1 and N*M >= K."""
    for k in range(1, 50):
        rows, cols = calculate_best_grid(k)
        assert rows * cols >= k, f"Failed capacity for K={k}: {rows}x{cols} = {rows*cols} < {k}"
        diff = abs(rows - cols)
        assert diff in (0, 1), f"Failed aspect condition for K={k}: rows={rows}, cols={cols}, diff={diff}"

def test_grid_layout_coordinates_multi_resolution():
    """Verify coordinates fit inside 720p, 1080p, and 1920p canvases without overflow."""
    resolutions = [
        (1280, 720),   # 720p
        (1920, 1080),  # 1080p Standard
        (2560, 1440),  # 1440p 2K
        (3414, 1920)   # 1920p Max
    ]
    for w, h in resolutions:
        for k in [1, 4, 9, 16, 25, 49]:
            rows, cols, cells = compute_grid_layout(k, w, h)
            assert len(cells) == k
            for cell in cells:
                assert 0 <= cell.x1 < cell.x2 <= w
                assert 0 <= cell.y1 < cell.y2 <= h
                assert cell.width > 0
                assert cell.height > 0

def test_bento_layout_with_mixed_orientations():
    """Verify Bento Grid properly handles mixed portrait and landscape photos."""
    # 5 photos: 3 portrait (9:16 approx 0.56) and 2 landscape (16:9 approx 1.77)
    aspect_ratios = [0.56, 1.77, 0.56, 1.77, 0.56]
    w, h = 1920, 1080
    rows, cols, cells = compute_bento_layout(len(aspect_ratios), w, h, aspect_ratios)

    assert len(cells) == len(aspect_ratios)
    for cell in cells:
        assert 0 <= cell.x1 < cell.x2 <= w
        assert 0 <= cell.y1 < cell.y2 <= h
        assert cell.width > 0
        assert cell.height > 0

    # Verify no two cells overlap
    for i in range(len(cells)):
        for j in range(i + 1, len(cells)):
            c1, c2 = cells[i], cells[j]
            # Two boxes overlap if they intersect horizontally and vertically
            overlap = not (c1.x2 <= c2.x1 or c2.x2 <= c1.x1 or c1.y2 <= c2.y1 or c2.y2 <= c1.y1)
            assert not overlap, f"Cells {i} and {j} overlap: {c1.to_dict()} vs {c2.to_dict()}"

def test_fit_image_contain_portrait_and_landscape():
    """
    Verify that fit_image_contain scales by height for portrait and width for landscape,
    leaving no cropped content and padding empty spaces with pure black (0, 0, 0).
    """
    target_w, target_h = 400, 300

    # 1. Portrait image (w=100, h=200 -> height > width)
    portrait_im = Image.new("RGB", (100, 200), color=(255, 0, 0))
    fitted_portrait = fit_image_contain(portrait_im, target_w, target_h, bg_color=(0, 0, 0))
    assert fitted_portrait.size == (target_w, target_h)
    # Check that top/bottom borders have image pixels while leftmost pixel is black
    assert fitted_portrait.getpixel((0, 150)) == (0, 0, 0)  # Left pillarbox is black
    assert fitted_portrait.getpixel((target_w - 1, 150)) == (0, 0, 0)  # Right pillarbox is black
    assert fitted_portrait.getpixel((target_w // 2, 150)) == (255, 0, 0)  # Center has image

    # 2. Landscape image (w=200, h=100 -> width > height)
    landscape_im = Image.new("RGB", (200, 100), color=(0, 255, 0))
    fitted_landscape = fit_image_contain(landscape_im, target_w, target_h, bg_color=(0, 0, 0))
    assert fitted_landscape.size == (target_w, target_h)
    assert fitted_landscape.getpixel((200, 0)) == (0, 0, 0)  # Top letterbox is black
    assert fitted_landscape.getpixel((200, target_h - 1)) == (0, 0, 0)  # Bottom letterbox is black
    assert fitted_landscape.getpixel((200, target_h // 2)) == (0, 255, 0)  # Center has image
