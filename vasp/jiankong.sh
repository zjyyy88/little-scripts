#!/bin/bash
# 文件名：jiankong_fixed.sh
# 功能：修复版VASP收敛性检查

echo "=== VASP计算收敛性检查（修复版）==="
echo "开始检查所有Li3Ta3O4Cl10_il0文件夹..."

for dir in ./jobs/*/; do
    if [ -d "$dir" ] && [ -f "$dir/OUTCAR" ]; then
        echo "检查: $dir"
        
        # 1. 检查是否收敛
        if grep -q "reached required accuracy" "$dir/OUTCAR"; then
            echo "  ✅ 计算已收敛"
            # 提取最终能量
            energy=$(grep "TOTEN" "$dir/OUTCAR" | tail -1 | awk '{print $5}')
            echo "  💡 最终能量: $energy eV"
            
        else
            echo "  ⚠️  计算未收敛"
            
            # 2. 正确提取离子步信息（过滤掉无关行）
            last_ionic_step=$(grep "F" "$dir/OSZICAR" | tail -1 | awk '{print $1}' 2>/dev/null)
            
            if [ -n "$last_ionic_step" ] && [ "$last_ionic_step" -eq "$last_ionic_step" ] 2>/dev/null; then
                echo "  🔄 离子步数: $last_ionic_step"
                
                # 提取该步的能量信息
                step_energy=$(grep "TOTEN" "$dir/OUTCAR" | tail -1 | awk '{print $5}')
                echo "  💡 当前能量: $step_energy eV"
                
            else
                # 3. 如果无法提取离子步，检查其他收敛信息
                echo "  🔍 分析收敛状态..."
                
                # 检查电子步收敛
                elec_steps=$(grep -c "DAV:" "$dir/OUTCAR")
                echo "  📊 电子步数: $elec_steps"
                
                # 检查力收敛
                force_info=$(grep "TOTAL-FORCE" "$dir/OUTCAR" | tail -1)
                if [ -n "$force_info" ]; then
                    echo "  💪 最后力计算完成"
                fi
                
                # 检查是否有错误信息
                if grep -q "ERROR" "$dir/OUTCAR"; then
                    echo "  ❗ 检测到错误信息"
                fi
            fi
        fi
        echo "---"
    else
        echo "跳过: $dir (无OUTCAR文件)"
    fi
done
echo "检查完成。"