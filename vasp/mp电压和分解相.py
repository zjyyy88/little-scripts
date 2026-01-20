# vasp/plot_stability.py
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pymatgen.core import Composition
from pymatgen.analysis.phase_diagram import PhaseDiagram
from mp_api.client import MPRester

# ================= 配置区域 =================
# 输入你的材料和体系
API_KEY = "HiDNgsh0Zz5RnMjLIjH3HxfFjTwnRIgb"  # 你的 API Key
TARGET_FORMULA = "Li3YCl6"           # 目标材料
CHEMSYS = ["Li", "Y","Cl"]             # 包含的元素体系
LI_REF_ENERGY = -1.9089                       # Li 金属参考能量 (eV/atom)
# ===========================================

def get_plot_data():
    with MPRester(API_KEY) as mpr:
        print(f"正在获取 {CHEMSYS} 体系数据...")
        entries = mpr.get_entries_in_chemsys(CHEMSYS)
        
    pd = PhaseDiagram(entries)
    comp = Composition(TARGET_FORMULA)
    
    # 计算电压-组分曲线
    # get_element_profile 返回的是不同化学势下最稳定的相组合
    profile_data = pd.get_element_profile("Li", comp)
    
    return profile_data

def parse_reaction_phases(reaction):
    """解析反应产物，返回 {晶格公式: 摩尔分数} 的字典"""
    products = {}
    
    # 获取产物及其系数
    for prod in reaction.products:
        # 简化显示：取漂亮的公式
        formula = prod.reduced_formula
        # 获取该产物的系数
        coeff = reaction.get_coeff(prod)
        products[formula] = coeff
    return products

def plot_stability(profile_data):
    # 准备画布：左边是电压线，右边是相分布
    fig, (ax_vol, ax_phase) = plt.subplots(1, 2, figsize=(12, 6), gridspec_kw={'width_ratios': [2, 1]})
    plt.subplots_adjust(wspace=0.05)

    data_points = []
    
    # 提取数据
    for step in profile_data:
        voltage = -(step['chempot'] - LI_REF_ENERGY)
        uptake = step['evolution'] # Li 摄取量 (相对于原式)
        reaction = step['reaction']
        data_points.append({
            'v': voltage,
            'uptake': uptake,
            'reaction': reaction
        })

    # --- 1. 绘制电压曲线 (左图) ---
    # 按照电压从高到低排序 (通常 profile 也是这个顺序)
    data_points.sort(key=lambda x: x['v'], reverse=True)
    
    voltages = [d['v'] for d in data_points]
    uptakes = [d['uptake'] for d in data_points]
    
    # 使用 step 函数绘制阶梯图
    ax_vol.step(uptakes, voltages, where='post', color='k', linewidth=1.5)
    
    # 寻找稳定性窗口 (即 Uptake = 0 的区域)
    # 实际上可能是极小值，或者根据成分判断是否含目标材料
    '''
    win_start, win_end = None, None
    for i in range(len(uptakes)-1):
        if abs(uptakes[i]) < 1e-3: # Uptake 约为 0
            high_v = voltages[i]
            low_v = voltages[i+1]
            # 填充粉色区域
            rect = patches.Rectangle((min(uptakes)-0.5, low_v), max(uptakes)-min(uptakes)+1, high_v-low_v, 
                                     color='pink', alpha=0.2)
            ax_vol.add_patch(rect)
            
            # 标记红色稳定线
            ax_vol.plot([0, 0], [low_v, high_v], color='red', linewidth=3)
            
            # 添加文字标注
            ax_vol.text(0.1, (high_v+low_v)/2, f"Stability Window\n{low_v:.2f} V - {high_v:.2f} V", 
                        verticalalignment='center', fontsize=10)
            
            win_start, win_end = low_v, high_v
'''
    ax_vol.set_xlabel("Li uptake per f.u.")
    ax_vol.set_ylabel("Potential ref. to Li+/Li (V)")
    ax_vol.set_title("Electrochemical Stability Profile")
    ax_vol.grid(True, linestyle='--', alpha=0.5)
    ax_vol.set_xlim(min(uptakes)-0.5, max(uptakes)+0.5)

    # --- 2. 绘制相平衡 (右图) ---
    # 右图展示不同电压区间下的稳定相
    # 我们遍历每个电压台阶，绘制一个堆叠柱状图
    
    # Y轴与左图保持一致
    ax_phase.set_ylim(ax_vol.get_ylim())
    ax_phase.set_xlabel("Phase Equilibria")
    ax_phase.set_xticks([]) # 隐藏X轴刻度
    ax_phase.yaxis.tick_right() # Y轴刻度在右侧
    
    # 颜色池
    colors = plt.cm.tab20.colors
    ph_color_map = {}
    c_idx = 0

    for i in range(len(data_points)-1):
        # 当前区间的电压范围
        v_top = data_points[i]['v']
        v_bottom = data_points[i+1]['v']
        height = v_top - v_bottom
        mid_y = (v_top + v_bottom) / 2
        
        # 当前区间的产物
        products = parse_reaction_phases(data_points[i]['reaction']) # 使用高电位端的反应产物代表该区间
        
        # 归一化用于绘图宽度
        total_moles = sum(products.values())
        
        current_left = 0
        for formula, moles in products.items():
            width = moles / total_moles
            
            # 分配颜色
            if formula not in ph_color_map:
                ph_color_map[formula] = colors[c_idx % len(colors)]
                c_idx += 1
            
            # 画方块
            rect = patches.Rectangle((current_left, v_bottom), width, height, 
                                     facecolor=ph_color_map[formula], edgecolor='k', alpha=0.8)
            ax_phase.add_patch(rect)
            
            # 如果方块足够大，写上化学式
            if height > 0.2 and width > 0.2:
                ax_phase.text(current_left + width/2, mid_y, formula, 
                              ha='center', va='center', rotation=90 if width < 0.3 else 0, fontsize=8)
            
            current_left += width

    plt.tight_layout()
    plt.savefig('stability_profile.png', dpi=300)
    print("图表已保存为 stability_profile.png")
    plt.show()

if __name__ == "__main__":
    data = get_plot_data()
    plot_stability(data)