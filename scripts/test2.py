import os

from mp_api.client import MPRester
from pymatgen.electronic_structure.plotter import DosPlotter, BSPlotter
import matplotlib.pyplot as plt

# 设置matplotlib以避免字体报错（沿用之前的配置）
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False 

API_KEY = os.environ.get("MP_API_KEY")
if not API_KEY:
    raise RuntimeError("请先设置环境变量 MP_API_KEY。")

with MPRester(API_KEY) as m:
    material_id = "mp-1234" # LuN (Lutetium Nitride)

    # 1. 下载并保存晶体结构
    print(f"正在处理 {material_id} ...")
    structure = m.get_structure_by_material_id(material_id)
    # 保存为 CIF 文件
    cif_filename = f"{material_id}.cif"
    structure.to(filename=cif_filename)
    print(f"✅ 结构文件已保存到: {cif_filename}")

    # 2. 下载并保存 DOS (态密度) 图
    dos = m.get_dos_by_material_id(material_id)
    plotter = DosPlotter()
    plotter.add_dos("Total DOS", dos)
    plt = plotter.get_plot()
    plt.title(f"{material_id} DOS")
    plt.savefig(f"{material_id}_dos.png")
    print(f"✅ DOS图已保存到: {material_id}_dos.png")
    plt.close() # 关闭画布释放内存

    # 3. 下载并保存能带结构图
    bandstructure = m.get_bandstructure_by_material_id(material_id)
    bs_plotter = BSPlotter(bandstructure)
    plt = bs_plotter.get_plot(ylim=[-5, 5]) # 限制Y轴范围在 -5 到 5 eV 以便看清费米能级附近
    plt.title(f"{material_id} Band Structure")
    plt.savefig(f"{material_id}_band.png")
    print(f"✅ 能带图已保存到: {material_id}_band.png")
    plt.close()
