"""从 VASP AIMD 的 vasprun.xml 生成迁移离子概率密度 CHGCAR。"""

# 依赖安装：pip install pymatgen pymatgen-analysis-diffusion

from pathlib import Path

import numpy as np
from pymatgen.analysis.diffusion.aimd.pathway import ProbabilityDensityAnalysis
from pymatgen.analysis.diffusion.analyzer import DiffusionAnalyzer


# ======================== 用户设置 ========================
MOBILE_ION = "Li"               # 迁移离子，例如 Li、Na、K、F
VASPRUN_FILES = ["vasprun.xml"]  # 多段连续 AIMD 时按时间顺序填写
# VASPRUN_FILES = ["run1/vasprun.xml", "run2/vasprun.xml"]
# VASPRUN_FILES = sorted(str(p) for p in Path(".").glob("run*/vasprun.xml"))

STEP_SKIP = 10             # 每隔多少个离子步读取一帧；1 表示读取全部
SKIP_INITIAL_FRAMES = 0    # 丢弃平衡阶段；这里指抽样后的帧数
GRID_INTERVAL = 0.3        # 概率密度网格间距，单位 Å；越小越精细、越慢
OUTPUT_FILE = f"ProbabilityDensity_{MOBILE_ION}.vasp"
# =========================================================


files = [str(Path(path)) for path in VASPRUN_FILES]
missing = [path for path in files if not Path(path).is_file()]
if missing:
    raise FileNotFoundError(f"未找到 vasprun.xml：{missing}")

# smoothed=False 可避免短轨迹因 MSD 数据不足而报错；概率密度不需要 MSD 拟合。
analyzer = DiffusionAnalyzer.from_files(
    files,
    specie=MOBILE_ION,
    step_skip=STEP_SKIP,
    smoothed=False,
)
n_mobile = sum(
    site.specie.symbol == MOBILE_ION for site in analyzer.structure
)
if n_mobile == 0:
    raise ValueError(f"结构中没有找到迁移离子 {MOBILE_ION}。")

# 使用框架漂移校正后的轨迹，并可跳过前面的平衡帧。
structures = analyzer.get_drift_corrected_structures(start=SKIP_INITIAL_FRAMES)
trajectories = np.array([structure.frac_coords for structure in structures])
if len(trajectories) == 0:
    raise ValueError("没有可分析的轨迹帧，请减小 SKIP_INITIAL_FRAMES。")

density = ProbabilityDensityAnalysis(
    analyzer.structure,
    trajectories,
    interval=GRID_INTERVAL,
    species=[MOBILE_ION],
)
density.to_chgcar(OUTPUT_FILE)

print(f"输入文件数: {len(files)}")
print(f"使用轨迹帧数: {len(trajectories)}")
print(f"迁移离子: {MOBILE_ION}，离子数: {n_mobile}")
print(f"概率密度网格: {density.lens}")
print(f"输出文件: {Path(OUTPUT_FILE).resolve()}")
print("可使用 VESTA 打开输出文件并绘制等值面。")
