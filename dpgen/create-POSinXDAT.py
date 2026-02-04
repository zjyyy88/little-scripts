
# 导出XDTACAR中指定步数的结构为POSCAR

# 设置XDTACAR文件名、目标步数和导出的POSCAR文件名
xdatcar_file="XDATCAR" # XDTACAR文件路径
target_step=1000 # 替换为你要导出的优化步数
poscar_file=f"POSCAR_step_{target_step}"

# 打开XDTACAR文件进行读取
with open(xdatcar_file, "r") as xdatcar:
    lines = xdatcar.readlines()

# 获取步数和原子数
step_line = lines[0]
num_atoms_line = lines[6]

# 找到指定步数的结构
step_count = 0
structure_lines = []
for line in lines:
    if "Direct configuration=" in line:
        step_count += 1
    if step_count == target_step:
        structure_lines.append(line)

# 检查是否找到了目标步数
if step_count < target_step:
    print(f"Step {target_step} not found in XDTACAR.")
else:
    # 创建POSCAR文件
    with open(poscar_file, "w") as poscar:
        poscar.write("Generated from XDTACAR\n")
        #poscar.write("unknown system\n")
        poscar.write("           1\n")
    # 写入晶格向量
        poscar.write("    11.015389    0.000000    0.000000\n")
        poscar.write("     0.021129   11.656914    0.000000\n")
        poscar.write("     0.000000    0.000000   33.124638\n")
    # 写入原子类型和数量
        poscar.write("   Cl   Li   Y    H    O \n")
        poscar.write("    72    36    12    32    16\n")
        #poscar.write(step_line)
        #poscar.write(num_atoms_line)
        for line in structure_lines:
            poscar.write(line)

    print(f"POSCAR file for step {target_step} has been created: {poscar_file}")
