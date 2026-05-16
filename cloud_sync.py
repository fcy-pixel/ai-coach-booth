"""
cloud_sync.py
將玩家分數同步到 Cloudflare Workers 雲端排行榜
在背景執行，不阻塞 UI
"""

import threading
import urllib.request
import urllib.error
import json

CLOUD_API = "https://ai-coach-booth.pages.dev/api/score"


def sync_score(player_data, squat_summary, balance_summary, reaction_summary=None,
               on_success=None, on_error=None):
    """
    在背景執行緒將分數 POST 到雲端
    on_success(rank, total): 成功回調
    on_error(msg): 失敗回調
    """
    def _run():
        payload = {
            "name":            player_data.get("name", ""),
            "age":             player_data.get("age"),
            "class_name":      player_data.get("class_name", ""),
            "squat_score":     squat_summary.get("score", 0),
            "balance_score":   balance_summary.get("score", 0),
            "reaction_score":  reaction_summary.get("score", 50) if reaction_summary else 50,
            "squat_count":     squat_summary.get("total_squats", 0),
            "squat_accuracy":  squat_summary.get("accuracy", 0),
            "balance_time":    balance_summary.get("best_balance_time", 0),
            "reaction_time":   reaction_summary.get("reaction_time", 0.3) if reaction_summary else 0.3,
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                CLOUD_API,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                result = json.loads(resp.read().decode())
                if on_success and result.get("success"):
                    on_success(result.get("rank"), result.get("total_players"))
        except urllib.error.URLError as e:
            if on_error:
                on_error(f"網絡錯誤：{e.reason}")
        except Exception as e:
            if on_error:
                on_error(str(e))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
