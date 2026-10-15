"""
Grid Calculator Service for FOTOSTREAM.
Calculates optimal, area-balanced, black-area-minimizing layouts for 1 to 49 images
supporting mixed aspect ratios (including 16:9 landscape and 9:16 portrait photos).
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
                aspect_diff = abs(aspect - (16.0 / 9.0))
                orientation_penalty = 0.5 if m < n else 0.0
                score = (waste * 2.0) + aspect_diff + orientation_penalty
                candidates.append((score, waste, n, m))

    candidates.sort(key=lambda item: item[0])
    best = candidates[0]
    return best[2], best[3]  # rows, cols

def _get_integer_partitions(n: int, k: int, min_val: int = 1):
    """Generate all partitions of integer n into k positive parts."""
    if k == 1:
        if n >= min_val:
            yield [n]
        return
    for i in range(min_val, n - k + 2):
        for rest in _get_integer_partitions(n - i, k - 1, 1):
            yield [i] + rest

def _evaluate_layout_cost(cells: List[CellBox], aspect_ratios: List[float], target_area: float) -> float:
    """
    Calculate composite loss:
    Wasted/Black area + mild penalty for area imbalance (equal area preservation).
    """
    cost = 0.0
    for c in cells:
        ar = aspect_ratios[c.index]
        cell_ar = c.width / max(1, c.height)
        match_ratio = min(ar / max(0.01, cell_ar), cell_ar / max(0.01, ar))
        cell_area = c.width * c.height
        wasted_area = cell_area * (1.0 - match_ratio)
        area_diff = abs(cell_area - target_area) / max(1.0, target_area)
        # 85% weight on minimizing black area, 15% on equal area preservation
        cost += wasted_area + (0.15 * target_area * (area_diff ** 2))
    return cost

def _solve_row_partition(
    items: List[Tuple[int, float]],
    x_offset: int,
    y_offset: int,
    usable_w: int,
    usable_h: int,
    gap: int,
    target_area: float,
    all_aspect_ratios: List[float]
) -> Tuple[float, int, int, List[CellBox]]:
    """Solve optimal row-based layout for given items."""
    k = len(items)
    if k == 0:
        return float('inf'), 0, 0, []
    if k == 1:
        idx, _ = items[0]
        cell = CellBox(idx, 0, 0, x_offset, y_offset, x_offset + usable_w, y_offset + usable_h)
        return _evaluate_layout_cost([cell], all_aspect_ratios, target_area), 1, 1, [cell]

    # Try different row counts R
    best_cost = float('inf')
    best_cells: List[CellBox] = []
    best_r = 1
    best_max_cols = 1

    max_r = min(k, 6)
    # Sort items by aspect ratio
    sorted_items = sorted(items, key=lambda x: x[1])

    for r in range(1, max_r + 1):
        if r == 1:
            partitions = [[k]]
        elif k <= 10:
            partitions = list(_get_integer_partitions(k, r))
        else:
            base = k / r
            partitions = [p for p in _get_integer_partitions(k, r) if all(abs(cnt - base) <= 2.2 for cnt in p)]
            if not partitions:
                b_int = k // r
                rem = k % r
                partitions = [[b_int + (1 if i < rem else 0) for i in range(r)]]

        total_h_avail = usable_h - ((r - 1) * gap)
        if total_h_avail < r * 20:
            continue

        for p in partitions:
            # Slice sorted items into rows
            sliced_rows = []
            start = 0
            for cnt in p:
                sliced_rows.append(sorted_items[start : start + cnt])
                start += cnt

            # Compute row heights proportional to 1 / sum(aspect_ratios)
            row_ars = [sum(it[1] for it in r_items) for r_items in sliced_rows]
            inv_ars = [1.0 / max(0.01, ar) for ar in row_ars]
            sum_inv = sum(inv_ars)

            raw_h = [int(total_h_avail * (inv / max(0.01, sum_inv))) for inv in inv_ars]
            diff_h = total_h_avail - sum(raw_h)
            raw_h[-1] += diff_h

            if any(h_val < 20 for h_val in raw_h):
                continue

            cur_y = y_offset
            cand_cells: List[CellBox] = []
            cand_max_cols = 1

            for r_idx, (r_items, rh) in enumerate(zip(sliced_rows, raw_h)):
                m = len(r_items)
                if m > cand_max_cols:
                    cand_max_cols = m
                total_w_avail = usable_w - ((m - 1) * gap)
                ar_sum = sum(it[1] for it in r_items)
                cur_x = x_offset
                for c_idx, (orig_idx, ar) in enumerate(r_items):
                    if c_idx == m - 1:
                        cw = (x_offset + usable_w) - cur_x
                    else:
                        cw = max(1, int(total_w_avail * (ar / max(0.01, ar_sum))))
                    cand_cells.append(CellBox(orig_idx, r_idx, c_idx, cur_x, cur_y, cur_x + cw, cur_y + rh))
                    cur_x += cw + gap
                cur_y += rh + gap

            cost = _evaluate_layout_cost(cand_cells, all_aspect_ratios, target_area)
            if cost < best_cost:
                best_cost = cost
                best_cells = cand_cells
                best_r = r
                best_max_cols = cand_max_cols

    return best_cost, best_r, best_max_cols, best_cells

def _solve_col_partition(
    items: List[Tuple[int, float]],
    x_offset: int,
    y_offset: int,
    usable_w: int,
    usable_h: int,
    gap: int,
    target_area: float,
    all_aspect_ratios: List[float]
) -> Tuple[float, int, int, List[CellBox]]:
    """Solve optimal column-based layout (vertical strips) for given items."""
    k = len(items)
    if k <= 1:
        return float('inf'), 0, 0, []

    best_cost = float('inf')
    best_cells: List[CellBox] = []
    best_max_rows = 1
    best_c = 1

    max_c = min(k, 8)
    sorted_items = sorted(items, key=lambda x: x[1])

    for c in range(2, max_c + 1):
        if k <= 10:
            partitions = list(_get_integer_partitions(k, c))
        else:
            base = k / c
            partitions = [p for p in _get_integer_partitions(k, c) if all(abs(cnt - base) <= 2.2 for cnt in p)]
            if not partitions:
                b_int = k // c
                rem = k % c
                partitions = [[b_int + (1 if i < rem else 0) for i in range(c)]]

        total_w_avail = usable_w - ((c - 1) * gap)
        if total_w_avail < c * 20:
            continue

        for p in partitions:
            sliced_cols = []
            start = 0
            for cnt in p:
                sliced_cols.append(sorted_items[start : start + cnt])
                start += cnt

            col_inv_ars = [sum(1.0 / max(0.01, it[1]) for it in c_items) for c_items in sliced_cols]
            col_widths_raw = [1.0 / max(0.01, inv) for inv in col_inv_ars]
            sum_w_raw = sum(col_widths_raw)

            raw_w = [int(total_w_avail * (w_val / max(0.01, sum_w_raw))) for w_val in col_widths_raw]
            diff_w = total_w_avail - sum(raw_w)
            raw_w[-1] += diff_w

            if any(w_val < 20 for w_val in raw_w):
                continue

            cur_x = x_offset
            cand_cells: List[CellBox] = []
            cand_max_rows = 1

            for c_idx, (c_items, cw) in enumerate(zip(sliced_cols, raw_w)):
                m = len(c_items)
                if m > cand_max_rows:
                    cand_max_rows = m
                total_h_avail = usable_h - ((m - 1) * gap)
                inv_sum = sum(1.0 / max(0.01, it[1]) for it in c_items)
                cur_y = y_offset
                for r_idx, (orig_idx, ar) in enumerate(c_items):
                    if r_idx == m - 1:
                        ch = (y_offset + usable_h) - cur_y
                    else:
                        ch = max(1, int(total_h_avail * ((1.0 / max(0.01, ar)) / max(0.01, inv_sum))))
                    cand_cells.append(CellBox(orig_idx, r_idx, c_idx, cur_x, cur_y, cur_x + cw, cur_y + ch))
                    cur_y += ch + gap
                cur_x += cw + gap

            cost = _evaluate_layout_cost(cand_cells, all_aspect_ratios, target_area)
            if cost < best_cost:
                best_cost = cost
                best_cells = cand_cells
                best_max_rows = cand_max_rows
                best_c = c

    return best_cost, best_max_rows, best_c, best_cells

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
    Computes an optimized layout for mixed 16:9 and 9:16 aspect ratio photos.
    Removes uniform NxM restriction to minimize black/empty wasted spaces while
    allocating approximately equal nominal area to every photo.
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

    usable_w = canvas_width - (2 * margin_x)
    usable_h = canvas_height - (2 * margin_y)

    if image_count == 1:
        cell = CellBox(0, 0, 0, margin_x, margin_y, margin_x + usable_w, margin_y + usable_h)
        return 1, 1, [cell]

    target_area = (usable_w * usable_h) / float(image_count)
    all_items = [(i, aspect_ratios[i]) for i in range(image_count)]

    # Candidate 1: Dynamic Row Partitioning
    cost_row, r_row, c_row, cells_row = _solve_row_partition(
        all_items, margin_x, margin_y, usable_w, usable_h, gap, target_area, aspect_ratios
    )

    # Candidate 2: Dynamic Column Partitioning
    cost_col, r_col, c_col, cells_col = _solve_col_partition(
        all_items, margin_x, margin_y, usable_w, usable_h, gap, target_area, aspect_ratios
    )

    best_cost = cost_row
    best_r = r_row
    best_c = c_row
    best_cells = cells_row

    if cost_col < best_cost:
        best_cost = cost_col
        best_r = r_col
        best_c = c_col
        best_cells = cells_col

    # Candidate 3: Clustered Block Split (Guillotine Tree for mixed portrait & landscape)
    portraits = [it for it in all_items if it[1] < 1.0]
    landscapes = [it for it in all_items if it[1] >= 1.0]

    if portraits and landscapes and len(portraits) + len(landscapes) == image_count:
        ratio_p = len(portraits) / float(image_count)
        ratio_l = len(landscapes) / float(image_count)

        # Split A: Horizontal split (Top block vs Bottom block)
        avail_h_split = usable_h - gap
        h_p = max(80, int(avail_h_split * ratio_p))
        h_l = avail_h_split - h_p

        # Top: Landscapes, Bottom: Portraits
        _, r_l1, c_l1, cells_l1 = _solve_row_partition(
            landscapes, margin_x, margin_y, usable_w, h_l, gap, target_area, aspect_ratios
        )
        _, r_p1, c_p1, cells_p1 = _solve_row_partition(
            portraits, margin_x, margin_y + h_l + gap, usable_w, h_p, gap, target_area, aspect_ratios
        )
        if cells_l1 and cells_p1:
            cand_cells = cells_l1 + cells_p1
            cand_cost = _evaluate_layout_cost(cand_cells, aspect_ratios, target_area)
            if cand_cost < best_cost:
                best_cost = cand_cost
                best_r = r_l1 + r_p1
                best_c = max(c_l1, c_p1)
                best_cells = cand_cells

        # Split B: Vertical split (Left block vs Right block)
        avail_w_split = usable_w - gap
        w_p = max(80, int(avail_w_split * ratio_p))
        w_l = avail_w_split - w_p

        # Left: Portraits, Right: Landscapes
        _, r_p2, c_p2, cells_p2 = _solve_col_partition(
            portraits, margin_x, margin_y, w_p, usable_h, gap, target_area, aspect_ratios
        )
        if not cells_p2:
            _, r_p2, c_p2, cells_p2 = _solve_row_partition(
                portraits, margin_x, margin_y, w_p, usable_h, gap, target_area, aspect_ratios
            )

        _, r_l2, c_l2, cells_l2 = _solve_row_partition(
            landscapes, margin_x + w_p + gap, margin_y, w_l, usable_h, gap, target_area, aspect_ratios
        )
        if cells_p2 and cells_l2:
            cand_cells = cells_p2 + cells_l2
            cand_cost = _evaluate_layout_cost(cand_cells, aspect_ratios, target_area)
            if cand_cost < best_cost:
                best_cost = cand_cost
                best_r = max(r_p2, r_l2)
                best_c = c_p2 + c_l2
                best_cells = cand_cells

    if not best_cells or len(best_cells) != image_count:
        # Fallback to standard uniform grid
        return compute_grid_layout(image_count, canvas_width, canvas_height, margin_x, margin_y, gap, aspect_ratios=None)

    # Sort cells strictly by image index 0..K-1
    best_cells.sort(key=lambda c: c.index)
    return max(1, best_r), max(1, best_c), best_cells

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
    If aspect_ratios is provided, optimizes non-uniform layout to minimize black area.
    Otherwise computes uniform NxM grid layout.
    """
    if aspect_ratios and len(aspect_ratios) == image_count:
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
