"""
feedback_engine.py
分析玩家數據，生成個人化訓練建議
純規則 based（不需要 API）
"""


def rate(score):
    """將分數轉換為星星評級"""
    if score >= 90:
        return "⭐⭐⭐⭐⭐", "優秀"
    elif score >= 75:
        return "⭐⭐⭐⭐", "良好"
    elif score >= 55:
        return "⭐⭐⭐", "一般"
    elif score >= 35:
        return "⭐⭐", "需要加油"
    else:
        return "⭐", "繼續練習"


def analyze_squat(squat_summary):
    """分析深蹲表現"""
    score = squat_summary.get("score", 0)
    count = squat_summary.get("total_squats", 0)
    accuracy = squat_summary.get("accuracy", 0)
    avg_angle = squat_summary.get("avg_knee_angle", 90)

    tips = []

    if count == 0:
        tips.append("下次試試做深蹲，記住腳與肩同寬！")
    elif count < 5:
        tips.append("你做了幾個深蹲！繼續練習，目標是10秒內做5個。")
    else:
        tips.append(f"你10秒內做了 {count} 個深蹲，非常努力！")

    if accuracy < 50:
        tips.append("姿勢要注意：膝蓋不要超過腳趾，上身保持直立。")
    elif accuracy < 80:
        tips.append("姿勢基本正確！試試蹲慢一點，更能鍛練肌肉。")
    else:
        tips.append("姿勢非常標準！可以嘗試負重深蹲增加難度。")

    if avg_angle and avg_angle > 120:
        tips.append("可以蹲得更低一點，膝蓋彎曲至90度效果最好。")

    return score, tips


def analyze_balance(balance_summary):
    """分析平衡力表現"""
    score = balance_summary.get("score", 0)
    best_time = balance_summary.get("best_balance_time", 0)
    tips = []

    if best_time < 2:
        tips.append("單腳平衡需要多練習！每天練習，從5秒開始。")
    elif best_time < 5:
        tips.append(f"你最長單腳站了 {best_time} 秒！目標是10秒。")
    elif best_time < 10:
        tips.append(f"平衡力不錯！{best_time} 秒！試試閉眼單腳站增加難度。")
    else:
        tips.append(f"平衡力超強！{best_time} 秒！你的核心肌群很好！")

    return score, tips


def analyze_reaction(reaction_summary):
    """分析反應力表現"""
    if not reaction_summary:
        return 50, ["反應力測試未完成。"]

    score = reaction_summary.get("score", 50)
    reaction_time = reaction_summary.get("reaction_time", 0.3)
    tips = []

    if reaction_time > 0.4:
        tips.append(f"反應時間 {reaction_time:.3f} 秒，多玩反應遊戲可以提升！")
    elif reaction_time > 0.25:
        tips.append(f"反應時間 {reaction_time:.3f} 秒，屬於正常水平！")
    else:
        tips.append(f"反應時間只有 {reaction_time:.3f} 秒，你有運動員的反應力！")

    return score, tips


def generate_training_plan(squat_score, balance_score, reaction_score):
    """根據弱點生成7日訓練計劃"""
    plan = {
        "第一、四天（腿部力量）": [],
        "第二、五天（平衡與核心）": [],
        "第三、六天（反應與敏捷）": [],
        "第七天（休息）": ["輕度伸展運動 10 分鐘", "保持充足睡眠"]
    }

    # 腿部力量（深蹲分析）
    if squat_score < 60:
        plan["第一、四天（腿部力量）"] = [
            "深蹲 3 組 × 10 次（慢速，注意姿勢）",
            "靠牆靜蹲 3 × 30 秒",
            "跳繩 2 分鐘"
        ]
    else:
        plan["第一、四天（腿部力量）"] = [
            "深蹲 4 組 × 15 次",
            "單腳深蹲 2 組 × 8 次（每邊）",
            "跳繩 3 分鐘"
        ]

    # 平衡與核心
    if balance_score < 50:
        plan["第二、五天（平衡與核心）"] = [
            "單腳站立 5 × 10 秒（每邊）",
            "平板支撐 3 × 20 秒",
            "走直線平衡練習 5 分鐘"
        ]
    else:
        plan["第二、五天（平衡與核心）"] = [
            "閉眼單腳站立 5 × 15 秒",
            "平板支撐 3 × 45 秒",
            "瑜伽樹式 3 × 30 秒"
        ]

    # 反應與敏捷
    if reaction_score < 50:
        plan["第三、六天（反應與敏捷）"] = [
            "拍手反應遊戲 5 分鐘（雙人）",
            "墊步側移 3 × 30 秒",
            "追球練習 5 分鐘"
        ]
    else:
        plan["第三、六天（反應與敏捷）"] = [
            "梯形敏捷跑 5 組",
            "彈力帶側步 3 × 20 次",
            "快速反應接球練習 10 分鐘"
        ]

    return plan


def generate_full_feedback(player_data):
    """
    輸入玩家數據字典，返回完整 feedback 報告字典
    """
    squat_summary = {
        "score": player_data.get("squat_score", 0),
        "total_squats": player_data.get("squat_count", 0),
        "accuracy": player_data.get("squat_accuracy", 0),
        "avg_knee_angle": 90
    }
    balance_summary = {
        "score": player_data.get("balance_score", 0),
        "best_balance_time": player_data.get("balance_time", 0)
    }
    reaction_summary = {
        "score": player_data.get("reaction_score", 50),
        "reaction_time": player_data.get("reaction_time", 0.3)
    }

    squat_score, squat_tips = analyze_squat(squat_summary)
    balance_score, balance_tips = analyze_balance(balance_summary)
    reaction_score, reaction_tips = analyze_reaction(reaction_summary)

    total_score = player_data.get("total_score", 0)
    total_stars, total_label = rate(total_score)
    squat_stars, _ = rate(squat_score)
    balance_stars, _ = rate(balance_score)
    reaction_stars, _ = rate(reaction_score)

    training_plan = generate_training_plan(squat_score, balance_score, reaction_score)

    # 找出最弱項目給建議
    scores = {"深蹲力量": squat_score, "平衡力": balance_score, "反應力": reaction_score}
    weakest = min(scores, key=scores.get)
    strongest = max(scores, key=scores.get)

    summary_text = (
        f"你的 {strongest} 最出色！"
        f"建議多加練習 {weakest}，7日訓練計劃可以幫到你！"
    )

    return {
        "total_score": total_score,
        "total_stars": total_stars,
        "total_label": total_label,
        "squat_stars": squat_stars,
        "squat_score": squat_score,
        "squat_tips": squat_tips,
        "balance_stars": balance_stars,
        "balance_score": balance_score,
        "balance_tips": balance_tips,
        "reaction_stars": reaction_stars,
        "reaction_score": reaction_score,
        "reaction_tips": reaction_tips,
        "summary_text": summary_text,
        "training_plan": training_plan
    }
