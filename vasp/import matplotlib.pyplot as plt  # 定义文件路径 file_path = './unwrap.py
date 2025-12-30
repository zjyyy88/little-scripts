import numpy as np
from copy import deepcopy

# 打开文件
xdatcar = open('XDATCAR', 'r')
xyz = open('XDATCAR.xyz', 'w')

# 读取初始系统信息（只需要读取一次，后续构型的重复信息会被跳过）
system = xdatcar.readline().strip()  # 系统名称："unknown system"
scale = float(xdatcar.readline().strip())  # 缩放因子：1.0
print(f"Scale factor: {scale}")

# 读取晶格向量（3行）
a1 = np.array([float(s) * scale for s in xdatcar.readline().strip().split()])
a2 = np.array([float(s) * scale for s in xdatcar.readline().strip().split()])
a3 = np.array([float(s) * scale for s in xdatcar.readline().strip().split()])

# 构建XYZ文件的晶格注释
comment = f'Lattice="{a1[0]} {a1[1]} {a1[2]} {a2[0]} {a2[1]} {a2[2]} {a3[0]} {a3[1]} {a3[2]}"'

# 读取元素名称和原子数（只需要一次）
element_names = xdatcar.readline().strip().split()  # 元素：["Li", "Y", "Cl"]
element_numbers = list(map(int, xdatcar.readline().strip().split()))  # 原子数：[9, 3, 18]
print(f"Element names: {element_names}")
print(f"Element numbers: {element_numbers}")

# 计算总原子数并生成原子名称列表（按顺序对应每个原子）
Natom = sum(element_numbers)
Nname = []
for t in range(len(element_names)):
    Nname.extend([element_names[t]] * element_numbers[t])  # 例如：["Li"]*9 + ["Y"]*3 + ["Cl"]*18
print(f"Total atoms: {Natom}")

# 初始化坐标存储（用于处理周期性边界条件）
f_prev = np.zeros([Natom, 3])
f_next = np.zeros([Natom, 3])
config_counter = 0

# 函数：跳过每个构型前的重复系统信息（共8行）
def skip_repeated_header(file):
    # 每个构型前的重复信息包括：
    # 1. 系统名称行（unknown system）
    # 2. 缩放因子行（1）
    # 3-5. 晶格向量（3行）
    # 6. 元素名称行（Li Y Cl）
    # 7. 元素数量行（9 3 18）
    # （可能存在空行，所以用循环跳过非"configuration"的行）
    for _ in range(8):  # 最多跳过8行（覆盖上述所有重复信息）
        line = file.readline()
        if not line:  # 文件结束
            return False
        if "configuration" in line.lower():  # 提前遇到构型行，退出
            file.seek(file.tell() - len(line))  # 回退指针，保留构型行
            return True
    # 跳过8行后，检查下一行是否为构型行
    line = file.readline()
    if not line:
        return False
    if "configuration" in line.lower():
        file.seek(file.tell() - len(line))
        return True
    else:
        return False  # 未找到构型行

# 主循环：处理所有构型
while True:
    # 跳过当前构型前的重复系统信息
    if not skip_repeated_header(xdatcar):
        break  # 所有构型处理完毕
    
    # 读取构型标题行（如"Direct configuration= 1"）
    config_line = xdatcar.readline().strip()
    if "configuration" not in config_line.lower():
        print(f"Warning: Unexpected line instead of configuration header: {config_line}")
        continue
    config_counter += 1
    print(f"Processing configuration {config_counter}")
    
    # 写入XYZ文件的头部（原子数 + 晶格注释）
    xyz.write(f"{Natom}\n{comment}\n")
    
    # 读取当前构型的所有原子坐标
    for atom in range(Natom):
        line = xdatcar.readline()
        if not line:
            print(f"Error: Unexpected end of file while reading atom {atom+1} in configuration {config_counter}")
            exit(1)
        line = line.strip()
        if not line:  # 跳过空行
            line = xdatcar.readline().strip()
        p = line.split()
        # 验证坐标格式（3个数值）
        if len(p) != 3:
            print(f"Error: Invalid coordinate line for atom {atom+1} in configuration {config_counter}")
            print(f"Line content: {p}")
            exit(1)
        # 转换坐标为浮点数
        try:
            f_next[atom, :] = np.array([float(s) for s in p])
        except ValueError as e:
            print(f"Error converting coordinates for atom {atom+1} in configuration {config_counter}: {e}")
            print(f"Line content: {p}")
            exit(1)
    
    # 处理周期性边界条件（消除跨周期跳跃）
    f_next -= np.around(f_next - f_prev)
    f_prev = deepcopy(f_next)
    
    # 转换为笛卡尔坐标并写入XYZ文件
    for atom in range(Natom):
        c_coords = f_next[atom, 0] * a1 + f_next[atom, 1] * a2 + f_next[atom, 2] * a3
        xyz.write(f"{Nname[atom]} {c_coords[0]:.8f} {c_coords[1]:.8f} {c_coords[2]:.8f}\n")

# 关闭文件
xdatcar.close()
xyz.close()
print(f"Conversion completed! Total configurations processed: {config_counter}")
