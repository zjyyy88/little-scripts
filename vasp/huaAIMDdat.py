import matplotlib.pyplot as plt
import numpy as np

#用法
#绘制temperature energy plot
# 1：grep 'F=' OSZICAR|awk '{print $1, "\t"$3,"\t"$9}' >AIMD.dat

#2： 读取数据，假设数据文件名为 data.txt，按实际文件名修改
data = np.loadtxt('AIMD.dat')

x = data[:, 0]
y_temperature = data[:, 1]
y_energy = data[:, 2]

# 创建图形
fig, ax1 = plt.subplots()

# 绘制 Temperature (K) 曲线，使用左 y 轴
color = 'tab:red'
ax1.set_xlabel('Index')
ax1.set_ylabel('Temperature (K)', color=color)
ax1.plot(x, y_temperature, color=color)
ax1.tick_params(axis='y', labelcolor=color)

# 创建第二个 y 轴，绘制 Energy (eV) 曲线
ax2 = ax1.twinx()  
color = 'tab:blue'
ax2.set_ylabel('Energy (eV)', color=color)  
ax2.plot(x, y_energy, color=color)
ax2.tick_params(axis='y', labelcolor=color)

# 整合显示
fig.tight_layout()  
plt.savefig('result_plot.jpg', dpi=1200, bbox_inches='tight')  # 保存为jpg，设置分辨率和边距
plt.show()
