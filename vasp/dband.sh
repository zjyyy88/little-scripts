#!/bin/bash
# 文件名：simple_dband_center.sh

echo "=== 简化版d带中心计算 ==="

for dir in ./*/111*/normal/dos; do
    if [ -d "$dir" ] && [ -f "$dir/OUTCAR" ]; then
        echo ""
        echo "处理: $dir"
        
        cd "$dir" || continue
        
        # 获取元素信息（从POSCAR第6行）
        if [ -f "POSCAR" ]; then
            elements=$(sed -n '6p' POSCAR)
            echo "元素: $elements"
            
            # 简单逻辑：取第一个非Li,非In,非Cl的元素作为TM
            for elem in $elements; do
                if [[ "$elem" != "Li" && "$elem" != "In" && "$elem" != "Cl" ]]; then
                    tm_element="$elem"
                    echo "目标过渡金属: $tm_element"
                    
                    # 执行vaspkit
                    {
                        echo "503"
                        echo "N" 
                        echo "$tm_element"
                    } | vaspkit
                    
                    break
                fi
            done
        fi
        
        cd - > /dev/null
    fi
done
