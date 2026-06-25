"""Generate a tight rectangular flowchart using matplotlib.

Produces:
  outputs/flowchart/industry_heat_dataflow.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

OUT_DIR = Path(__file__).parent.parent / "outputs" / "flowchart"
PNG_FILE = OUT_DIR / "industry_heat_dataflow.png"

# ── Colours ──
C_SRC = ("#fff7e6", "#d95f0e")
C_DS  = ("#e8f4f8", "#2c7bb6")
C_EL  = ("#e8f8e8", "#2ca02c")
C_GRP = ("#f8f8f8", "#bbbbbb")
C_ARR = "#777777"
C_ARR_DASH = "#999999"


# ── Data ──
DATA_SOURCES = [
    "Mayer2024", "heat_tech_param\n.xlsx", "Rehfeldt2017", "AIDRES2023",
    "Wolf2017", "process_param\n.xlsx", "JRC-EU-TIMES",
    "JRC-IDEES\n-2023", "Eurostat", "FAOSTAT",
    "industry_carriers\n.xlsx",
]

DATASETS = [
    ("Mayer2024", "TES params"),
    ("HeatTechParam.", "boiler & HP\nparams"),
    ("ProcessParam.", "sector params,\nfuel shares, costs"),
    ("JrcIdees", "capacity &\ndemand"),
    ("Eurostat", "boiler capacity"),
    ("Faostat", "food cap. &\ndemand"),
    ("IndustryCarrier", "carrier\nattributes"),
]

GROUPS = [
    ("TES", [
        ["water 0-100", "water 100-150"],
        ["steam 100-150", "steam 150-200"],
    ]),
    ("Heat Supply", [
        ["HP 0-100", "HP 100-150", "HP 150-200"],
        ["bio. boiler", "elec. boiler", "NG boiler"],
        ["temp conv 150", "temp conv 100"],
    ]),
    ("Production", [
        ["glass prod.", "ceramic prod.", "paper prod.", "food prod."],
    ]),
    ("Carriers", [
        ["glass", "ceramic", "paper", "food"],
        ["heat 0-100", "heat 100-150", "heat 150-200"],
    ]),
    ("DSM", [
        ["glass DSM", "ceramic DSM"],
        ["paper DSM", "food DSM"],
    ]),
]

# source_idx -> dataset_idx
EDGES_S2D = [
    (0, 0),                         # Mayer2024 -> Mayer2024
    (1, 1),                         # heat_tech_param -> HeatTechParam
    (2, 2), (3, 2), (4, 2),         # Rehfeldt,AIDRES,Wolf -> ProcessParam
    (5, 2), (6, 2),                 # process_param,JRC-EU-TIMES -> ProcessParam
    (7, 3),                         # JRC-IDEES -> JrcIdees
    (8, 4),                         # Eurostat -> Eurostat
    (9, 5),                         # FAOSTAT -> Faostat
    (10, 6),                        # industry_carriers -> IndustryCarrier
]
EDGES_S2D_DASHED = [(7, 2)]        # JRC-IDEES -.-> ProcessParam (fuel shares)

# dataset_idx -> group_idx
EDGES_D2G = [
    (0, 0),                         # Mayer2024 -> TES
    (1, 1),                         # HeatTechParam -> Heat Supply
    (2, 1), (2, 2),                 # ProcessParam -> Heat Supply, Production
    (3, 2), (3, 3),                 # JrcIdees -> Production, Carriers
    (4, 1),                         # Eurostat -> Heat Supply
    (5, 2), (5, 3),                 # Faostat -> Production, Carriers
    (6, 3),                         # IndustryCarrier -> Carriers
]


def _rect(ax, x, y, w, h, fill, edge, lw=0.7, zorder=2):
    r = mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02",
        facecolor=fill, edgecolor=edge, linewidth=lw, zorder=zorder,
    )
    ax.add_patch(r)
    return r


def _text(ax, x, y, txt, fs=7, bold=False, italic=False, color="#333", zorder=3, ha="center", va="center"):
    ax.text(x, y, txt, fontsize=fs, fontweight="bold" if bold else "normal",
            fontstyle="italic" if italic else "normal", color=color,
            ha=ha, va=va, family="sans-serif", zorder=zorder)


def _arrow(ax, x0, y0, x1, y1, dashed=False):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(
                    arrowstyle="->,head_width=0.15,head_length=0.1",
                    color=C_ARR_DASH if dashed else C_ARR,
                    lw=0.6, linestyle="--" if dashed else "-",
                    shrinkA=1, shrinkB=1,
                ), zorder=1)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Layout constants ──
    FW, FH = 20, 14
    fig, ax = plt.subplots(figsize=(FW, FH))
    ax.set_xlim(0, FW)
    ax.set_ylim(0, FH)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # Column positions: sources | datasets | element groups (centred in figure)
    COL_SRC_X = 2.5       # centre of source column
    COL_DS_X  = 7.0       # centre of dataset column
    COL_EL_X0 = 11.5      # left edge of element area

    # ── Sources (left column, stacked vertically) ──
    src_w, src_h = 2.0, 0.55
    src_gap = 0.15
    n_src = len(DATA_SOURCES)
    src_total_h = n_src * src_h + (n_src - 1) * src_gap
    src_y_top = FH / 2 + src_total_h / 2
    src_positions = []

    for i, name in enumerate(DATA_SOURCES):
        cy = src_y_top - i * (src_h + src_gap) - src_h / 2
        cx = COL_SRC_X
        _rect(ax, cx - src_w / 2, cy - src_h / 2, src_w, src_h, *C_SRC)
        _text(ax, cx, cy, name, fs=6.5)
        src_positions.append((cx + src_w / 2, cy))

    # Source group box
    _rect(ax, COL_SRC_X - src_w / 2 - 0.25, src_y_top - src_total_h - 0.2,
          src_w + 0.5, src_total_h + 0.7, C_GRP[0], C_SRC[1], lw=1.0, zorder=0)
    _text(ax, COL_SRC_X, src_y_top + 0.2, "Data Sources", fs=9, bold=True, color=C_SRC[1])

    # ── Datasets (middle column, stacked vertically) ──
    ds_w, ds_h = 2.8, 0.7
    ds_gap = 0.2
    n_ds = len(DATASETS)
    ds_total_h = n_ds * ds_h + (n_ds - 1) * ds_gap
    ds_y_top = FH / 2 + ds_total_h / 2
    ds_positions = []

    for i, (name, sub) in enumerate(DATASETS):
        cy = ds_y_top - i * (ds_h + ds_gap) - ds_h / 2
        cx = COL_DS_X
        _rect(ax, cx - ds_w / 2, cy - ds_h / 2, ds_w, ds_h, *C_DS)
        _text(ax, cx, cy + 0.1, name, fs=7.5, bold=True)
        _text(ax, cx, cy - 0.15, sub, fs=5.5, italic=True, color="#666")
        ds_positions.append((cx - ds_w / 2, cy, cx + ds_w / 2, cy))

    # Dataset group box
    _rect(ax, COL_DS_X - ds_w / 2 - 0.25, ds_y_top - ds_total_h - 0.2,
          ds_w + 0.5, ds_total_h + 0.7, C_GRP[0], C_DS[1], lw=1.0, zorder=0)
    _text(ax, COL_DS_X, ds_y_top + 0.2, "Dataset Classes", fs=9, bold=True, color=C_DS[1])

    # ── Element groups (right area, grid layout) ──
    el_w, el_h = 1.35, 0.42
    el_gap_x, el_gap_y = 0.15, 0.12
    grp_pad = 0.2
    grp_title_h = 0.35
    grp_gap_y = 0.35

    grp_rects = []  # (left_x, center_y) for arrow targets
    grp_y_cursor = FH - 1.2

    for gi, (gname, rows) in enumerate(GROUPS):
        n_cols = max(len(r) for r in rows)
        n_rows = len(rows)
        inner_w = n_cols * el_w + (n_cols - 1) * el_gap_x
        inner_h = n_rows * el_h + (n_rows - 1) * el_gap_y
        box_w = inner_w + 2 * grp_pad
        box_h = inner_h + grp_title_h + 2 * grp_pad

        bx = COL_EL_X0
        by = grp_y_cursor - box_h

        _rect(ax, bx, by, box_w, box_h, C_GRP[0], C_EL[1], lw=0.9, zorder=0)
        _text(ax, bx + box_w / 2, by + box_h - grp_pad + 0.05, gname,
              fs=8, bold=True, color=C_EL[1])

        row_y_top = by + box_h - grp_title_h - grp_pad
        for ri, row in enumerate(rows):
            for ci, label in enumerate(row):
                ex = bx + grp_pad + ci * (el_w + el_gap_x)
                ey = row_y_top - ri * (el_h + el_gap_y) - el_h
                _rect(ax, ex, ey, el_w, el_h, *C_EL)
                _text(ax, ex + el_w / 2, ey + el_h / 2, label, fs=6)

        grp_center_y = by + box_h / 2
        grp_rects.append((bx, grp_center_y))
        grp_y_cursor = by - grp_gap_y

    # Outer element box
    el_box_right = COL_EL_X0 + max(
        max(len(r) for r in rows) * el_w + (max(len(r) for r in rows) - 1) * el_gap_x + 2 * grp_pad
        for _, rows in GROUPS
    )
    outer_bottom = grp_y_cursor + grp_gap_y - 0.3
    outer_top = FH - 0.65
    _rect(ax, COL_EL_X0 - 0.3, outer_bottom,
          el_box_right - COL_EL_X0 + 0.6,
          outer_top - outer_bottom,
          "none", "#555555", lw=1.2, zorder=0)
    _text(ax, (COL_EL_X0 + el_box_right) / 2, outer_top - 0.2,
          "Element Classes / IndustryHeat Sector — 27", fs=9, bold=True, color="#555")

    # ── Arrows: Sources -> Datasets ──
    for si, di in EDGES_S2D:
        sx, sy = src_positions[si]
        dx, dy = ds_positions[di][0], ds_positions[di][1]
        _arrow(ax, sx, sy, dx, dy)

    for si, di in EDGES_S2D_DASHED:
        sx, sy = src_positions[si]
        dx, dy = ds_positions[di][0], ds_positions[di][1]
        _arrow(ax, sx, sy, dx, dy, dashed=True)
        mx, my = (sx + dx) / 2, (sy + dy) / 2
        _text(ax, mx, my + 0.15, "fuel shares", fs=5, italic=True, color=C_ARR_DASH)

    # ── Arrows: Datasets -> Groups ──
    for di, gi in EDGES_D2G:
        dx, dy = ds_positions[di][2], ds_positions[di][3]
        gx, gy = grp_rects[gi]
        _arrow(ax, dx, dy, gx, gy)

    # ── Title ──
    _text(ax, FW / 2, FH - 0.15, "Industry Heat — Data Flow",
          fs=14, bold=True, color="#333")

    fig.savefig(str(PNG_FILE), dpi=200, bbox_inches="tight",
                facecolor="white", edgecolor="none", pad_inches=0.1)
    plt.close(fig)
    print(f"PNG saved to {PNG_FILE}")


if __name__ == "__main__":
    main()
