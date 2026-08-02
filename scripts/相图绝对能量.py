import os

from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition
from pymatgen.entries.compatibility import MaterialsProject2020Compatibility
from pymatgen.entries.computed_entries import ComputedEntry


API_KEY = os.environ.get("MP_API_KEY")
TARGET_FORMULA = "Li5B1P1Sb1F24O8S4N2C2"
TARGET_ENERGY = -346.5  # VASP 总能量，eV

if not API_KEY:
    raise RuntimeError("请先设置环境变量 MP_API_KEY。")

composition = Composition(TARGET_FORMULA)
elements = [element.symbol for element in composition.elements]

# 获取 Li-B-P-Sb-F 体系及其所有子体系的 MP GGA/GGA+U 条目。
# compatible_only=True 返回经过 MP2020 能量校正、可用于相图的条目。
with MPRester(API_KEY) as mpr:
    mp_entries = mpr.get_entries_in_chemsys(
        elements,
        compatible_only=True,
        additional_criteria={"thermo_types": ["GGA_GGA+U"]},
    )

# 目标能量来自与 MP 一致的 GGA 和 POTCAR，因此施加同一套 MP2020 校正。
target_entry = ComputedEntry(
    composition,
    TARGET_ENERGY,
    parameters={"run_type": "GGA", "hubbards": {}},
    data={
        "oxidation_states": {
            "Li": 1,
            "B": 3,
            "P": 5,
            "Sb": 5,
            "F": -1,
            "O": -2,
            "S": +6,
            "N": -3,
            "C": +2,
        }
    },
    entry_id="target",
)
target_entry = MaterialsProject2020Compatibility(
    check_potcar=False
).process_entry(target_entry)

if target_entry is None:
    raise ValueError("目标条目未通过 Materials Project 兼容性检查。")

# 用 MP 已有条目建立参考凸包，并计算目标材料相对于该凸包的分解。
phase_diagram = PhaseDiagram(mp_entries)
decomposition, energy_difference = phase_diagram.get_decomp_and_e_above_hull(
    target_entry,
    allow_negative=True,
)
energy_above_hull = max(energy_difference, 0.0)

print(f"MP 条目数: {len(mp_entries)}")
print(f"目标材料: {TARGET_FORMULA}")
print(f"原始总能量: {TARGET_ENERGY:.6f} eV")
print(f"MP2020 校正后总能量: {target_entry.energy:.6f} eV")
print(f"Energy above hull: {energy_above_hull:.6f} eV/atom")

if energy_difference < 0:
    print(f"目标材料比当前 MP 凸包低 {-energy_difference:.6f} eV/atom。")

print("竞争分解相（原子分数）:")
for entry, fraction in decomposition.items():
    material_id = entry.entry_id or "无 material_id"
    print(
        f"  {entry.composition.reduced_formula:<16}"
        f"{fraction:>10.6f}    {material_id}"
    )
formation_energy = phase_diagram.get_form_energy(target_entry)
formation_energy_per_atom = phase_diagram.get_form_energy_per_atom(target_entry)

print(f"形成能: {formation_energy:.6f} eV/化学式")
print(f"形成能: {formation_energy_per_atom:.6f} eV/atom")
