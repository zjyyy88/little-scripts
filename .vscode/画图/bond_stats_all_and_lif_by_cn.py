#!/usr/bin/env python
"""Bond statistics for periodic structures with Li-F grouped by Li coordination.

Direct run defaults are set for IDE "Run" button.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from pymatgen.analysis.local_env import CrystalNN
from pymatgen.core import Structure

# 右上角直接运行时默认读取的结构文件路径。
# 后续换结构时，优先改这里。
DEFAULT_STRUCTURE_PATH = (
    r"D:\my-post-graduate-life\third-year\MSS\王博-氟化物搜索\2-1\EA765-221_CONTCAR"
)
# 默认 CSV 输出目录。若目标目录无写权限，可改到本地可写路径（如 D:\vscode）。
DEFAULT_OUT_DIR = r"D:\my-post-graduate-life\third-year\MSS\王博-氟化物搜索\2-1"


@dataclass
class BondRecord:
    i: int
    j: int
    elem_i: str
    elem_j: str
    image: tuple[int, int, int]
    length: float
    weight: float


@dataclass
class LiFBondByCN:
    li_index: int
    f_index: int
    li_cn: int
    image: tuple[int, int, int]
    length: float
    weight: float


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="All-bond stats + Li-F bond stats grouped by Li coordination."
    )
    parser.add_argument(
        # 结构路径参数：不传时使用 DEFAULT_STRUCTURE_PATH
        "structure",
        nargs="?",
        default=DEFAULT_STRUCTURE_PATH,
        help=f"Structure file path (default: {DEFAULT_STRUCTURE_PATH})",
    )
    parser.add_argument(
        # 结果输出目录：不传时使用 DEFAULT_OUT_DIR
        "--out-dir",
        default=DEFAULT_OUT_DIR,
        help=f"CSV output directory (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        # 以哪个元素作为“中心原子”统计配位（默认 Li）
        "--center",
        default="Li",
        help="Center element for coordination grouping (default: Li).",
    )
    parser.add_argument(
        # 统计中心原子与哪个元素的键（默认 F）
        "--neighbor",
        default="F",
        help="Neighbor element for grouped bond stats (default: F).",
    )
    parser.add_argument(
        # CrystalNN 搜索半径，结构稀疏时可适当调大
        "--search-cutoff",
        type=float,
        default=7.0,
        help="CrystalNN neighbor search cutoff in Angstrom (default: 7.0).",
    )
    parser.add_argument(
        # 过滤低权重邻居（0~1）；想更严格可设为 0.1/0.2
        "--min-weight",
        type=float,
        default=0.0,
        help="Discard CrystalNN neighbors with weight below this value.",
    )
    parser.add_argument(
        # 距离上限筛选（单位 A）；不限制则保留默认 None
        "--max-distance",
        type=float,
        default=2.4,
        help="Keep only bonds <= this distance in Angstrom.",
    )
    parser.add_argument(
        # 是否启用加权配位数模式（默认关闭）
        "--weighted-cn",
        action="store_true",
        help="Enable weighted coordination in CrystalNN.",
    )
    parser.add_argument(
        # 是否显示 pymatgen 的警告信息（默认隐藏）
        "--show-warnings",
        action="store_true",
        help="Show pymatgen local_env warnings.",
    )
    parser.add_argument(
        # 仅终端打印，不导出 CSV（调试时常用）
        "--no-csv",
        action="store_true",
        help="Do not write CSV files.",
    )
    return parser


def normalize_image(image: tuple[float, float, float]) -> tuple[int, int, int]:
    return tuple(int(round(float(x))) for x in image)


def canonical_bond_key(
    i: int, j: int, image: tuple[int, int, int]
) -> tuple[tuple[int, int, tuple[int, int, int]], tuple[int, int, int]]:
    if i < j:
        return (i, j, image), image
    if i > j:
        image_neg = (-image[0], -image[1], -image[2])
        return (j, i, image_neg), image_neg
    image_neg = (-image[0], -image[1], -image[2])
    image_canon = min(image, image_neg)
    return (i, i, image_canon), image_canon


def collect_all_bonds(
    structure: Structure, cnn: CrystalNN, min_weight: float, max_distance: float | None
) -> list[BondRecord]:
    seen: set[tuple[int, int, tuple[int, int, int]]] = set()
    bonds: list[BondRecord] = []

    for i in range(len(structure)):
        for nn in cnn.get_nn_info(structure, i):
            j = int(nn["site_index"])
            image = normalize_image(nn["image"])
            weight = float(nn.get("weight", 1.0))
            if weight < min_weight:
                continue

            key, image_canon = canonical_bond_key(i, j, image)
            if key in seen:
                continue

            a, b, _ = key
            length = float(structure.get_distance(a, b, jimage=image_canon))
            if max_distance is not None and length > max_distance:
                continue

            seen.add(key)
            elem_a = structure[a].specie.symbol
            elem_b = structure[b].specie.symbol
            bonds.append(
                BondRecord(
                    i=a,
                    j=b,
                    elem_i=elem_a,
                    elem_j=elem_b,
                    image=image_canon,
                    length=length,
                    weight=weight,
                )
            )
    return bonds


def summarize_by_pair(bonds: list[BondRecord]) -> list[dict[str, float | int | str]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for b in bonds:
        pair = "-".join(sorted((b.elem_i, b.elem_j)))
        grouped[pair].append(b.length)

    rows: list[dict[str, float | int | str]] = []
    for pair in sorted(grouped):
        vals = grouped[pair]
        rows.append(
            {
                "pair": pair,
                "count": len(vals),
                "mean": statistics.fmean(vals),
                "min": min(vals),
                "max": max(vals),
                "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
            }
        )
    return rows


def collect_target_bonds_grouped_by_center_cn(
    structure: Structure,
    cnn: CrystalNN,
    center_elem: str,
    neighbor_elem: str,
    min_weight: float,
    max_distance: float | None,
) -> tuple[list[LiFBondByCN], dict[int, int]]:
    center_indices = [
        i for i, site in enumerate(structure) if site.specie.symbol == center_elem
    ]
    cn_by_center: dict[int, int] = {}
    records: list[LiFBondByCN] = []

    for i in center_indices:
        per_center_seen: set[tuple[int, tuple[int, int, int]]] = set()
        per_center_bonds: list[tuple[int, tuple[int, int, int], float, float]] = []

        for nn in cnn.get_nn_info(structure, i):
            j = int(nn["site_index"])
            if structure[j].specie.symbol != neighbor_elem:
                continue

            image = normalize_image(nn["image"])
            weight = float(nn.get("weight", 1.0))
            if weight < min_weight:
                continue

            local_key = (j, image)
            if local_key in per_center_seen:
                continue

            length = float(structure.get_distance(i, j, jimage=image))
            if max_distance is not None and length > max_distance:
                continue

            per_center_seen.add(local_key)
            per_center_bonds.append((j, image, length, weight))

        cn = len(per_center_bonds)
        cn_by_center[i] = cn

        for j, image, length, weight in per_center_bonds:
            records.append(
                LiFBondByCN(
                    li_index=i,
                    f_index=j,
                    li_cn=cn,
                    image=image,
                    length=length,
                    weight=weight,
                )
            )

    return records, cn_by_center


def summarize_target_by_cn(records: list[LiFBondByCN]) -> list[dict[str, float | int]]:
    grouped: dict[int, list[float]] = defaultdict(list)
    for r in records:
        grouped[r.li_cn].append(r.length)

    rows: list[dict[str, float | int]] = []
    for cn in sorted(grouped):
        vals = grouped[cn]
        rows.append(
            {
                "cn": cn,
                "count_bonds": len(vals),
                "mean": statistics.fmean(vals),
                "min": min(vals),
                "max": max(vals),
                "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
            }
        )
    return rows


def write_all_bond_csv(
    out_dir: Path, stem: str, bonds: list[BondRecord], summary_rows: list[dict[str, float | int | str]]
) -> tuple[Path, Path]:
    detail = out_dir / f"{stem}_all_bond_detail.csv"
    summary = out_dir / f"{stem}_all_bond_summary.csv"

    with detail.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["site_i", "site_j", "elem_i", "elem_j", "image", "length_A", "weight"])
        for b in bonds:
            w.writerow(
                [
                    b.i,
                    b.j,
                    b.elem_i,
                    b.elem_j,
                    f"({b.image[0]},{b.image[1]},{b.image[2]})",
                    f"{b.length:.6f}",
                    f"{b.weight:.6f}",
                ]
            )

    with summary.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "count", "mean_A", "min_A", "max_A", "std_A"])
        for r in summary_rows:
            w.writerow(
                [
                    r["pair"],
                    r["count"],
                    f"{r['mean']:.6f}",
                    f"{r['min']:.6f}",
                    f"{r['max']:.6f}",
                    f"{r['std']:.6f}",
                ]
            )

    return detail, summary


def write_target_cn_csv(
    out_dir: Path,
    stem: str,
    center_elem: str,
    neighbor_elem: str,
    records: list[LiFBondByCN],
    cn_by_center: dict[int, int],
    summary_rows: list[dict[str, float | int]],
) -> tuple[Path, Path, Path]:
    prefix = f"{stem}_{center_elem}-{neighbor_elem}_by_{center_elem}CN"
    detail = out_dir / f"{prefix}_detail.csv"
    summary = out_dir / f"{prefix}_summary.csv"
    site_cn = out_dir / f"{prefix}_site_cn.csv"

    with detail.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                f"{center_elem.lower()}_index",
                f"{neighbor_elem.lower()}_index",
                f"{center_elem}_coordination_number",
                "image",
                "length_A",
                "weight",
            ]
        )
        for r in records:
            w.writerow(
                [
                    r.li_index,
                    r.f_index,
                    r.li_cn,
                    f"({r.image[0]},{r.image[1]},{r.image[2]})",
                    f"{r.length:.6f}",
                    f"{r.weight:.6f}",
                ]
            )

    with summary.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                f"{center_elem}_coordination_number",
                "bond_count",
                "mean_A",
                "min_A",
                "max_A",
                "std_A",
            ]
        )
        for r in summary_rows:
            w.writerow(
                [
                    r["cn"],
                    r["count_bonds"],
                    f"{r['mean']:.6f}",
                    f"{r['min']:.6f}",
                    f"{r['max']:.6f}",
                    f"{r['std']:.6f}",
                ]
            )

    with site_cn.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([f"{center_elem.lower()}_index", f"{center_elem}_coordination_number"])
        for idx in sorted(cn_by_center):
            w.writerow([idx, cn_by_center[idx]])

    return detail, summary, site_cn


def main() -> None:
    args = build_parser().parse_args()
    structure_path = Path(args.structure).expanduser().resolve()
    if not structure_path.exists():
        raise FileNotFoundError(f"Structure file not found: {structure_path}")

    if not args.show_warnings:
        warnings.filterwarnings("ignore", module="pymatgen.analysis.local_env")

    structure = Structure.from_file(structure_path)
    cnn = CrystalNN(weighted_cn=args.weighted_cn, search_cutoff=args.search_cutoff)

    all_bonds = collect_all_bonds(
        structure=structure,
        cnn=cnn,
        min_weight=args.min_weight,
        max_distance=args.max_distance,
    )
    all_summary = summarize_by_pair(all_bonds)

    target_records, cn_by_center = collect_target_bonds_grouped_by_center_cn(
        structure=structure,
        cnn=cnn,
        center_elem=args.center,
        neighbor_elem=args.neighbor,
        min_weight=args.min_weight,
        max_distance=args.max_distance,
    )
    target_summary = summarize_target_by_cn(target_records)
    cn_dist = Counter(cn_by_center.values())

    print(f"Structure: {structure_path}")
    print(f"Formula: {structure.composition.reduced_formula}")
    print(f"Sites: {len(structure)}")
    print(f"Unique all bonds: {len(all_bonds)}")

    print("\nAll-pair bond statistics (Angstrom):")
    print(f"{'Pair':<12}{'Count':>8}{'Mean':>12}{'Min':>12}{'Max':>12}{'Std':>12}")
    for r in all_summary:
        print(
            f"{r['pair']:<12}{r['count']:>8d}{r['mean']:>12.4f}"
            f"{r['min']:>12.4f}{r['max']:>12.4f}{r['std']:>12.4f}"
        )

    print(f"\n{args.center} coordination distribution vs {args.neighbor}:")
    print(f"{'CN':<8}{'Center-site count':>18}")
    for cn in sorted(cn_dist):
        print(f"{cn:<8}{cn_dist[cn]:>18d}")

    print(f"\n{args.center}-{args.neighbor} bond stats grouped by {args.center} CN (Angstrom):")
    if not target_summary:
        print("No target bonds found with current settings.")
    else:
        print(f"{'CN':<8}{'Bond count':>12}{'Mean':>12}{'Min':>12}{'Max':>12}{'Std':>12}")
        for r in target_summary:
            print(
                f"{r['cn']:<8d}{r['count_bonds']:>12d}{r['mean']:>12.4f}"
                f"{r['min']:>12.4f}{r['max']:>12.4f}{r['std']:>12.4f}"
            )

    if args.no_csv:
        return

    # 导出结果文件名以输入结构 stem 为前缀
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = structure_path.stem

    all_detail, all_summary_path = write_all_bond_csv(out_dir, stem, all_bonds, all_summary)
    target_detail, target_summary_path, site_cn_path = write_target_cn_csv(
        out_dir=out_dir,
        stem=stem,
        center_elem=args.center,
        neighbor_elem=args.neighbor,
        records=target_records,
        cn_by_center=cn_by_center,
        summary_rows=target_summary,
    )

    print(f"\nAll-bond detail CSV:   {all_detail}")
    print(f"All-bond summary CSV:  {all_summary_path}")
    print(f"Target detail CSV:     {target_detail}")
    print(f"Target summary CSV:    {target_summary_path}")
    print(f"Center CN list CSV:    {site_cn_path}")


if __name__ == "__main__":
    main()
