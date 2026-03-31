#!/usr/bin/env python
"""Bond-length statistics for periodic structures using pymatgen.
使用方法:python bond_stats_pmg.py "D:\my-post-graduate-life\third-year\MSS\王博-氟化物搜索\LiBF4.vasp" --out-dir "D:\vscode"

Usage examples:
    python bond_stats_pmg.py POSCAR
    python bond_stats_pmg.py my_structure.vasp --min-weight 0.2
    python bond_stats_pmg.py my_structure.vasp --no-csv
"""

from __future__ import annotations

import argparse
import csv
import statistics
import warnings
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from pymatgen.analysis.local_env import CrystalNN
from pymatgen.core import Structure


@dataclass
class BondRecord:
    # 记录一条唯一键的信息（原子索引、元素、周期像、键长、权重）
    i: int
    j: int
    elem_i: str
    elem_j: str
    image: tuple[int, int, int]
    length: float
    weight: float


def build_parser() -> argparse.ArgumentParser:
    # 命令行参数定义：输入结构、判键参数、导出参数
    parser = argparse.ArgumentParser(
        description="Count and summarize bond lengths in a .vasp/POSCAR structure."
    )
    parser.add_argument("structure", help="Path to a structure file (.vasp, POSCAR, CONTCAR, ...).")
    parser.add_argument(
        "--search-cutoff",
        type=float,
        default=7.0,
        help="Neighbor search cutoff used by CrystalNN (default: 7.0 A).",
    )
    parser.add_argument(
        "--min-weight",
        type=float,
        default=0.0,
        help="Discard neighbors with CrystalNN weight below this value (default: 0.0).",
    )
    parser.add_argument(
        "--max-distance",
        type=float,
        default=None,
        help="Keep only bonds <= this distance in Angstrom.",
    )
    parser.add_argument(
        "--weighted-cn",
        action="store_true",
        help="Enable weighted coordination in CrystalNN.",
    )
    parser.add_argument(
        "--show-warnings",
        action="store_true",
        help="Show CrystalNN warnings (hidden by default for clean output).",
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Do not write CSV files; print only terminal statistics.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory for output CSV files (default: same directory as structure file).",
    )
    return parser


def normalize_image(image: tuple[float, float, float]) -> tuple[int, int, int]:
    # pymatgen 返回的 image 可能是 np.float64，这里统一转为整数三元组
    return tuple(int(round(float(x))) for x in image)


def canonical_bond_key(
    i: int, j: int, image: tuple[int, int, int]
) -> tuple[tuple[int, int, tuple[int, int, int]], tuple[int, int, int]]:
    # 把 (i,j,image) 规范化，确保 i-j 与 j-i 不会被重复统计
    if i < j:
        return (i, j, image), image
    if i > j:
        image_neg = (-image[0], -image[1], -image[2])
        return (j, i, image_neg), image_neg

    image_neg = (-image[0], -image[1], -image[2])
    image_canon = min(image, image_neg)
    return (i, i, image_canon), image_canon


def collect_bonds(structure: Structure, cnn: CrystalNN, min_weight: float) -> list[BondRecord]:
    # 扫描所有原子的近邻，生成去重后的“唯一键”列表
    seen: set[tuple[int, int, tuple[int, int, int]]] = set()
    bonds: list[BondRecord] = []

    for i in range(len(structure)):
        for nn in cnn.get_nn_info(structure, i):
            j = int(nn["site_index"])
            image = normalize_image(nn["image"])
            weight = float(nn.get("weight", 1.0))
            if weight < min_weight:
                # 可选阈值：过滤 CrystalNN 置信度较低的近邻
                continue

            key, image_canon = canonical_bond_key(i, j, image)
            if key in seen:
                continue
            seen.add(key)

            a, b, _ = key
            # 使用规范化后的周期像计算键长，保证距离与去重键一致
            length = float(structure.get_distance(a, b, jimage=image_canon))
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


def summarize(bonds: list[BondRecord]) -> list[dict[str, float | int | str]]:
    # 按元素对（如 B-F、Li-F）分组做统计
    grouped: dict[str, list[float]] = defaultdict(list)
    for bond in bonds:
        pair = "-".join(sorted((bond.elem_i, bond.elem_j)))
        grouped[pair].append(bond.length)

    rows: list[dict[str, float | int | str]] = []
    for pair in sorted(grouped):
        values = grouped[pair]
        rows.append(
            {
                "pair": pair,
                "count": len(values),
                "mean": statistics.fmean(values),
                "min": min(values),
                "max": max(values),
                "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
            }
        )
    return rows


def write_detail_csv(path: Path, bonds: list[BondRecord]) -> None:
    # 明细表：每一条唯一键一行
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["site_i", "site_j", "elem_i", "elem_j", "image", "length_A", "weight"])
        for b in bonds:
            writer.writerow(
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


def write_summary_csv(path: Path, summary_rows: list[dict[str, float | int | str]]) -> None:
    # 汇总表：每种键类型一行
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pair", "count", "mean_A", "min_A", "max_A", "std_A"])
        for row in summary_rows:
            writer.writerow(
                [
                    row["pair"],
                    row["count"],
                    f"{row['mean']:.6f}",
                    f"{row['min']:.6f}",
                    f"{row['max']:.6f}",
                    f"{row['std']:.6f}",
                ]
            )


def main() -> None:
    args = build_parser().parse_args()
    structure_path = Path(args.structure).expanduser().resolve()

    if not structure_path.exists():
        raise FileNotFoundError(f"Structure file not found: {structure_path}")

    if not args.show_warnings:
        warnings.filterwarnings("ignore", module="pymatgen.analysis.local_env")

    structure = Structure.from_file(structure_path)
    # CrystalNN 是 pymatgen 常用的晶体近邻识别器
    cnn = CrystalNN(weighted_cn=args.weighted_cn, search_cutoff=args.search_cutoff)

    bonds = collect_bonds(structure, cnn=cnn, min_weight=args.min_weight)
    if args.max_distance is not None:
        # 可选距离截断：只保留较短键
        bonds = [b for b in bonds if b.length <= args.max_distance]

    summary_rows = summarize(bonds)

    print(f"Structure: {structure_path}")
    print(f"Formula: {structure.composition.reduced_formula}")
    print(f"Sites: {len(structure)}")
    print(f"Unique bonds: {len(bonds)}")

    if not bonds:
        print("No bonds found with current settings.")
        return

    print("\nPair statistics (Angstrom):")
    print(f"{'Pair':<12}{'Count':>8}{'Mean':>12}{'Min':>12}{'Max':>12}{'Std':>12}")
    for row in summary_rows:
        print(
            f"{row['pair']:<12}{row['count']:>8d}{row['mean']:>12.4f}"
            f"{row['min']:>12.4f}{row['max']:>12.4f}{row['std']:>12.4f}"
        )

    if args.no_csv:
        return

    # 默认导出到结构文件所在目录，也可以通过 --out-dir 指定
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else structure_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = structure_path.stem
    detail_csv = out_dir / f"{stem}_bond_detail.csv"
    summary_csv = out_dir / f"{stem}_bond_summary.csv"
    write_detail_csv(detail_csv, bonds)
    write_summary_csv(summary_csv, summary_rows)
    print(f"\nDetail CSV:  {detail_csv}")
    print(f"Summary CSV: {summary_csv}")


if __name__ == "__main__":
    main()
