ummarize_band_center_corrected.sh
# 功能：根据实际文件格式汇总带中心数据

echo "=== 带中心数据汇总（修正列顺序）==="
echo "搜索路径: ./*/111*/normal"

# 输出文件
OUTPUT_CSV="band_center_summary.csv"
OUTPUT_TXT="band_center_summary.txt"

# 创建输出文件头
echo "Directory,Element,Spin_UP_sBand(eV),Spin_UP_pBand(eV),Spin_UP_dBand(eV),Spin_DW_sBand(eV),Spin_DW_pBand(eV),Spin_DW_dBand(eV),Average_dBand(eV),Energy_Window" > "$OUTPUT_CSV"
echo "====================================================================" > "$OUTPUT_TXT"
echo "带中心数据汇总 - 基于实际文件格式" >> "$OUTPUT_TXT"
echo "生成时间: $(date)" >> "$OUTPUT_TXT"
echo "====================================================================" >> "$OUTPUT_TXT"

# 计数器
total_dirs=0
found_files=0
success_count=0

# 遍历指定路径
for dir in ./*/111*/normal/dos; do
    if [ -d "$dir" ] && [ -f "$dir/OUTCAR" ]; then
        total_dirs=$((total_dirs + 1))
        echo ""
        echo "处理 [$total_dirs]: $dir"
        
        # 检查BAND_CENTER文件是否存在
        if [ -f "$dir/BAND_CENTER" ]; then
            found_files=$((found_files + 1))
            echo "✅ 找到BAND_CENTER文件"
            
            # 提取目录信息
            parent_dir=$(basename "$(dirname "$(dirname "$dir")")")
            
            # 解析BAND_CENTER文件 - 修正列顺序
            spin_up_s=""
            spin_up_p=""
            spin_up_d=""
            spin_dw_s=""
            spin_dw_p=""
            spin_dw_d=""
            energy_window=""
            
            # 读取文件内容
            while IFS= read -r line; do
                # 跳过注释行和空行
                if [[ "$line" == \#* ]] || [[ -z "$line" ]]; then
                    continue
                fi
                
                # 提取能量窗口
                if [[ "$line" == *"energy window of integration"* ]]; then
                    energy_window=$(echo "$line" | grep -o '\[.*\]')
                    echo "📊 能量窗口: $energy_window"
                fi
                
                # 提取Spin-UP数据（第2-4列）
                if [[ "$line" == *"Spin-UP"* ]]; then
                    spin_up_s=$(echo "$line" | awk '{print $2}')  # s-band
                    spin_up_p=$(echo "$line" | awk '{print $3}')  # p-band  
                    spin_up_d=$(echo "$line" | awk '{print $4}')  # d-band
                    echo "📈 Spin-UP: s=$spin_up_s, p=$spin_up_p, d=$spin_up_d eV"
                fi
                
                # 提取Spin-DW数据（第2-4列）
                if [[ "$line" == *"Spin-DW"* ]]; then
                    spin_dw_s=$(echo "$line" | awk '{print $2}')  # s-band
                    spin_dw_p=$(echo "$line" | awk '{print $3}')  # p-band
                    spin_dw_d=$(echo "$line" | awk '{print $4}')  # d-band
                    echo "📈 Spin-DW: s=$spin_dw_s, p=$spin_dw_p, d=$spin_dw_d eV"
                fi
                
            done < "$dir/BAND_CENTER"
            
            # 验证数据完整性
            if [ -n "$spin_up_d" ] && [ -n "$spin_dw_d" ]; then
                # 计算d带中心平均值
                average_dband=$(echo "scale=4; ($spin_up_d + $spin_dw_d) / 2" | bc -l 2>/dev/null || echo "N/A")
                success_count=$((success_count + 1))
                
                echo "✅ 数据提取成功"
                echo "   Spin-UP: s=$spin_up_s, p=$spin_up_p, d=$spin_up_d eV"
                echo "   Spin-DW: s=$spin_dw_s, p=$spin_dw_p, d=$spin_dw_d eV"
                echo "   平均d带中心: $average_dband eV"
                
                # 获取元素信息
                element_info="Unknown"
                if [[ "$parent_dir" =~ Li3Ta3O4Cl10 ]]; then
                    element_info="Ta"
                else
                    element_info=$(echo "$parent_dir" | grep -oE '[A-Z][a-z]?' | head -1 || echo "Unknown")
                fi
                
                echo "🔬 推断元素: $element_info"
                
                # 写入CSV文件
                echo "$parent_dir,$element_info,$spin_up_s,$spin_up_p,$spin_up_d,$spin_dw_s,$spin_dw_p,$spin_dw_d,$average_dband,$energy_window" >> "$OUTPUT_CSV"
                
                # 写入文本文件
                cat >> "$OUTPUT_TXT" << EOF

目录: $parent_dir
路径: $dir
元素: $element_info

Spin-UP 带中心:
  s-band: $spin_up_s eV
  p-band: $spin_up_p eV
  d-band: $spin_up_d eV

Spin-DW 带中心:
  s-band: $spin_dw_s eV
  p-band: $spin_dw_p eV
  d-band: $spin_dw_d eV

平均d带中心: $average_dband eV
能量窗口: $energy_window
----------------------------------------
EOF
            else
                echo "❌ 数据提取不完整"
                echo "   Spin-UP d-band: $spin_up_d"
                echo "   Spin-DW d-band: $spin_dw_d"
            fi
        else
            echo "❌ 未找到BAND_CENTER文件"
        fi
    fi
done

# 生成统计报告
generate_statistics_report

echo ""
echo "=== 汇总完成 ==="
echo "搜索目录数: $total_dirs"
echo "找到BAND_CENTER文件: $found_files"
echo "成功处理: $success_count"
echo "输出文件:"
echo "  - $OUTPUT_CSV (CSV格式，包含所有带中心数据)"
echo "  - $OUTPUT_TXT (文本格式详细报告)"

# 函数：生成统计报告
generate_statistics_report() {
    if [ $success_count -gt 0 ]; then
        echo ""
        echo "=== 统计报告 ==="
        echo "" >> "$OUTPUT_TXT"
        echo "=== 统计报告 ===" >> "$OUTPUT_TXT"
        
        # d带中心统计
        awk -F',' 'NR>1 && $5 != "" {
            count[$2]++
            sum_up_d[$2] += $5    # Spin-UP d-band
            sum_dw_d[$2] += $8    # Spin-DW d-band
            sum_avg[$2] += $9     # Average d-band
        } END {
            if (length(count) > 0) {
                print "d带中心统计:"
                for (e in count) {
                    avg_up_d = sum_up_d[e] / count[e]
                    avg_dw_d = sum_dw_d[e] / count[e]
                    avg_avg = sum_avg[e] / count[e]
                    printf "%s: %d个数据, UP-d=%.3f DW-d=%.3f AVG=%.3f eV\n", 
                           e, count[e], avg_up_d, avg_dw_d, avg_avg
                }
            }
        }' "$OUTPUT_CSV" | tee -a "$OUTPUT_TXT"
        
        # 总体统计
        awk -F',' 'NR>1 && $5 != "" {
            data_up_d[NR]=$5; data_dw_d[NR]=$8; data_avg[NR]=$9
            sum_up_d+=$5; sum_dw_d+=$8; sum_avg+=$9; count++
        } END {
            if (count > 0) {
                asort(data_up_d); asort(data_dw_d); asort(data_avg)
                print ""
                print "总体d带中心统计:"
                printf "Spin-UP d-band: 平均=%.3f, 范围=%.3f~%.3f eV\n", 
                       sum_up_d/count, data_up_d[1], data_up_d[count]
                printf "Spin-DW d-band: 平均=%.3f, 范围=%.3f~%.3f eV\n", 
                       sum_dw_d/count, data_dw_d[1], data_dw_d[count]
                printf "平均值:        平均=%.3f, 范围=%.3f~%.3f eV\n", 
                       sum_avg/count, data_avg[1], data_avg[count]
            }
        }' "$OUTPUT_CSV" | tee -a "$OUTPUT_TXT"
        
        # 显示示例数据
        echo "" >> "$OUTPUT_TXT"
        echo "=== 数据示例 ===" >> "$OUTPUT_TXT"
        awk -F',' 'NR==2 {
            printf "示例数据:\n"
            printf "Spin-UP: s=%.3f p=%.3f d=%.3f eV\n", $3, $4, $5
            printf "Spin-DW: s=%.3f p=%.3f d=%.3f eV\n", $6, $7, $8
        }' "$OUTPUT_CSV" | tee -a "$OUTPUT_TXT"
    fi
}
