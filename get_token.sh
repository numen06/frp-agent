#!/bin/bash
#
# 获取认证 Token
# 
# 使用方式:
#   ./get_token.sh [username] [password] [api_url]
#

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 参数
USERNAME="${1:-admin}"
PASSWORD="${2:-admin@123}"
API_URL="${3:-http://localhost:8000}"

echo -e "${YELLOW}正在登录...${NC}"
echo "API: $API_URL"
echo "用户名: $USERNAME"

# 发送登录请求
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=$USERNAME&password=$PASSWORD")

# 分离响应体和状态码
HTTP_BODY=$(echo "$RESPONSE" | head -n -1)
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)

# 检查状态码
if [ "$HTTP_CODE" -eq 200 ]; then
    # 提取 token
    if command -v jq &> /dev/null; then
        TOKEN=$(echo "$HTTP_BODY" | jq -r '.access_token')
        echo -e "${GREEN}✓ 登录成功${NC}"
        echo
        echo "您的 Token:"
        echo "$TOKEN"
        echo
        echo "使用示例:"
        echo "  export FRP_AGENT_TOKEN=\"$TOKEN\""
        echo "  ./import_frpc_config.sh frpc.ini"
        echo
        echo "或者:"
        echo "  ./import_frpc_config.py frpc.ini --token \"$TOKEN\""
    else
        echo -e "${GREEN}✓ 登录成功${NC}"
        echo
        echo "响应:"
        echo "$HTTP_BODY"
        echo
        echo "提示: 安装 jq 工具可以自动提取 token"
        echo "macOS: brew install jq"
        echo "Ubuntu/Debian: sudo apt-get install jq"
    fi
else
    echo "✗ 登录失败 (HTTP $HTTP_CODE)"
    echo "$HTTP_BODY"
    exit 1
fi

