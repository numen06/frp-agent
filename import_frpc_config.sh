#!/bin/bash
#
# frpc 配置文件导入工具 (Shell 版本)
#
# 使用方式:
#   ./import_frpc_config.sh frpc.ini YOUR_TOKEN 1 ini [group_name]
#   ./import_frpc_config.sh frpc.toml YOUR_TOKEN 2 toml production
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 使用说明
usage() {
    cat << EOF
使用方式: $0 <配置文件> <TOKEN> [服务器ID] [格式] [分组名称] [API地址]

参数:
  配置文件    frpc 配置文件路径 (.ini 或 .toml)
  TOKEN       认证 Token
  服务器ID    frps 服务器 ID (默认: 1)
  格式        配置格式 ini 或 toml (默认: 根据文件扩展名判断)
  分组名称    分组名称 (可选)
  API地址     API 基础地址 (默认: http://localhost:8000)

示例:
  $0 frpc.ini YOUR_TOKEN
  $0 frpc.ini YOUR_TOKEN 1 ini
  $0 frpc.toml YOUR_TOKEN 2 toml production
  $0 frpc.ini YOUR_TOKEN 1 ini default http://192.168.1.100:8000

环境变量:
  FRP_AGENT_TOKEN    认证 Token (如果不通过参数传递)
  FRP_AGENT_URL      API 地址 (默认: http://localhost:8000)

EOF
    exit 1
}

# 检查 jq 是否安装
if ! command -v jq &> /dev/null; then
    echo -e "${RED}错误: 需要安装 jq 工具${NC}" >&2
    echo "macOS: brew install jq" >&2
    echo "Ubuntu/Debian: sudo apt-get install jq" >&2
    echo "CentOS/RHEL: sudo yum install jq" >&2
    exit 1
fi

# 解析参数
CONFIG_FILE="${1}"
TOKEN="${2:-${FRP_AGENT_TOKEN}}"
SERVER_ID="${3:-1}"
FORMAT="${4}"
GROUP_NAME="${5}"
API_URL="${6:-${FRP_AGENT_URL:-http://localhost:8000}}"

# 检查必需参数
if [ -z "$CONFIG_FILE" ]; then
    echo -e "${RED}错误: 缺少配置文件参数${NC}" >&2
    usage
fi

if [ -z "$TOKEN" ]; then
    echo -e "${RED}错误: 缺少 TOKEN 参数，请通过参数或 FRP_AGENT_TOKEN 环境变量提供${NC}" >&2
    usage
fi

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}错误: 配置文件 '$CONFIG_FILE' 不存在${NC}" >&2
    exit 1
fi

# 自动检测格式
if [ -z "$FORMAT" ]; then
    case "$CONFIG_FILE" in
        *.ini)
            FORMAT="ini"
            ;;
        *.toml)
            FORMAT="toml"
            ;;
        *)
            echo -e "${RED}错误: 无法从文件扩展名判断格式，请明确指定格式参数 (ini 或 toml)${NC}" >&2
            exit 1
            ;;
    esac
fi

# 验证格式
if [[ "$FORMAT" != "ini" && "$FORMAT" != "toml" ]]; then
    echo -e "${RED}错误: 格式必须是 ini 或 toml${NC}" >&2
    exit 1
fi

# 读取配置文件内容
echo -e "${YELLOW}正在读取配置文件: $CONFIG_FILE${NC}"
CONTENT=$(cat "$CONFIG_FILE")

# 构建 JSON 数据
if [ -n "$GROUP_NAME" ]; then
    JSON_DATA=$(jq -n \
        --arg content "$CONTENT" \
        --arg format "$FORMAT" \
        --argjson server_id "$SERVER_ID" \
        --arg group "$GROUP_NAME" \
        '{
            content: $content,
            format: $format,
            frps_server_id: $server_id,
            group_name: $group
        }')
else
    JSON_DATA=$(jq -n \
        --arg content "$CONTENT" \
        --arg format "$FORMAT" \
        --argjson server_id "$SERVER_ID" \
        '{
            content: $content,
            format: $format,
            frps_server_id: $server_id
        }')
fi

# 发送请求
echo -e "${YELLOW}正在导入配置 (格式: $FORMAT, 服务器: $SERVER_ID)...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/config/import/text" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$JSON_DATA")

# 分离响应体和状态码
HTTP_BODY=$(echo "$RESPONSE" | head -n -1)
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)

# 检查 HTTP 状态码
if [ "$HTTP_CODE" -ne 200 ]; then
    echo -e "${RED}✗ 请求失败 (HTTP $HTTP_CODE)${NC}" >&2
    echo "$HTTP_BODY" | jq -r '.detail // .' >&2
    exit 1
fi

# 解析响应
SUCCESS=$(echo "$HTTP_BODY" | jq -r '.success // false')

if [ "$SUCCESS" = "true" ]; then
    echo -e "${GREEN}✓ 导入成功${NC}"
    echo
    echo "$HTTP_BODY" | jq -r '.message'
    
    # 显示统计信息
    echo
    echo "统计信息:"
    echo "  总计: $(echo "$HTTP_BODY" | jq -r '.stats.total')"
    echo "  新增: $(echo "$HTTP_BODY" | jq -r '.stats.created')"
    echo "  更新: $(echo "$HTTP_BODY" | jq -r '.stats.updated')"
    echo "  失败: $(echo "$HTTP_BODY" | jq -r '.stats.failed')"
    
    # 显示错误详情
    FAILED=$(echo "$HTTP_BODY" | jq -r '.stats.failed')
    if [ "$FAILED" -gt 0 ]; then
        echo
        echo "失败详情:"
        echo "$HTTP_BODY" | jq -r '.stats.errors[] | "  - \(.proxy_name): \(.error)"'
    fi
else
    echo -e "${RED}✗ 导入失败${NC}" >&2
    echo "$HTTP_BODY" | jq -r '.message // "未知错误"' >&2
    exit 1
fi

