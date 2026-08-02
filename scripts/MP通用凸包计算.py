import os

from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition
from pymatgen.entries.compatibility import MaterialsProject2020Compatibility
from pymatgen.entries.computed_entries import ComputedEntry


# ======================== 只修改这里 ========================
API_KEY = os.environ.get("MP_API_KEY")
TARGET_FORMULA = "Li16B4P4Sb8F88"
TARGET_ENERGY = -923.0  # 一个 TARGET_FORMULA 对应的 VASP 总能量，eV

# 普通 GGA：
RUN_TYPE = "GGA"
HUBBARDS = {}

# GGA+U：需要时取消下面两行的注释，数值必须与 MPRelaxSet 一致。
# RUN_TYPE = "GGA+U"
# HUBBARDS = {"Fe": 5.3}
# O/F 环境下 MP 常用 U 值：
# Co 3.32, Cr 3.70, Fe 5.30, Mn 3.90,
# Mo 4.38, Ni 6.20, V 3.25, W 6.20 eV

# 默认自动判断氧化态；如需手动指定，取消对应字典的注释即可。
AUTO_GUESS_OXIDATION_STATES = True
# AUTO_GUESS_OXIDATION_STATES = False
ENTRY_DATA = {}
# ENTRY_DATA["oxidation_states"] = {
#     "Li": 1, "B": 3, "P": 5, "Sb": 5, "F": -1
# }
# 其他示例：
# ENTRY_DATA["oxidation_states"] = {"Fe": 3, "O": -2}

# 含氧体系可指定类型；四种选项为 oxide/peroxide/superoxide/ozonide。
# 不指定时，无结构信息的条目通常按普通 oxide 处理。
# ENTRY_DATA["oxide_type"] = "oxide"
# ENTRY_DATA["oxide_type"] = "peroxide"
# ENTRY_DATA["oxide_type"] = "superoxide"
# ENTRY_DATA["oxide_type"] = "ozonide"

# 含硫体系可明确指定；普通硫化物和多硫化物使用同一 MP2020 校正。
# ENTRY_DATA["sulfide_type"] = "sulfide"
# ENTRY_DATA["sulfide_type"] = "polysulfide"

# 只有提供了完整 POTCAR 元数据时才打开检查；这项是检查，不是能量校正。
CHECK_POTCAR = False
# CHECK_POTCAR = True
# ===========================================================

if not API_KEY:
    raise RuntimeError("请先设置环境变量 MP_API_KEY。")


composition = Composition(TARGET_FORMULA)
elements = [element.symbol for element in composition.elements]

if AUTO_GUESS_OXIDATION_STATES and "oxidation_states" not in ENTRY_DATA:
    oxidation_state_guesses = composition.oxi_state_guesses()
    if oxidation_state_guesses:
        ENTRY_DATA["oxidation_states"] = oxidation_state_guesses[0]

# MP 的 GGA/GGA+U 相图条目已经施加 MP2020 兼容性校正。
with MPRester(API_KEY) as mpr:
    mp_entries = mpr.get_entries_in_chemsys(
        elements,
        compatible_only=True,
        additional_criteria={"thermo_types": ["GGA_GGA+U"]},
    )

parameters = {
    "run_type": RUN_TYPE,
    "hubbards": HUBBARDS,
}

# 如果要启用 POTCAR 检查，还需填入本次计算实际使用的 POTCAR 标题。
# parameters["potcar_symbols"] = [
#     "PAW_PBE Fe_pv 06Sep2000",
#     "PAW_PBE O 08Apr2002",
# ]

target_entry = ComputedEntry(
    composition=composition,
    energy=TARGET_ENERGY,
    parameters=parameters,
    data=ENTRY_DATA,
    entry_id="target",
)

# Advanced 会自动处理：
# 1. GGA/GGA+U 混合校正；
# 2. O、S、F、Cl、Br、I、N、Se、Si、Sb、Te、H 等组成校正；
# 3. oxide/peroxide/superoxide/ozonide 类型校正。
compatibility = MaterialsProject2020Compatibility(
    compat_type="Advanced",
    correct_peroxide=True,
    strict_anions="require_bound",
    check_potcar=CHECK_POTCAR,
)
target_entry = compatibility.process_entry(target_entry)

if target_entry is None:
    raise ValueError(
        "目标条目未通过 MP2020 检查。请检查 RUN_TYPE、HUBBARDS 和 POTCAR 设置。"
    )

# 以 MP 现有条目为参考凸包，得到竞争相和目标材料相对凸包的能量差。
phase_diagram = PhaseDiagram(mp_entries)
decomposition, energy_difference = phase_diagram.get_decomp_and_e_above_hull(
    target_entry,
    allow_negative=True,
)
energy_above_hull = max(energy_difference, 0.0)

print(f"MP 条目数: {len(mp_entries)}")
print(f"目标材料: {TARGET_FORMULA}")
print(f"计算类型: {RUN_TYPE}")
print(f"原始总能量: {TARGET_ENERGY:.6f} eV")
print(f"MP2020 校正后总能量: {target_entry.energy:.6f} eV")

print("\n目标条目采用的校正:")
if target_entry.energy_adjustments:
    for adjustment in target_entry.energy_adjustments:
        print(f"  {adjustment.name}: {adjustment.value:+.6f} eV")
else:
    print("  无")

print(f"\nEnergy above hull: {energy_above_hull:.6f} eV/atom")
if energy_difference < 0:
    print(f"目标材料比当前 MP 凸包低 {-energy_difference:.6f} eV/atom。")

print("\n竞争分解相（原子分数）:")
for entry, fraction in decomposition.items():
    material_id = entry.entry_id or "无 material_id"
    print(
        f"  {entry.composition.reduced_formula:<16}"
        f"{fraction:>10.6f}    {material_id}"
    )
