#!/bin/bash

# 脚本: grep_potcar_tit.sh
# 功能: 搜索当前文件夹下所有POTCAR-*文件中的TIT信息，并进行汇总输出
# 用法: ./grep_potcar_tit.sh 或 bash grep_potcar_tit.sh

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${BLUE}  POTCAR 文件 TIT 信息汇总工具${NC}"
echo -e "${CYAN}========================================${NC}"
echo

# 检查当前目录下是否有POTCAR-*文件
potcar_files=$(ls POTCAR* 2>/dev/null)
potcar_count=$(echo "$potcar_files" | grep -c "^POTCAR-")

if [ $potcar_count -eq 0 ]; then
    echo -e "${RED}❌ 未找到任何 POTCAR-* 文件！${NC}"
    echo -e "请确认："
    echo -e "  1. 当前目录包含 POTCAR-* 文件"
    echo -e "  2. 文件名格式为 POTCAR-开头（如 POTCAR-Al, POTCAR-Fe 等）"
    exit 1
fi

echo -e "${GREEN}✅ 找到 $potcar_count 个 POTCAR 文件：${NC}"
echo "$potcar_files" | while read file; do
    echo "  - $file"
done
echo

# 创建输出目录
output_dir="POTCAR_Results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$output_dir"

# 定义输出文件
summary_file="$output_dir/00_POTCAR_TIT_Summary.txt"
csv_file="$output_dir/00_POTCAR_TIT_Summary.csv"
details_dir="$output_dir/details"

mkdir -p "$details_dir"

# 创建CSV文件头
echo "文件名,TIT信息,元素符号,其他信息,匹配行数" > "$csv_file"

# 清空汇总文件
> "$summary_file"

echo -e "${YELLOW}🔍 开始搜索 TIT 信息...${NC}"
echo

total_matches=0
files_with_tit=0

# 处理每个POTCAR文件
for potcar in $potcar_files; do
    echo -e "${BLUE}处理: $potcar${NC}"
    
    # 定义每个文件的详细信息输出文件
    detail_file="$details_dir/${potcar}_TIT_details.txt"
    
    # 搜索TIT行
    tit_lines=$(grep -n "TIT" "$potcar")
    match_count=$(echo "$tit_lines" | grep -c "TIT" || echo 0)
    
    echo "匹配行数: $match_count" | tee -a "$summary_file"
    echo "----------------------------------------" | tee -a "$summary_file"
    
    if [ $match_count -gt 0 ]; then
        files_with_tit=$((files_with_tit + 1))
        total_matches=$((total_matches + match_count))
        
        echo "文件: $potcar" > "$detail_file"
        echo "匹配到 $match_count 行包含 TIT:" >> "$detail_file"
        echo "----------------------------------------" >> "$detail_file"
        
        # 输出匹配行
        echo "$tit_lines" | while IFS= read -r line; do
            if [ -n "$line" ]; then
                # 输出到汇总文件
                echo "$line" | tee -a "$summary_file"
                
                # 输出到详细文件
                echo "$line" >> "$detail_file"
                
                # 尝试提取元素符号
                element=""
                other_info=""
                
                # 尝试不同的模式匹配
                if [[ "$line" =~ TIT.*= ]]; then
                    # 提取等号后的内容
                    after_equal=${line#*=}
                    # 提取第一个单词（通常是元素符号）
                    element=$(echo "$after_equal" | awk '{print $1}' | tr -d '[:punct:]')
                    
                    # 提取其他信息
                    other_info=$(echo "$line" | sed 's/.*TIT//g')
                fi
                
                # 写入CSV
                echo "\"$potcar\",\"$line\",\"$element\",\"$other_info\",$match_count" >> "$csv_file"
            fi
        done
        
        echo "✅ 已保存到: $detail_file"
    else
        echo -e "${YELLOW}⚠️  未找到 TIT 信息${NC}"
        echo "文件: $potcar" > "$detail_file"
        echo "未找到 TIT 信息" >> "$detail_file"
        
        # 写入CSV
        echo "\"$potcar\",\"未找到\",\"\",\"\",0" >> "$csv_file"
    fi
    
    echo | tee -a "$summary_file"
    echo
done

# 生成汇总统计
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}📊 搜索完成！汇总信息：${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "📁 处理的 POTCAR 文件总数: ${BLUE}$potcar_count${NC}"
echo -e "🔍 包含 TIT 信息的文件数: ${BLUE}$files_with_tit${NC}"
echo -e "📄 匹配到的 TIT 总行数: ${BLUE}$total_matches${NC}"
echo
echo -e "${YELLOW}📁 输出文件：${NC}"
echo -e "  ${GREEN}汇总文件:${NC} $summary_file"
echo -e "  ${GREEN}CSV 文件:${NC} $csv_file"
echo -e "  ${GREEN}详细信息:${NC} $details_dir/"
echo
echo -e "${CYAN}========================================${NC}"
echo -e "使用以下命令查看详细信息："
echo -e "  ${BLUE}cat $summary_file${NC}"
echo -e "  ${BLUE}cat $csv_file${NC}"
echo -e "  ${BLUE}ls -la $details_dir/${NC}"
echo -e "${CYAN}========================================${NC}"

# 显示前10行汇总信息
echo
echo -e "${PURPLE}📄 汇总信息预览：${NC}"
echo "========================================"
head -20 "$summary_file"
echo "========================================"
echo
echo -e "${GREEN}✅ 处理完成！${NC}"
