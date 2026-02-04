#!/usr/bin/env python3
import os
from datetime import datetime

def find_deepmd_data_dirs(root_dir='.'):
    """
    查找所有名为deepmd_data的文件夹并返回绝对路径列表
    """
    deepmd_paths = []
    for root, dirs, files in os.walk(root_dir):
        if 'deepmd_data' in dirs:
            abs_path = os.path.abspath(os.path.join(root, 'deepmd_data'))
            deepmd_paths.append(abs_path)
    return deepmd_paths

if __name__ == "__main__":
    print("正在搜索deepmd_data文件夹...")
    current_dir = os.getcwd()
    results = find_deepmd_data_dirs(current_dir)
    
    # 生成输出文件名
    dir_name = os.path.basename(current_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"dpmddata-{dir_name}-{timestamp}.txt"
    
    if results:
        print("\n找到以下deepmd_data文件夹：")
        with open(output_file, 'w') as f:
            f.write("# deepmd_data文件夹路径列表\n")
            f.write(f"# 搜索时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 搜索目录: {current_dir}\n\n")
            
            for i, path in enumerate(results, 1):
                print(f"{i}. {path}")
                f.write(f"{path}\n")
        
        print(f"\n共找到 {len(results)} 个deepmd_data文件夹")
        print(f"结果已保存到: {os.path.abspath(output_file)}")
    else:
        print("\n未找到名为deepmd_data的文件夹")
        with open(output_file, 'w') as f:
            f.write("# 未找到deepmd_data文件夹\n")
            f.write(f"# 搜索时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 搜索目录: {current_dir}\n")
