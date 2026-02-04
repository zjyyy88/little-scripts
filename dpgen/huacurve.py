import numpy as np
import matplotlib.pyplot as plt

def print_loss_statistics(data):
    """打印损失函数的统计信息"""
    print("\n=== 损失函数统计信息 ===")
    for name in data.dtype.names[1:-1]:  # 跳过'step'和最后一个字段（如果有）
        loss_values = data[name]
        print(f"\n【{name}】")
        print(f"  初始值: {loss_values[0]:.6e}")
        print(f"  最终值: {loss_values[-1]:.6e}")
        print(f"  最大值: {loss_values.max():.6e}")
        print(f"  最小值: {loss_values.min():.6e}")
        print(f"  平均值: {loss_values.mean():.6e}")
        print(f"  变化率: {(loss_values[0]-loss_values[-1])/loss_values[0]*100:.2f}%")
        print(f"  收敛速度: {(loss_values[0]-loss_values[-1])/len(loss_values):.2e}/step")

def plot_training_curves(data):
    """绘制训练曲线并保存"""
    plt.figure(figsize=(12, 8))
    
    # 绘制每条曲线
    for name in data.dtype.names[1:-1]:
        plt.plot(data['step'], data[name], lw=2, label=name)
    
    # 图形装饰
    plt.legend(fontsize=12, framealpha=0.5)
    plt.xlabel('Training Step', fontsize=14)
    plt.ylabel('Loss Value', fontsize=14)
    plt.title('Training Loss Curves', fontsize=16, pad=20)
    plt.xscale('symlog')
    plt.yscale('log')
    plt.grid(True, which="both", ls="-", alpha=0.3)
    
    # 修正保存参数（移除quality参数）
    plt.savefig('training_curve.jpg', dpi=300, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    try:
        # 读取数据
        data = np.genfromtxt("lcurve.out", names=True)
        
        # 检查数据有效性
        if len(data) == 0:
            raise ValueError("输入文件为空或格式不正确")
            
        # 输出统计信息
        print_loss_statistics(data)
        
        # 绘制曲线
        plot_training_curves(data)
        
        print("\n图表已保存为: training_curve.jpg")
        
    except FileNotFoundError:
        print("错误: 未找到lcurve.out文件")
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
