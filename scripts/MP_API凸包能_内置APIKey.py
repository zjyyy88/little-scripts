#!/usr/bin/env python
"""
通过 Materials Project API 计算自定义材料的 0 K 能量高于凸包值。

推荐模式（可验证计算参数）：
  python MP_API凸包能.py --vasprun D:\\calc\\vasprun.xml

筛选模式（只有化学式和总能量，无法验证 POTCAR/INCAR）：
  python MP_API凸包能.py --formula Li4SbB2PF24 --total-energy -259 ^
      --assume-mp-compatible

请把 API key 直接填写到下方 SCRIPT_MP_API_KEY 常量中。
也可以用 --api-key 临时覆盖脚本内的值。

科学前提：
  自定义 VASP 计算必须使用与 Materials Project 兼容的计算设置。
  只提供化学式和绝对总能量时，脚本只能做筛选，不能验证能量零点。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from monty.serialization import dumpfn, loadfn
from mp_api.client import MPRester
from pymatgen.analysis.compatibility import MaterialsProject2020Compatibility
from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition
from pymatgen.core.entries import ComputedEntry
from pymatgen.io.vasp.outputs import Vasprun


NEGATIVE_DISTANCE_WARNING_EV_PER_ATOM = -0.10

# 在下面的引号中填写你的 Materials Project API key。
SCRIPT_MP_API_KEY = "PASTE_YOUR_MATERIALS_PROJECT_API_KEY_HERE"


class HullCalculationError(RuntimeError):
    """适合直接展示的输入、API 或兼容性错误。"""


def configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def parse_oxidation_states(values: list[str]) -> dict[str, float]:
    oxidation_states: dict[str, float] = {}
    for item in values:
        if "=" not in item:
            raise HullCalculationError(
                f"氧化态格式错误：{item!r}；正确示例为 F=-1。"
            )
        symbol, raw_value = item.split("=", maxsplit=1)
        symbol = symbol.strip()
        try:
            element_comp = Composition(symbol)
            value = float(raw_value)
        except (ValueError, TypeError) as exc:
            raise HullCalculationError(f"无效氧化态：{item!r}") from exc
        if len(element_comp.elements) != 1 or element_comp.num_atoms != 1:
            raise HullCalculationError(f"无效元素符号：{symbol!r}")
        if not math.isfinite(value):
            raise HullCalculationError(f"氧化态必须是有限数值：{item!r}")
        oxidation_states[element_comp.elements[0].symbol] = value
    return oxidation_states


def build_target_entry(args: argparse.Namespace) -> tuple[Any, str, list[str]]:
    warnings: list[str] = []

    if args.vasprun:
        vasprun_path = Path(args.vasprun)
        if not vasprun_path.exists():
            raise HullCalculationError(f"vasprun.xml 不存在：{vasprun_path}")
        vasprun = Vasprun(
            vasprun_path,
            parse_dos=False,
            parse_eigen=False,
            parse_projected_eigen=False,
        )
        raw_entry = vasprun.get_computed_entry(
            inc_structure=True, entry_id=args.target_name
        )
        check_potcar = not args.skip_potcar_check
        source_description = f"vasprun.xml：{vasprun_path}"
        if args.skip_potcar_check:
            warnings.append("已跳过 POTCAR 一致性检查。")
    else:
        if args.total_energy is None:
            raise HullCalculationError("--formula 必须同时提供 --total-energy。")
        if not args.assume_mp_compatible:
            raise HullCalculationError(
                "只有化学式和总能量时无法验证 POTCAR/INCAR。"
                "若确认该能量来自 MP 兼容的 VASP 设置，请添加 "
                "--assume-mp-compatible。"
            )
        composition = Composition(args.formula)
        raw_entry = ComputedEntry(
            composition=composition,
            energy=args.total_energy,
            parameters={"run_type": args.run_type},
            entry_id=args.target_name,
        )
        check_potcar = False
        source_description = "化学式 + 总能量（筛选模式）"
        warnings.append(
            "未验证 POTCAR、ENCUT、KPOINTS、Hubbard U 和实际晶胞组成；"
            "结果仅在输入能量确实与 MP 同口径时有效。"
        )

    oxidation_states = parse_oxidation_states(args.oxidation_state)
    if oxidation_states:
        raw_entry.data["oxidation_states"] = oxidation_states

    compatibility = MaterialsProject2020Compatibility(check_potcar=check_potcar)
    try:
        processed_entry = compatibility.process_entry(raw_entry)
    except Exception as exc:
        raise HullCalculationError(
            "目标条目未能通过 MaterialsProject2020Compatibility："
            f"{exc}"
        ) from exc

    if processed_entry is None:
        raise HullCalculationError(
            "目标条目被 MaterialsProject2020Compatibility 拒绝。"
            "请检查 VASP 设置、POTCAR 和 Hubbard U 参数。"
        )
    return processed_entry, source_description, warnings


def chemical_system(composition: Composition) -> list[str]:
    return sorted(element.symbol for element in composition.elements)


def load_or_download_entries(
    elements: list[str], args: argparse.Namespace
) -> tuple[list[Any], str]:
    cache_path = Path(args.cache) if args.cache else None
    if cache_path and cache_path.exists() and not args.refresh_cache:
        entries = loadfn(cache_path)
        if not isinstance(entries, list):
            raise HullCalculationError(f"缓存不是条目列表：{cache_path}")
        return entries, f"本地缓存：{cache_path}"

    api_key = args.api_key or SCRIPT_MP_API_KEY.strip()
    if (
        not api_key
        or api_key == "PASTE_YOUR_MATERIALS_PROJECT_API_KEY_HERE"
    ):
        raise HullCalculationError(
            "尚未填写 API key。请在脚本开头设置 SCRIPT_MP_API_KEY。"
        )
    try:
        with MPRester(api_key) as mpr:
            entries = mpr.get_entries_in_chemsys(
                elements=elements,
                additional_criteria={"thermo_types": ["GGA_GGA+U"]},
            )
    except Exception as exc:
        raise HullCalculationError(f"Materials Project API 请求失败：{exc}") from exc

    if not entries:
        raise HullCalculationError(
            f"API 未返回 {'-'.join(elements)} 体系的热力学条目。"
        )

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        dumpfn(entries, cache_path)
        return entries, f"MP API；已缓存到：{cache_path}"
    return entries, "Materials Project API"


def format_number(value: float) -> str:
    rounded = round(value)
    if abs(value - rounded) < 1e-8:
        return str(int(rounded))
    return f"{value:.8g}"


def decomposition_reaction(
    target_composition: Composition, decomposition: dict[Any, float]
) -> str:
    products: list[str] = []
    for entry, atom_fraction in sorted(
        decomposition.items(), key=lambda item: item[1], reverse=True
    ):
        coefficient = (
            target_composition.num_atoms
            * float(atom_fraction)
            / entry.composition.num_atoms
        )
        coefficient_text = "" if abs(coefficient - 1) < 1e-8 else (
            f"{format_number(coefficient)} "
        )
        products.append(
            f"{coefficient_text}{entry.composition.reduced_formula}"
        )
    return f"{target_composition.formula} -> " + " + ".join(products)


def calculate(args: argparse.Namespace) -> dict[str, Any]:
    target_entry, target_source, warnings = build_target_entry(args)
    elements = chemical_system(target_entry.composition)
    entries, reference_source = load_or_download_entries(elements, args)

    phase_diagram = PhaseDiagram(entries)
    decomposition, signed_distance = phase_diagram.get_decomp_and_e_above_hull(
        target_entry, allow_negative=True
    )
    signed_distance = float(signed_distance)
    energy_above_hull = max(0.0, signed_distance)

    if signed_distance < NEGATIVE_DISTANCE_WARNING_EV_PER_ATOM:
        warnings.append(
            "目标能量显著低于现有 MP 凸包。大幅负值通常意味着总能量归一化、"
            "POTCAR、泛函、U 值或能量修正口径不一致；此时不能把 0 eV/atom "
            "直接解释为可靠的热力学稳定性。"
        )

    decomposition_rows: list[dict[str, Any]] = []
    for entry, atom_fraction in sorted(
        decomposition.items(), key=lambda item: item[1], reverse=True
    ):
        atom_fraction = float(atom_fraction)
        formula_units = (
            target_entry.composition.num_atoms
            * atom_fraction
            / entry.composition.num_atoms
        )
        decomposition_rows.append(
            {
                "formula": entry.composition.reduced_formula,
                "entry_id": str(entry.entry_id),
                "atom_fraction": atom_fraction,
                "formula_units_per_target_cell": formula_units,
            }
        )

    result = {
        "target_name": args.target_name,
        "target_source": target_source,
        "composition": target_entry.composition.formula,
        "reduced_formula": target_entry.composition.reduced_formula,
        "chemical_system": "-".join(elements),
        "number_of_atoms": float(target_entry.composition.num_atoms),
        "uncorrected_total_energy_eV": float(target_entry.uncorrected_energy),
        "correction_total_eV": float(target_entry.correction),
        "corrected_total_energy_eV": float(target_entry.energy),
        "corrected_energy_per_atom_eV": float(target_entry.energy_per_atom),
        "reference_source": reference_source,
        "reference_entry_count": len(entries),
        "signed_distance_to_old_hull_eV_per_atom": signed_distance,
        "energy_above_hull_eV_per_atom": energy_above_hull,
        "energy_above_hull_meV_per_atom": energy_above_hull * 1000,
        "decomposition_reaction": decomposition_reaction(
            target_entry.composition, decomposition
        ),
        "decomposition": decomposition_rows,
        "warnings": warnings,
    }
    return result


def print_result(result: dict[str, Any]) -> None:
    print("=" * 72)
    print("Materials Project API 凸包能结果")
    print("=" * 72)
    print(f"目标名称：{result['target_name']}")
    print(f"输入来源：{result['target_source']}")
    print(f"化学式：{result['composition']}")
    print(f"约化式：{result['reduced_formula']}")
    print(f"化学体系：{result['chemical_system']}")
    print(f"原子数：{format_number(result['number_of_atoms'])}")
    print(f"MP 参考条目：{result['reference_entry_count']}")
    print(f"参考来源：{result['reference_source']}")
    print("-" * 72)
    print(
        f"未修正总能：{result['uncorrected_total_energy_eV']:.10f} eV"
    )
    print(f"总修正：{result['correction_total_eV']:.10f} eV")
    print(f"修正后总能：{result['corrected_total_energy_eV']:.10f} eV")
    print(
        f"修正后单原子能："
        f"{result['corrected_energy_per_atom_eV']:.10f} eV/atom"
    )
    print("-" * 72)
    print(
        f"E_hull：{result['energy_above_hull_eV_per_atom']:.10f} eV/atom"
    )
    print(
        f"E_hull：{result['energy_above_hull_meV_per_atom']:.3f} meV/atom"
    )
    print(
        "相对原 MP 凸包的有符号距离："
        f"{result['signed_distance_to_old_hull_eV_per_atom']:.10f} eV/atom"
    )
    print(f"分解反应：{result['decomposition_reaction']}")
    print("分解条目：")
    for item in result["decomposition"]:
        print(
            f"  {item['formula']:<16} "
            f"原子分数={item['atom_fraction']:.8f}  "
            f"目标晶胞计量数={item['formula_units_per_target_cell']:.8f}  "
            f"ID={item['entry_id']}"
        )

    if result["warnings"]:
        print("-" * 72)
        print("警告：")
        for warning in result["warnings"]:
            print(f"  - {warning}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="通过 MP API 和 pymatgen 计算自定义材料的 0 K 凸包能。"
    )
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--vasprun", help="推荐：自定义材料的 vasprun.xml 路径。"
    )
    target_group.add_argument(
        "--formula", help="筛选模式：目标化学式，例如 Li4SbB2PF24。"
    )
    parser.add_argument(
        "--total-energy",
        type=float,
        help="筛选模式下该化学式/晶胞的 VASP 总能量，单位 eV。",
    )
    parser.add_argument(
        "--run-type",
        default="GGA",
        choices=("GGA", "GGA+U"),
        help="筛选模式的计算类型，默认 GGA。",
    )
    parser.add_argument(
        "--assume-mp-compatible",
        action="store_true",
        help="确认化学式+总能量来自 MP 兼容设置，并接受无法验证的风险。",
    )
    parser.add_argument(
        "--skip-potcar-check",
        action="store_true",
        help="vasprun 模式下跳过 POTCAR 检查，不建议。",
    )
    parser.add_argument(
        "--oxidation-state",
        action="append",
        default=[],
        metavar="ELEMENT=VALUE",
        help="指定元素氧化态，例如 F=-1；可重复使用。",
    )
    parser.add_argument(
        "--target-name", default="user-material", help="目标材料名称。"
    )
    parser.add_argument(
        "--api-key",
        help="临时覆盖脚本开头的 SCRIPT_MP_API_KEY。",
    )
    parser.add_argument(
        "--cache",
        help="可选：MP 条目缓存路径，推荐扩展名 .json.gz。",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="忽略已有缓存，重新调用 API。",
    )
    parser.add_argument("--json-output", help="可选：保存完整结果 JSON。")
    return parser


def main() -> int:
    configure_utf8_console()
    parser = build_parser()
    args = parser.parse_args()

    try:
        result = calculate(args)
        print_result(result)
        if args.json_output:
            output_path = Path(args.json_output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"JSON 结果：{output_path.resolve()}")
        return 0
    except HullCalculationError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("已取消。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
