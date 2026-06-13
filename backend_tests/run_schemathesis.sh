#!/usr/bin/env bash
# 用一個隨機帳號登入拿 session_id，再用 schemathesis 對本機 API 做 fuzz 測試。
# 用法：
#   bash backend_tests/run_schemathesis.sh           # 預設每個 endpoint 跑 100 個 case
#   bash backend_tests/run_schemathesis.sh 20        # 每個 endpoint 跑 20 個 case（較快）
set -euo pipefail

BASE_URL="http://127.0.0.1:8000"
SQL_API_URL="http://sql-api.shiragaserver.lan/query"
MAX_EXAMPLES="${1:-100}"

ACCOUNT="schemathesis_$(date +%s)_$$"
PASSWORD="Test1234!"

db_query() {
  curl -s -X POST "$SQL_API_URL" -H "Content-Type: application/json" \
    -d "{\"sql\": \"$1\", \"params\": []}"
}

# 記錄目前最大的 user_id：之後不管是我們自己註冊的帳號，還是 schemathesis
# fuzz POST /auth/register 時意外成功建立的帳號，user_id 都會大於這個值，
# 結束時可以一次清掉，不會動到原本就存在的帳號
MAX_ID_BEFORE=$(db_query "SELECT COALESCE(MAX(user_id), 0) AS m FROM users" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['rows'][0]['m'])")

cleanup() {
  echo "清理測試期間建立的帳號 (user_id > $MAX_ID_BEFORE)..."
  db_query "DELETE FROM users WHERE user_id > $MAX_ID_BEFORE" > /dev/null
}
trap cleanup EXIT

echo "建立測試帳號: $ACCOUNT"
curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"account\": \"$ACCOUNT\", \"password\": \"$PASSWORD\"}" > /dev/null

echo "登入取得 session_id..."
SESSION_ID=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"account\": \"$ACCOUNT\", \"password\": \"$PASSWORD\"}" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")

echo "session_id = $SESSION_ID"
echo "開始跑 schemathesis (每個 endpoint $MAX_EXAMPLES 個 case)..."

schemathesis run "$BASE_URL/openapi.json" \
  --header "X-Session-Id: $SESSION_ID" \
  --checks all \
  --max-examples="$MAX_EXAMPLES"


