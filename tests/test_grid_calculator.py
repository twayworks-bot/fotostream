import pytest
from app.services.grid_calculator import calculate_best_grid, compute_grid_layout

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
