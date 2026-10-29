"""쿠팡 가격 추적 1회 백필(10/30 Cowork ①): git log의 events.json now·chk(커밋마다 — 그때 옵션 item 그대로 키) + posts.json 진우 쿠팡 글 처음 올린 가격 -> price_hist.json(있으면 합침).
저장소 루트에서: python3 tools/price_backfill.py (전체 기록이 있는 clone에서 — Actions 얕은 checkout X)"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.getcwd())
import build_site as S  # noqa: E402


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout


h, n = S.ph_load(), 0
for sha in git("log", "--reverse", "--format=%H", "--", "events.json").split():
    try:
        n += S.ph_events(h, S.ev_info(json.loads(git("show", f"{sha}:events.json"))))
    except (subprocess.CalledProcessError, ValueError) as e:
        print("skip", sha[:10], type(e).__name__)
n += S.ph_posts(h, json.load(open("posts.json")), S.ev_info())
json.dump(h, open(S.PRICE_HIST, "w"), separators=(",", ":"))
print(f"price_hist.json 상품 {len(h)}개 · 줄 {sum(map(len, h.values()))} · 이번 +{n}")
