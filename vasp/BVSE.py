#使用方法
#1.install BVlain
#2.准备cif文件，以mp下载的cif文件格式为标准
#3.运行脚本
#4.获得输出的grd文件,cube文件。grd不包含原子，cube包含原子
#5.导入vesta进行可视化，等值面选择negative，数值小点，其中黄色部分代表通道

import os
from bvlain import Lain  # 从bvlain库导入Lain类
file = r'C:\Users\ZHANGJY02\PycharmProjects\PythonProject\CONTCAR_Bi3_CONTCAR_supercell.cif'  # 正确的结构文件路径
calc = Lain(verbose = True)        # 定义计算器对象，并设置为详细模式
calc.read_file(file) # 读取结构文件

# define params  # 定义参数
params = {
    'mobile_ion': 'Li1+',  # 移动离子类型为Li1+
    'r_cut': 10.0,          # 截断半径为10.0
    'resolution': 0.2,      # 分辨率为0.2
    'k': 100                # k值为100
    #'use_softbv_covalent_radii': False # default is False, use True to compare results with softBV
}

_ = calc.bvse_distribution(**params)
energies = calc.percolation_barriers(encut = 5.0)
for key in energies.keys():
    print(f'{key[-2:]} percolation barrier is {round(energies[key], 4)} eV')
#calc.write_grd(file + '_bvse', task = 'bvse')  # saves .grd file
calc.write_cube(file + '_bvse', task = 'bvse') # alternatively, save .cube file

###计算价态是否与设置的一致
#table = calc.mismatch(r_cut = 4.0)  # 计算失配表，截断半径为4.0
#print(table.to_string())  # 打印表格内容
####计算void
#_ = calc.void_distribution(**params)
#radii = calc.percolation_radii()
#for key in radii.keys():
#    print(f'{key[-2:]} percolation barrier is {round(radii[key], 4)} angstrom')
#calc.write_grd(file + '_void', task = 'void') # # save void distribution


