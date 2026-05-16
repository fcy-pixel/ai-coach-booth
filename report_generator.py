"""
report_generator.py
生成 PDF 報告 + QR Code（讓訪客掃碼帶走）
"""

import qrcode
import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _try_register_font():
    """嘗試註冊支援中文的字型"""
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("Chinese", path))
                return "Chinese"
            except Exception:
                continue
    return "Helvetica"


def generate_qr_code(player_id, player_name):
    """生成包含玩家資訊的 QR Code 圖片，返回圖片 bytes"""
    data = (
        f"AI體能教練報告\n"
        f"姓名: {player_name}\n"
        f"ID: {player_id}\n"
        f"日期: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"到 Booth 查看你的排名！"
    )
    qr = qrcode.QRCode(version=2, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generate_report(player_data, feedback, rank=None, total_players=None, percentile=None):
    """
    生成完整 PDF 報告
    返回 PDF 檔案路徑
    """
    font_name = _try_register_font()

    player_id = player_data.get("id", 0)
    name = player_data.get("name", "同學")
    filename = f"report_{player_id}_{name}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm
    )

    styles = getSampleStyleSheet()

    def style(name_s, size=12, bold=False, color=colors.black, align=TA_LEFT):
        return ParagraphStyle(
            name_s, fontName=font_name,
            fontSize=size, textColor=color,
            alignment=align,
            leading=size * 1.4,
            spaceAfter=4,
            bold=bold
        )

    title_style = style("title", 22, bold=True, color=colors.HexColor("#1a7a4a"), align=TA_CENTER)
    subtitle_style = style("subtitle", 13, color=colors.HexColor("#555555"), align=TA_CENTER)
    section_style = style("section", 14, bold=True, color=colors.HexColor("#1a7a4a"))
    body_style = style("body", 11)
    tip_style = style("tip", 10, color=colors.HexColor("#336699"))

    story = []

    # ── 標題 ──
    story.append(Paragraph("🏃 AI 體能教練報告", title_style))
    story.append(Paragraph(f"{name} 同學的運動能力分析", subtitle_style))
    story.append(Spacer(1, 0.4 * cm))

    # ── 總分 ──
    total = feedback.get("total_score", 0)
    total_label = feedback.get("total_label", "")
    total_stars = feedback.get("total_stars", "")

    score_data = [
        ["總體評級", f"{total_stars}  {total_label}"],
        ["綜合分數", f"{total} / 100 分"],
    ]
    if rank and total_players:
        score_data.append(["全場排名", f"第 {rank} 名（共 {total_players} 人）"])
    if percentile:
        score_data.append(["同齡百分位", f"超越了 {percentile}% 的同齡人！"])

    score_table = Table(score_data, colWidths=[5 * cm, 11 * cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f5e9")),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── 各項目分數 ──
    story.append(Paragraph("各項目成績", section_style))

    items = [
        ("深蹲力量", feedback.get("squat_stars", ""), feedback.get("squat_score", 0),
         f"共 {player_data.get('squat_count', 0)} 次，標準率 {player_data.get('squat_accuracy', 0)}%"),
        ("平衡力", feedback.get("balance_stars", ""), feedback.get("balance_score", 0),
         f"最長單腳站 {player_data.get('balance_time', 0):.1f} 秒"),
        ("反應力", feedback.get("reaction_stars", ""), feedback.get("reaction_score", 50),
         f"反應時間 {player_data.get('reaction_time', 0.3):.3f} 秒"),
    ]

    item_data = [["項目", "評級", "分數", "詳情"]]
    for label, stars, score, detail in items:
        item_data.append([label, stars, f"{score}分", detail])

    item_table = Table(item_data, colWidths=[3.5 * cm, 4 * cm, 2.5 * cm, 6 * cm])
    item_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a7a4a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0faf4")]),
        ("PADDING", (0, 0), (-1, -1), 7),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── 個人化分析 ──
    story.append(Paragraph("AI 教練分析", section_style))
    story.append(Paragraph(feedback.get("summary_text", ""), body_style))
    story.append(Spacer(1, 0.3 * cm))

    all_tips = (
        feedback.get("squat_tips", []) +
        feedback.get("balance_tips", []) +
        feedback.get("reaction_tips", [])
    )
    for tip in all_tips:
        story.append(Paragraph(f"• {tip}", tip_style))
    story.append(Spacer(1, 0.5 * cm))

    # ── 7日訓練計劃 ──
    story.append(Paragraph("你的個人化 7 日訓練計劃", section_style))
    training_plan = feedback.get("training_plan", {})
    for day, exercises in training_plan.items():
        story.append(Paragraph(f"▶ {day}", style("day", 11, bold=True, color=colors.HexColor("#336633"))))
        for ex in exercises:
            story.append(Paragraph(f"   - {ex}", tip_style))
        story.append(Spacer(1, 0.15 * cm))

    story.append(Spacer(1, 0.5 * cm))

    # ── QR Code ──
    story.append(Paragraph("掃描 QR Code 帶走報告", section_style))
    qr_buf = generate_qr_code(player_id, name)
    qr_img = Image(qr_buf, width=4 * cm, height=4 * cm)
    story.append(qr_img)

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        f"報告日期：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}",
        style("footer", 9, color=colors.grey, align=TA_CENTER)
    ))

    doc.build(story)
    return filepath
