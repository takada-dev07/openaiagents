#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "== health =="
curl -sS "${BASE_URL}/health" | cat
echo

echo "== images/generate =="
IMG_JSON="$(curl -sS -X POST "${BASE_URL}/images/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"日本語のデモ画像。青い背景、白い文字で『学習用』","size":"512x512","transparent":false}')"
echo "${IMG_JSON}" | cat
echo

IMG_PATH="$(python - <<PY
import json
print(json.loads('''${IMG_JSON}''')["image_path"])
PY
)"

echo "== pptx/render =="
PPTX_JSON="$(curl -sS -X POST "${BASE_URL}/pptx/render" \
  -H "Content-Type: application/json" \
  -d "$(python - <<PY
import json
payload = {
  "title":"デモ資料",
  "slides":[
    {"heading":"概要","bullets":["これはDevContainerで動く最小サンプルです。","画像生成はAPIキー無しでもダミーで動きます。"],"image_path":"%s"},
    {"heading":"次にやること","bullets":["本物のLLM接続に差し替える","workflowノードを増やす","テンプレをリッチにする"],"image_path":"%s"}
  ]
}
print(json.dumps(payload, ensure_ascii=False) % ("%s","%s"))
PY
 | python - <<PY
import sys
import json
s = sys.stdin.read()
obj = json.loads(s.replace("%s","${IMG_PATH}"))
print(json.dumps(obj, ensure_ascii=False))
PY
)")"
echo "${PPTX_JSON}" | cat
echo

PPTX_PATH="$(python - <<PY
import json
print(json.loads('''${PPTX_JSON}''')["pptx_path"])
PY
)"

echo "== pptx/explain =="
curl -sS -X POST "${BASE_URL}/pptx/explain" \
  -H "Content-Type: application/json" \
  -d "$(python - <<PY
import json
print(json.dumps({"pptx_path":"${PPTX_PATH}"}, ensure_ascii=False))
PY
)" | cat
echo

echo "== workflow/run =="
curl -sS -X POST "${BASE_URL}/workflow/run" \
  -H "Content-Type: application/json" \
  -d "$(python - <<'PY'
import json
payload = {
  "workflow": {
    "nodes": [
      {"id":"outline","tool":"outline","params":{"task":{"$ref":"input.task"}}, "retry":0, "timeout_sec":10},
      {"id":"image","tool":"generate_image","params":{"prompt":{"$ref":"input.task"},"size":"512x512","transparent":False}, "retry":1, "timeout_sec":60},
      {"id":"pptx","tool":"render_pptx","params":{"title":{"$ref":"results.outline.title"},"slides":{"$ref":"results.outline.slides"},"image_path":{"$ref":"results.image.image_path"}}, "retry":0, "timeout_sec":60},
      {"id":"explain","tool":"explain_pptx","params":{"pptx_path":{"$ref":"results.pptx.pptx_path"}}, "retry":0, "timeout_sec":60}
    ],
    "edges": [
      {"from":"outline","to":"image"},
      {"from":"image","to":"pptx"},
      {"from":"pptx","to":"explain"}
    ]
  },
  "input": {"task":"ワークフローで資料を作り、説明まで出して"}
}
print(json.dumps(payload, ensure_ascii=False))
PY
)" | cat
echo


