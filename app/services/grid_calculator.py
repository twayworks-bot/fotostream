"""
Grid Calculator Service for FOTOSTREAM.
Calculates optimal NxM matrix layouts and dynamic Bento Grid layouts
for 1 to 49 images, minimizing black/empty areas for mixed aspect ratio photos.
"""

from typing import Tuple, List, Dict, Optional

class CellBox:
    def __init__(self, index: int, row: int, col: int, x1: int, y1: int, x2: int, y2: int):
        self.index = index
        self.row = row
        self.col = col
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.width = max(1, x2 - x1)
        self.height = max(1, y2 - y1)
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

def compute_bento_layout(
    image_count: int,
    canvas_width: int = 1920,
    canvas_height: int = 1080,
    aspect_ratios: Optional[List[float]] = None,
    margin_x: Optional[int] = None,
    margin_y: Optional[int] = None,
    gap: Optional[int] = None
) -> Tuple[int, int, List[CellBox]]:
    """
    Computes an optimized Bento Grid layout for photos with mixed aspect ratios.
    Dynamically scales row heights and column widths so that portrait (tall) and
    landscape (wide) photos fit their allocated slots with minimal black/empty space.
    """
    if image_count < 1:
        return 1, 1, []
    if image_count > 49:
        image_count = 49

    scale = canvas_height / 720.0
    if margin_x is None:
        margin_x = int(24 * scale)
    if margin_y is None:
        margin_y = int(24 * scale)
    if gap is None:
        gap = int(12 * scale)

    if aspect_ratios is None or len(aspect_ratios) < image_count:
        aspect_ratios = [16.0 / 9.0] * image_count
    else:
        aspect_ratios = [max(0.2, min(5.0, float(ar))) for ar in aspect_ratios[:image_count]]

    # 1 Image fills usable canvas
    if image_count == 1:
        cell = CellBox(0, 0, 0, margin_x, margin_y, canvas_width - margin_x, canvas_height - margin_y)
        return 1, 1, [cell]

    usable_w = canvas_width - (2 * margin_x)
    usable_h = canvas_height - (2 * margin_y)

    rows, _ = calculate_best_grid(image_count)
    R = max(1, min(rows, image_count))

    if R == 1:
        avail_w = max(1, usable_w - ((image_count - 1) * gap))
        sum_ar = sum(aspect_ratios)
        cells = []
        cur_x = margin_x
        for i, ar in enumerate(aspect_ratios):
            if i == image_count - 1:
                cw = (margin_x + usable_w) - cur_x
            else:
                cw = max(1, int(avail_w * (ar / max(0.01, sum_ar))))
            cells.append(CellBox(i, 0, i, cur_x, margin_y, cur_x + cw, margin_y + usable_h))
            cur_x += cw + gap
        return 1, image_count, cells

    # Pair each image with original index: (orig_index, aspect_ratio)
    items = [(i, aspect_ratios[i]) for i in range(image_count)]
    # Sort from smallest AR (tallest portrait) to largest AR (widest landscape)
    sorted_items = sorted(items, key=lambda x: x[1])

    # Generate candidate partitions of image_count into R non-empty parts
    def get_partitions(n, k, min_val=1):
        if k == 1:
            yield [n]
            return
        for i in range(min_val, n - k + 2):
            for rest in get_partitions(n - i, k - 1, 1):
                yield [i] + rest

    all_partitions = []
    if image_count <= 12:
        all_partitions = list(get_partitions(image_count, R))
    else:
        # Constrain partition search around balanced counts for performance
        base_m = image_count / R
        for p in get_partitions(image_count, R):
            if all(abs(cnt - base_m) <= 2.5 for cnt in p):
                all_partitions.append(p)
        if not all_partitions:
            base_int = image_count // R
            rem = image_count % R
            all_partitions = [[base_int + (1 if r < rem else 0) for r in range(R)]]

    best_partition = None
    best_cost = float('inf')

    for p in all_partitions:
        sliced_rows = []
        start = 0
        for cnt in p:
            sliced_rows.append(sorted_items[start : start + cnt])
            start += cnt

        # Evaluate wasted area for this partition
        row_ars = [sum(it[1] for it in r_items) for r_items in sliced_rows]
        inv_ars = [1.0 / max(0.01, ar) for ar in row_ars]
        sum_inv = sum(inv_ars)
        total_h_avail = usable_h - ((R - 1) * gap)
        row_h_list = [int(total_h_avail * (inv / max(0.01, sum_inv))) for inv in inv_ars]

        cost = 0.0
        for r_items, rh in zip(sliced_rows, row_h_list):
            m = len(r_items)
            total_w_avail = usable_w - ((m - 1) * gap)
            ar_sum = sum(it[1] for it in r_items)
            for _, ar in r_items:
                cw = max(1, int(total_w_avail * (ar / max(0.01, ar_sum))))
                cell_area = cw * max(1, rh)
                cell_ar = cw / max(1, rh)
                ratio = min(ar / cell_ar, cell_ar / ar) if cell_ar > 0 and ar > 0 else 0
                cost += cell_area * (1.0 - ratio)

        if cost < best_cost:
            best_cost = cost
            best_partition = sliced_rows

    if not best_partition:
        return compute_grid_layout(image_count, canvas_width, canvas_height, margin_x, margin_y, gap)

    # Compute layout coordinates from best_partition
    row_ars = [sum(it[1] for it in r_items) for r_items in best_partition]
    inv_ars = [1.0 / max(0.01, ar) for ar in row_ars]
    sum_inv = sum(inv_ars)
    total_h_avail = usable_h - ((R - 1) * gap)

    min_row_h = int(usable_h / (R * 2.2))
    max_row_h = int(usable_h * 2.2 / R)
    raw_h = [max(min_row_h, min(max_row_h, int(total_h_avail * (inv / max(0.01, sum_inv))))) for inv in inv_ars]
    total_raw_h = sum(raw_h)
    row_heights = [int(h_val * (total_h_avail / max(1, total_raw_h))) for h_val in raw_h]
    diff_h = total_h_avail - sum(row_heights)
    row_heights[-1] += diff_h

    cells: List[CellBox] = []
    cur_y = margin_y
    max_cols = 1

    for r_idx, (r_items, rh) in enumerate(zip(best_partition, row_heights)):
        m = len(r_items)
        if m > max_cols:
            max_cols = m

        total_w_avail = usable_w - ((m - 1) * gap)
        ar_sum = sum(it[1] for it in r_items)

        cur_x = margin_x
        for c_idx, (orig_idx, ar) in enumerate(r_items):
            if c_idx == m - 1:
                cw = (margin_x + usable_w) - cur_x
            else:
                cw = max(1, int(total_w_avail * (ar / max(0.01, ar_sum))))

            x1 = cur_x
            y1 = cur_y
            x2 = cur_x + cw
            y2 = cur_y + rh
            cells.append(CellBox(orig_idx, r_idx, c_idx, x1, y1, x2, y2))
            cur_x += cw + gap

        cur_y += rh + gap

    # Sort cells so cells[i] directly corresponds to image index i
    cells.sort(key=lambda c: c.index)
    return R, max_cols, cells

def compute_grid_layout(
    image_count: int,
    canvas_width: int = 1920,
    canvas_height: int = 1080,
    margin_x: Optional[int] = None,
    margin_y: Optional[int] = None,
    gap: Optional[int] = None,
    aspect_ratios: Optional[List[float]] = None
) -> Tuple[int, int, List[CellBox]]:
    """
    Calculates cell boxes for each image in canvas.
    If aspect_ratios contains mixed orientations (portrait & landscape),
    dispatches to compute_bento_layout to minimize empty black borders.
    Otherwise computes uniform NxM grid layout.
    """
    if aspect_ratios and len(aspect_ratios) == image_count:
        min_ar = min(aspect_ratios)
        max_ar = max(aspect_ratios)
        # Use Bento Grid if variance in aspect ratio is significant or portrait photos exist
        if (max_ar / max(0.01, min_ar)) > 1.25 or min_ar < 0.9:
            return compute_bento_layout(
                image_count, canvas_width, canvas_height, aspect_ratios, margin_x, margin_y, gap
            )

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
