"""
Grid Calculator Service for FOTOSTREAM.
Calculates the optimal NxM matrix layout satisfying M=N or N=M±1
for 1 to 49 images, and computes bounding coordinates for 720p canvas (1280x720).
"""

from typing import Tuple, List, Dict

class CellBox:
    def __init__(self, index: int, row: int, col: int, x1: int, y1: int, x2: int, y2: int):
        self.index = index
        self.row = row
        self.col = col
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.width = x2 - x1
        self.height = y2 - y1
        self.center_x = (x1 + x2) // 2
        self.center_y = (y1 + y2) // 2

    def to_dict(self) -> Dict:
        return {
            "index": self.index,
            "row": self.row,
            "col": self.col,
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "width": self.width,
            "height": self.height,
            "center_x": self.center_x,
            "center_y": self.center_y
        }

def calculate_best_grid(image_count: int) -> Tuple[int, int]:
    """
    Calculate optimal (rows N, cols M) for given image count K (1 <= K <= 49).
    Constraint: M == N or N == M + 1 or N == M - 1.
    Criteria:
    1. Capacity (N * M) >= image_count
    2. Minimize empty cells: (N * M) - image_count
    3. Prefer aspect ratio close to 16:9 (1.777), preferring M >= N for widescreen.
    """
    if image_count < 1:
        return 1, 1
    if image_count > 49:
        image_count = 49

    candidates = []
    # Search reasonable grid ranges up to 7x7
    for n in range(1, 8):
        for m in (n, n + 1, n - 1):
            if m < 1:
                continue
            capacity = n * m
            if capacity >= image_count:
                waste = capacity - image_count
                aspect = m / n
                # Distance from 16:9 widescreen ratio
                aspect_diff = abs(aspect - (16.0 / 9.0))
                # Small penalty if M < N because screens are landscape
                orientation_penalty = 0.5 if m < n else 0.0
                score = (waste * 2.0) + aspect_diff + orientation_penalty
                candidates.append((score, waste, n, m))

    candidates.sort(key=lambda item: item[0])
    best = candidates[0]
    return best[2], best[3]  # rows, cols

def compute_grid_layout(
    image_count: int,
    canvas_width: int = 1920,
    canvas_height: int = 1080,
    margin_x: int = None,
    margin_y: int = None,
    gap: int = None
) -> Tuple[int, int, List[CellBox]]:
    """
    Calculates the cell boxes for each image in the canvas.
    Scales margins and gaps proportionally with canvas resolution.
    """
    rows, cols = calculate_best_grid(image_count)

    scale = canvas_height / 720.0
    if margin_x is None:
        margin_x = int(24 * scale)
    if margin_y is None:
        margin_y = int(24 * scale)
    if gap is None:
        gap = int(12 * scale)


    usable_width = canvas_width - (2 * margin_x) - ((cols - 1) * gap)
    usable_height = canvas_height - (2 * margin_y) - ((rows - 1) * gap)

    cell_w = max(1, usable_width // cols)
    cell_h = max(1, usable_height // rows)

    # Re-center grid if integer division caused slight remainder
    actual_grid_w = (cols * cell_w) + ((cols - 1) * gap)
    actual_grid_h = (rows * cell_h) + ((rows - 1) * gap)
    start_x = (canvas_width - actual_grid_w) // 2
    start_y = (canvas_height - actual_grid_h) // 2

    cells: List[CellBox] = []
    idx = 0
    for r in range(rows):
        for c in range(cols):
            if idx >= image_count:
                break
            x1 = start_x + (c * (cell_w + gap))
            y1 = start_y + (r * (cell_h + gap))
            x2 = x1 + cell_w
            y2 = y1 + cell_h
            cells.append(CellBox(idx, r, c, x1, y1, x2, y2))
            idx += 1

    return rows, cols, cells
