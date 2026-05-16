"""
data_store.py
SQLite 資料庫模組 - 儲存玩家數據和排行榜
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "ai_coach_data.db")


def init_db():
    """初始化資料庫，建立所需表格"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            class_name TEXT,
            squat_count INTEGER DEFAULT 0,
            squat_correct INTEGER DEFAULT 0,
            squat_accuracy INTEGER DEFAULT 0,
            squat_score INTEGER DEFAULT 0,
            balance_time REAL DEFAULT 0,
            balance_score INTEGER DEFAULT 0,
            reaction_time REAL DEFAULT 0,
            reaction_score INTEGER DEFAULT 0,
            total_score INTEGER DEFAULT 0,
            played_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_player(name, age, class_name, squat_summary, balance_summary, reaction_summary=None):
    """
    儲存一位玩家的完整數據
    返回 player_id
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    squat_score = squat_summary.get("score", 0)
    balance_score = balance_summary.get("score", 0)
    reaction_score = reaction_summary.get("score", 0) if reaction_summary else 50
    total_score = round((squat_score + balance_score + reaction_score) / 3)

    c.execute("""
        INSERT INTO players
        (name, age, class_name,
         squat_count, squat_correct, squat_accuracy, squat_score,
         balance_time, balance_score,
         reaction_time, reaction_score,
         total_score, played_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name, age, class_name,
        squat_summary.get("total_squats", 0),
        squat_summary.get("correct_squats", 0),
        squat_summary.get("accuracy", 0),
        squat_score,
        balance_summary.get("best_balance_time", 0),
        balance_score,
        reaction_summary.get("reaction_time", 0) if reaction_summary else 0,
        reaction_score,
        total_score,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    player_id = c.lastrowid
    conn.commit()
    conn.close()
    return player_id


def get_player(player_id):
    """取得單一玩家數據"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE id = ?", (player_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return _row_to_dict(row)
    return None


def get_leaderboard(limit=10):
    """取得排行榜（按總分排序）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT name, class_name, total_score, squat_score, balance_score, reaction_score, played_at
        FROM players
        ORDER BY total_score DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_rank(player_id):
    """取得玩家排名"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT total_score FROM players WHERE id = ?", (player_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None, None
    score = row[0]
    c.execute("SELECT COUNT(*) FROM players WHERE total_score > ?", (score,))
    rank = c.fetchone()[0] + 1
    c.execute("SELECT COUNT(*) FROM players")
    total = c.fetchone()[0]
    conn.close()
    return rank, total


def get_class_average(class_name):
    """取得同班平均分"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT AVG(total_score), AVG(squat_score), AVG(balance_score)
        FROM players WHERE class_name = ?
    """, (class_name,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        return {
            "avg_total": round(row[0]),
            "avg_squat": round(row[1]),
            "avg_balance": round(row[2])
        }
    return None


def get_age_percentile(player_id):
    """計算玩家在同齡中的百分位"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT age, total_score FROM players WHERE id = ?", (player_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    age, score = row
    c.execute("SELECT COUNT(*) FROM players WHERE age = ?", (age,))
    total_same_age = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM players WHERE age = ? AND total_score <= ?", (age, score))
    below_count = c.fetchone()[0]
    conn.close()
    if total_same_age <= 1:
        return None
    return round(below_count / total_same_age * 100)


def _row_to_dict(row):
    keys = ["id", "name", "age", "class_name",
            "squat_count", "squat_correct", "squat_accuracy", "squat_score",
            "balance_time", "balance_score",
            "reaction_time", "reaction_score",
            "total_score", "played_at"]
    return dict(zip(keys, row))


# 啟動時自動初始化
init_db()
