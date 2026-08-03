"""从 VASP AIMD 的 XDATCAR 生成迁移离子概率密度 CHGCAR。"""

from pathlib import Path

import numpy as np
from pymatgen.analysis.diffusion.aimd.pathway import ProbabilityDensityAnalysis
from pymatgen.io.vasp import Xdatcar


# ======================== 用户设置 ========================
MOBILE_ION = "Li"               # 迁移离子，例如 Li、Na、K、F
XDATCAR_FILE = "XDATCAR"        # XDATCAR 文件路径
STEP_SKIP = 1                   # 每隔多少个离子步读取一帧；1 表示全部
SKIP_INITIAL_FRAMES = 0         # 跳过开头的 N 帧（平衡阶段）
GRID_INTERVAL = 0.5             # 概率密度网格间距，单位 Å
OUTPUT_FILE = f"ProbabilityDensity_{MOBILE_ION}.vasp"
# =========================================================

xdatcar = Xdatcar(XDATCAR_FILE)
structures = xdatcar.structures[SKIP_INITIAL_FRAMES::STEP_SKIP]

if len(structures) == 0:
    raise ValueError("没有可分析的轨迹帧，请减小 SKIP_INITIAL_FRAMES。")

n_mobile = sum(site.specie.symbol == MOBILE_ION for site in structures[0])
if n_mobile == 0:
    raise ValueError(f"结构中没有找到迁移离子 {MOBILE_ION}。")

trajectories = np.array([s.frac_coords for s in structures])

density = ProbabilityDensityAnalysis(
    structures[0],
    trajectories,
    interval=GRID_INTERVAL,
    species=[MOBILE_ION],
)
density.to_chgcar(OUTPUT_FILE)

print(f"XDATCAR 读取总帧数: {len(xdatcar.structures)}")
print(f"使用轨迹帧数: {len(trajectories)}")
print(f"迁移离子: {MOBILE_ION}，离子数: {n_mobile}")
print(f"概率密度网格: {density.lens}")
print(f"输出文件: {Path(OUTPUT_FILE).resolve()}")
print("可使用 VESTA 打开输出文件并绘制等值面。")
