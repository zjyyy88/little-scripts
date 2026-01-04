import matplotlib.pyplot as plt

# 定义文件路径
file_path = './300K-msd.json'

# 初始化存储时间步和 MSD 值的列表
timesteps = []
msd_values = []

# 读取文件内容
with open(file_path, 'r') as file:
    for line in file:
        # 跳过注释行
        if line.startswith('#'):
            continue
        # 分割每行数据
        data = line.split()
        if len(data) >= 5:  # 确保每行至少有 5 个数据项
            timestep = int(data[0])
            msd = float(data[4])  # 假设 MSD 值在第 5 列
            timesteps.append(timestep)
            msd_values.append(msd)

# 绘制 MSD 随时间步的变化曲线
plt.plot(timesteps, msd_values)
plt.xlabel('Timestep(fs)')
plt.ylabel('Mean Squared Displacement(Angstron2)')
plt.title('MSD vs Timestep at 300K')
plt.grid(True)

# 保存图表为 JPG 文件
plt.savefig('300Kmsd_plot.jpg', dpi=1000)

# 显示图表（可选，如果不想显示图表，可注释掉该行）
# plt.show()
