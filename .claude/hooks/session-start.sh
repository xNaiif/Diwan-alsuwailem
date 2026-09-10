#!/bin/bash
set -euo pipefail

# يسخّن كاش npm لحزمة ruflo (Ruflo / Claude-Flow) عشان أول تشغيل فعلي لأداة
# تنسيق الوكلاء المتعددة (المسجّلة في .mcp.json) يكون سريع بدل ما ينزّلها من الصفر.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

npm install -g ruflo@3.40.0 >/dev/null 2>&1 || true
