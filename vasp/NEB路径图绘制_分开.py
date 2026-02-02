"""
NEB路径图绘制脚本 - 分别绘制
将每条路径单独绘制保存，保持格式一致
需要安装 scipy: pip install scipy
"""
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import make_interp_spline, PchipInterpolator
import os

# ========== 字体与画板设置 (保持一致) ==========
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 25
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['axes.linewidth'] = 2  # 边框线宽

# ========== 数据输入区域 ==========
# 格式：{"label": "图例名称", "path": [X轴数据], "energy": [Y轴数据], "color": "颜色"}
# Path单位: Å, Energy单位: eV
data_series = [
    {
        "label": "LIC-(010)",
        "path": [0,
1.535678,
3.082381,
4.631845,
6.182503,
7.785816,
9.390555
],
        "energy": [0,
0.242327,
1.029873,
1.043207,
1.10192,
0.852427,
0.757836
],
        "color": "#000000"  # 绿色
    },
    {
        "label": "LIC-(100)",
        "path": [0,
1.968828,
3.946596,
5.940495,
6.992419,
8.040221,
9.094222,
10.153316,
11.213531
],
        "energy": [0,
0.446439,
1.629186,
1.705579,
1.602869,
1.452311,
1.346175,
1.218241,
1.118222
],
        "color": "#000000"  # 蓝色
    },
    {
        "label": "LIC-(111)",
        "path": [0,
2.364445,
4.735183,
7.114062,
9.802582,
12.489717,
15.164532,
17.806101,
20.43837
],
        "energy": [0,
0.10539,
0.580384,
1.441407,
1.380191,
1.302513,
1.367787,
1.20205,
0.985534
],
        "color": "#000000"  # 黄色
    },
{
        "label": "LYC-(100)",
        "path": [0,
1.460879,
2.934589,
4.418548,
5.925095,
7.438555,
8.966643,
10.065929,
11.189216

],
        "energy": [0,
0.039012,
0.232215,
0.257244,
0.601004,
1.11186,
1.300753,
1.27792,
1.418234

],
        "color": "#000000"  # 黄色
    },
{
        "label": "LYC-(100)",
        "path": [0,
1.460879,
2.934589,
4.418548,
5.925095,
7.438555,
8.966643,
10.065929,
11.189216

],
        "energy": [0,
0.039012,
0.232215,
0.257244,
0.601004,
1.11186,
1.300753,
1.27792,
1.418234

],
        "color": "#000000"  # 黄色
    },
{
        "label": "LYC-(110)",
        "path": [0,
1.137448,
2.289633,
3.457489,
4.652989,
5.858667,
6.682415,
7.51805,
8.366015


],
        "energy": [0,
0.114368,
0.613154,
0.704762,
0.760001,
1.0555,
1.020874,
0.935051,
0.972306
],
        "color": "#000000"  # 黄色
    }]

# 额外标注文本
#inner_text = "1H2O" # 图内的文字
#title_text = "(a)"  # 图左上角的编号

# ========== 绘图逻辑 ==========

# 遍历绘制每一条路径，分别保存
for idx, series in enumerate(data_series):
    # 为每张图创建一个新的画布
    fig, ax = plt.subplots(figsize=(10, 8))
    # 调整边距
    plt.subplots_adjust(left=0.15, right=0.95, top=0.9, bottom=0.15)
    
    x = np.array(series["path"])
    y = np.array(series["energy"])
    label = series["label"]
    color = series["color"]
    
    # 1. 绘制散点 (实心点)
    ax.scatter(x, y, color=color, s=120, zorder=5) 

    # 标注最高点（能垒）
    max_idx = np.argmax(y)
    max_energy = y[max_idx]
    max_path = x[max_idx]
    ax.text(max_path , max_energy + 0.05, f"{max_energy:.2f} eV", 
            ha='center', va='bottom', fontsize=30, fontweight='bold', color=color, zorder=6)
    
    # 2. 绘制平滑曲线
    # 使用 PchipInterpolator 可以避免插值产生的过冲（凹点），保持单调区间内的单调性，更适合NEB路径
    try:
        x_smooth = np.linspace(x.min(), x.max(), 300)
        # model = make_interp_spline(x, y, k=3) # 原来的高阶样条插值容易产生不必要的震荡
        model = PchipInterpolator(x, y) 
        y_smooth = model(x_smooth)
        ax.plot(x_smooth, y_smooth, color=color, linewidth=3, label=label, zorder=4)
    except Exception as e:
        print(f"插值失败 ({label}): {e}, 使用直接连线代替")
        ax.plot(x, y, color=color, linewidth=3, label=label, zorder=4)

    # ========== 装饰与布局 (对每张图分别设置) ==========
    
    # 坐标轴标签 (粗体)
    ax.set_xlabel("Reaction Path (Å)", fontsize=30, fontweight='bold')
    ax.set_ylabel("Relative Energy (eV)", fontsize=30, fontweight='bold')

    # 坐标轴刻度设置
    ax.tick_params(axis='both', which='major', labelsize=25, width=2, length=6)

    # 设置Y轴范围和刻度 (保持统一，方便对比)
    ax.set_ylim(-0.2, 2.0)
    ax.set_yticks(np.arange(0, 2.1, 0.5))

    # 设置X轴范围 (可以根据需要统一或自适应，这里暂时保持统一以便对比)
    #ax.set_xlim(-0.1, 21)
    
    ax.tick_params(top=False, right=False)
    
    # 设置刻度标签为粗体
    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontweight('bold')

    # 图例
    legend = ax.legend(loc='lower right', frameon=False, fontsize=30, handletextpad=0.4)
    for text in legend.get_texts():
        text.set_fontweight('bold')

    # 添加左上角内部文字
    #ax.text(0.04, 0.96, inner_text, transform=ax.transAxes, 
    #        fontsize=25, fontweight='bold', va='top', ha='left')

    # 添加左上角外部标题
    #ax.text(-0.12, 1.0, title_text, transform=ax.transAxes, 
    #        fontsize=35, fontweight='bold', va='bottom', ha='right')

    # 保存文件
    # 文件名不包含非法字符
    safe_label = label.replace("(", "").replace(")", "").replace(" ", "_")
    output_name = f"neb_path_diagram_{safe_label}.png"
    plt.savefig(output_name, dpi=600, bbox_inches='tight')
    
    # 清理画布，防止内存堆积（虽然在循环末尾通常不是大问题，但这里有多个figure）
    plt.close(fig) 
    
    print(f"图片已保存为 {output_name}")
