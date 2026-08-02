#!/usr/bin/env python
"""
使用本地 Materials Project 数据查询或计算凸包能。

当前桌面 mp.tar.gz 的 summary.csv 只包含 MP 已计算好的
energy_above_hull，因此：

1. lookup 可直接查询数据库中已有材料的凸包能。
2. calculate 需要参考数据额外包含 formation_energy_per_atom，
   才能为新材料重新构建相图并计算凸包能。

示例：
  python 本地MP凸包能.py inspect
  python 本地MP凸包能.py lookup --material-id mp-985592
  python 本地MP凸包能.py lookup --formula Li6PS5Cl
  python 本地MP凸包能.py calculate --formula Li6PS5Cl ^
      --target-formation-energy-per-atom -1.85 ^
      --references D:\\data\\mp_with_formation_energy.csv

目标能量必须和参考数据采用同一套 DFT/修正口径。不能把任意 VASP
绝对能直接与 MP formation_energy_per_atom 混用。
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
import tarfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, TextIO


DEFAULT_ARCHIVE = Path(r"C:\Users\16540\Desktop\mp.tar.gz")
FORMULA_COLUMNS = ("formula_pretty", "formula", "composition")
FORMATION_ENERGY_COLUMNS = (
    "formation_energy_per_atom",
    "formation_energy_per_atom_corrected",
)


def _configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


class LocalMPError(RuntimeError):
    """可直接展示给用户的数据或输入错误。"""


def _find_column(fieldnames: list[str], candidates: tuple[str, ...]) -> str | None:
    normalized = {name.strip().lower(): name for name in fieldnames}
    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]
    return None


def _find_summary_member(archive: tarfile.TarFile) -> tarfile.TarInfo:
    csv_members = [
        member
        for member in archive.getmembers()
        if member.isfile() and member.name.lower().endswith("/summary.csv")
    ]
    if not csv_members:
        csv_members = [
            member
            for member in archive.getmembers()
            if member.isfile() and member.name.lower() == "summary.csv"
        ]
    if not csv_members:
        raise LocalMPError("压缩包中没有找到 summary.csv。")
    return min(csv_members, key=lambda member: len(member.name))


@contextmanager
def open_csv_source(path: Path) -> Iterator[tuple[csv.DictReader, str]]:
    """打开普通 CSV 或 tar/tar.gz 中的 summary.csv。"""
    if not path.exists():
        raise LocalMPError(f"数据文件不存在：{path}")

    if tarfile.is_tarfile(path):
        with tarfile.open(path, mode="r:*") as archive:
            member = _find_summary_member(archive)
            raw_stream = archive.extractfile(member)
            if raw_stream is None:
                raise LocalMPError(f"无法读取压缩包成员：{member.name}")
            with io.TextIOWrapper(
                raw_stream, encoding="utf-8-sig", newline=""
            ) as text_stream:
                yield csv.DictReader(text_stream), member.name
        return

    if path.suffix.lower() != ".csv":
        raise LocalMPError(
            "参考数据目前支持 CSV、.tar、.tar.gz；压缩包中需包含 summary.csv。"
        )

    with path.open("r", encoding="utf-8-sig", newline="") as text_stream:
        yield csv.DictReader(text_stream), path.name


def _safe_float(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise LocalMPError(f"{field_name} 不是有效数字：{value!r}") from exc
    if not math.isfinite(number):
        raise LocalMPError(f"{field_name} 必须是有限数值：{value!r}")
    return number


def command_inspect(args: argparse.Namespace) -> int:
    source = Path(args.archive)
    with open_csv_source(source) as (reader, member_name):
        fieldnames = list(reader.fieldnames or [])
        row_count = sum(1 for _ in reader)

    has_stored_hull = _find_column(fieldnames, ("energy_above_hull",)) is not None
    formation_column = _find_column(fieldnames, FORMATION_ENERGY_COLUMNS)

    print(f"数据文件：{source}")
    print(f"数据成员：{member_name}")
    print(f"记录数量：{row_count:,}")
    print(f"字段：{', '.join(fieldnames)}")
    print(f"可查询库中已有凸包能：{'是' if has_stored_hull else '否'}")
    print(f"可重建相图计算新材料：{'是' if formation_column else '否'}")
    if not formation_column:
        print(
            "原因：缺少 formation_energy_per_atom。CIF 只保存结构，"
            "不能从原子坐标反推出 DFT 能量。"
        )
    return 0


def _normalize_text(value: Any) -> str:
    return "".join(str(value).split()).casefold()


def command_lookup(args: argparse.Namespace) -> int:
    source = Path(args.archive)
    query_id = _normalize_text(args.material_id) if args.material_id else None
    query_formula = _normalize_text(args.formula) if args.formula else None

    matches: list[dict[str, str]] = []
    with open_csv_source(source) as (reader, _):
        fieldnames = list(reader.fieldnames or [])
        id_column = _find_column(fieldnames, ("material_id", "task_id"))
        formula_column = _find_column(fieldnames, FORMULA_COLUMNS)
        hull_column = _find_column(fieldnames, ("energy_above_hull", "e_above_hull"))

        if not id_column or not formula_column or not hull_column:
            raise LocalMPError(
                "数据表至少需要 material_id、formula_pretty/formula 和 "
                "energy_above_hull 字段。"
            )

        for row in reader:
            id_matches = query_id and _normalize_text(row.get(id_column)) == query_id
            formula_matches = (
                query_formula
                and _normalize_text(row.get(formula_column)) == query_formula
            )
            if id_matches or formula_matches:
                matches.append(row)

    if not matches:
        query = args.material_id or args.formula
        print(f"未找到：{query}")
        return 1

    print(
        f"{'material_id':<16} {'formula':<20} "
        f"{'E_hull (eV/atom)':>18} {'E_hull (meV/atom)':>20}"
    )
    for row in sorted(matches, key=lambda item: float(item[hull_column])):
        hull_ev = _safe_float(row[hull_column], hull_column)
        print(
            f"{row[id_column]:<16} {row[formula_column]:<20} "
            f"{hull_ev:>18.8f} {hull_ev * 1000:>20.3f}"
        )
        if tarfile.is_tarfile(source):
            print(f"  CIF 成员：mp/{row[id_column]}.cif")
    return 0


def _import_pymatgen() -> dict[str, Any]:
    try:
        from pymatgen.analysis.phase_diagram import PDEntry, PhaseDiagram
        from pymatgen.core import Composition, Structure
        from pymatgen.io.vasp.outputs import Vasprun
    except ImportError as exc:
        raise LocalMPError(
            "calculate 需要 pymatgen。请使用 "
            r"D:\A_caculate\Mambaforge\python.exe 运行此命令；"
            r"D:\vscode\anaconda 当前没有安装 pymatgen。"
        ) from exc
    return {
        "Composition": Composition,
        "Structure": Structure,
        "Vasprun": Vasprun,
        "PDEntry": PDEntry,
        "PhaseDiagram": PhaseDiagram,
    }


def _read_target(args: argparse.Namespace, pmg: dict[str, Any]) -> tuple[Any, float | None]:
    Composition = pmg["Composition"]
    Structure = pmg["Structure"]
    Vasprun = pmg["Vasprun"]

    vasprun_energy: float | None = None
    if args.vasprun:
        vasprun = Vasprun(
            args.vasprun,
            parse_dos=False,
            parse_eigen=False,
            parse_projected_eigen=False,
        )
        composition = vasprun.final_structure.composition
        vasprun_energy = float(vasprun.final_energy)
    elif args.structure:
        composition = Structure.from_file(args.structure).composition
    elif args.formula:
        composition = Composition(args.formula)
    else:
        raise LocalMPError("calculate 需要 --formula、--structure 或 --vasprun。")

    if args.formula:
        requested = Composition(args.formula)
        if requested.reduced_composition != composition.reduced_composition:
            raise LocalMPError(
                f"--formula ({requested.reduced_formula}) 与结构中的成分 "
                f"({composition.reduced_formula}) 不一致。"
            )
    return composition, vasprun_energy


def _parse_element_references(values: list[str], pmg: dict[str, Any]) -> dict[str, float]:
    Composition = pmg["Composition"]
    references: dict[str, float] = {}
    for item in values:
        if "=" not in item:
            raise LocalMPError(
                f"元素参考能格式错误：{item!r}；正确格式示例为 Li=-1.90。"
            )
        symbol, raw_energy = item.split("=", maxsplit=1)
        symbol = symbol.strip()
        element_comp = Composition(symbol)
        if len(element_comp.elements) != 1 or element_comp.num_atoms != 1:
            raise LocalMPError(f"元素参考能左侧必须是元素符号：{symbol!r}")
        references[element_comp.elements[0].symbol] = _safe_float(
            raw_energy, f"{symbol} 参考能"
        )
    return references


def _target_formation_energy(
    args: argparse.Namespace,
    composition: Any,
    vasprun_energy: float | None,
    pmg: dict[str, Any],
) -> tuple[float, str]:
    if args.target_formation_energy_per_atom is not None:
        return (
            _safe_float(
                args.target_formation_energy_per_atom,
                "target_formation_energy_per_atom",
            ),
            "用户给定 formation_energy_per_atom",
        )

    total_energy = (
        _safe_float(args.target_total_energy, "target_total_energy")
        if args.target_total_energy is not None
        else vasprun_energy
    )
    if total_energy is None:
        raise LocalMPError(
            "请提供 --target-formation-energy-per-atom，或提供 "
            "--target-total-energy/--vasprun 以及每种元素的 --element-reference。"
        )

    references = _parse_element_references(args.element_reference, pmg)
    missing = sorted(
        element.symbol
        for element in composition.elements
        if element.symbol not in references
    )
    if missing:
        raise LocalMPError(f"缺少元素参考能：{', '.join(missing)}")

    reference_total = sum(
        amount * references[element.symbol]
        for element, amount in composition.items()
    )
    formation_energy = (total_energy - reference_total) / composition.num_atoms
    return formation_energy, "由总能和用户给定元素参考能计算"


def _build_reference_entries(
    source: Path, target_composition: Any, pmg: dict[str, Any]
) -> tuple[list[Any], int, str]:
    Composition = pmg["Composition"]
    PDEntry = pmg["PDEntry"]
    target_elements = {element.symbol for element in target_composition.elements}
    entries: list[Any] = []

    with open_csv_source(source) as (reader, _):
        fieldnames = list(reader.fieldnames or [])
        formula_column = _find_column(fieldnames, FORMULA_COLUMNS)
        energy_column = _find_column(fieldnames, FORMATION_ENERGY_COLUMNS)
        id_column = _find_column(fieldnames, ("material_id", "task_id", "entry_id"))

        if not formula_column:
            raise LocalMPError(
                f"参考数据缺少成分字段；现有字段：{', '.join(fieldnames)}"
            )
        if not energy_column:
            raise LocalMPError(
                "参考数据缺少 formation_energy_per_atom，无法重建凸包。"
                f"\n现有字段：{', '.join(fieldnames)}"
                "\n当前 mp.tar.gz 只能查询库中已有的 energy_above_hull。"
            )

        skipped = 0
        for row in reader:
            try:
                composition = Composition(row[formula_column])
                element_symbols = {element.symbol for element in composition.elements}
                if not element_symbols.issubset(target_elements):
                    continue
                energy_per_atom = float(row[energy_column])
                if not math.isfinite(energy_per_atom):
                    skipped += 1
                    continue
                entry_name = row.get(id_column) if id_column else None
                entries.append(
                    PDEntry(
                        composition,
                        energy_per_atom * composition.num_atoms,
                        name=entry_name,
                    )
                )
            except (TypeError, ValueError):
                skipped += 1

    # 形成能相图中，每种稳定单质的形成能定义为 0 eV/atom。
    for symbol in sorted(target_elements):
        element_composition = Composition(symbol)
        entries.append(PDEntry(element_composition, 0.0, name=f"{symbol}-reference"))

    return entries, skipped, energy_column


def command_calculate(args: argparse.Namespace) -> int:
    pmg = _import_pymatgen()
    composition, vasprun_energy = _read_target(args, pmg)
    target_formation_energy, energy_source = _target_formation_energy(
        args, composition, vasprun_energy, pmg
    )

    reference_source = Path(args.references)
    entries, skipped, energy_column = _build_reference_entries(
        reference_source, composition, pmg
    )
    PhaseDiagram = pmg["PhaseDiagram"]
    PDEntry = pmg["PDEntry"]

    phase_diagram = PhaseDiagram(entries)
    target_entry = PDEntry(
        composition,
        target_formation_energy * composition.num_atoms,
        name=args.target_name,
    )
    decomposition, signed_distance = phase_diagram.get_decomp_and_e_above_hull(
        target_entry, allow_negative=True
    )
    hull_energy = max(0.0, float(signed_distance))

    print(f"目标：{args.target_name}")
    print(f"成分：{composition.formula}")
    print(f"约化化学式：{composition.reduced_formula}")
    print(
        f"目标形成能：{target_formation_energy:.8f} eV/atom（{energy_source}）"
    )
    print(f"参考能字段：{energy_column}")
    print(f"参与相图的参考条目：{len(entries):,}")
    if skipped:
        print(f"跳过无效条目：{skipped:,}")
    print(f"凸包能：{hull_energy:.8f} eV/atom")
    print(f"凸包能：{hull_energy * 1000:.3f} meV/atom")
    if signed_distance < 0:
        print(
            f"说明：目标比当前本地凸包低 {-signed_distance * 1000:.3f} meV/atom；"
            "把目标加入相图后，它位于新凸包上，因此标准 E_hull 记为 0。"
        )

    print("竞争相分解：")
    decomposition_rows = []
    for entry, fraction in sorted(
        decomposition.items(), key=lambda item: item[1], reverse=True
    ):
        label = entry.name or entry.composition.reduced_formula
        fraction_value = float(fraction)
        decomposition_rows.append(
            {
                "name": label,
                "formula": entry.composition.reduced_formula,
                "fraction": fraction_value,
            }
        )
        print(
            f"  {label:<20} {entry.composition.reduced_formula:<15} "
            f"{fraction_value:.8f}"
        )

    if args.json_output:
        output_path = Path(args.json_output)
        result = {
            "target_name": args.target_name,
            "composition": composition.formula,
            "reduced_formula": composition.reduced_formula,
            "target_formation_energy_per_atom_eV": target_formation_energy,
            "energy_above_hull_eV_per_atom": hull_energy,
            "energy_above_hull_meV_per_atom": hull_energy * 1000,
            "signed_distance_to_old_hull_eV_per_atom": float(signed_distance),
            "reference_source": str(reference_source),
            "reference_energy_column": energy_column,
            "decomposition": decomposition_rows,
        }
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"JSON 结果：{output_path.resolve()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="读取本地 MP 数据并查询或计算能量高于凸包值。"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect", help="检查本地 MP 数据字段是否足够计算凸包。"
    )
    inspect_parser.add_argument(
        "--archive", default=str(DEFAULT_ARCHIVE), help="本地 CSV 或 MP 压缩包。"
    )
    inspect_parser.set_defaults(func=command_inspect)

    lookup_parser = subparsers.add_parser(
        "lookup", help="查询数据库已有记录的 energy_above_hull。"
    )
    lookup_parser.add_argument(
        "--archive", default=str(DEFAULT_ARCHIVE), help="本地 CSV 或 MP 压缩包。"
    )
    query_group = lookup_parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--material-id", help="例如 mp-985592。")
    query_group.add_argument("--formula", help="精确匹配 formula_pretty。")
    lookup_parser.set_defaults(func=command_lookup)

    calculate_parser = subparsers.add_parser(
        "calculate",
        help="用带 formation_energy_per_atom 的本地参考表重建凸包。",
    )
    calculate_parser.add_argument(
        "--references",
        default=str(DEFAULT_ARCHIVE),
        help="含 formation_energy_per_atom 的 CSV 或压缩包。",
    )
    target_group = calculate_parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--formula", help="目标化学式。")
    target_group.add_argument("--structure", help="目标 CIF/POSCAR/CONTCAR 路径。")
    target_group.add_argument("--vasprun", help="目标 vasprun.xml 路径。")
    calculate_parser.add_argument(
        "--target-name", default="new-material", help="目标材料名称。"
    )
    calculate_parser.add_argument(
        "--target-formation-energy-per-atom",
        type=float,
        help="与本地 MP 参考表口径一致的形成能，单位 eV/atom。",
    )
    calculate_parser.add_argument(
        "--target-total-energy",
        type=float,
        help="目标结构晶胞总能，单位 eV；需同时给元素参考能。",
    )
    calculate_parser.add_argument(
        "--element-reference",
        action="append",
        default=[],
        metavar="ELEMENT=EV",
        help="每个元素的参考能，例如 Li=-1.90；可重复使用。",
    )
    calculate_parser.add_argument(
        "--json-output", help="可选：保存结果 JSON 的路径。"
    )
    calculate_parser.set_defaults(func=command_calculate)
    return parser


def main() -> int:
    _configure_utf8_console()
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except LocalMPError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("已取消。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
