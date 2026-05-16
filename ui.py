"""
ui.py
主介面 - Tkinter GUI，管理整個 booth 體驗流程
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import time
import cv2
from PIL import Image, ImageTk

from pose_detector import SquatDetector, BalanceDetector
from data_store import save_player, get_rank, get_age_percentile, get_leaderboard
from feedback_engine import generate_full_feedback
from report_generator import generate_report


# ── 顏色主題 ──
BG = "#0d1b2a"
CARD = "#1b2838"
GREEN = "#1db954"
YELLOW = "#f5c518"
WHITE = "#ffffff"
GREY = "#aaaaaa"
RED = "#e05252"


class AICoachApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🏃 AI 體能教練 Booth")
        self.configure(bg=BG)
        self.geometry("1100x720")
        self.resizable(True, True)

        self.player_name = tk.StringVar()
        self.player_age = tk.StringVar(value="10")
        self.player_class = tk.StringVar()

        self.squat_detector = None
        self.balance_detector = None
        self.cap = None
        self.camera_running = False
        self.current_phase = None  # "squat" | "balance" | "reaction"
        self.squat_result = None
        self.balance_result = None
        self.reaction_result = None
        self.reaction_start = None
        self.reaction_active = False
        self.reaction_times = []

        self._build_fonts()
        self._show_welcome()

    def _build_fonts(self):
        self.font_title = tkfont.Font(family="PingFang TC", size=28, weight="bold")
        self.font_h2 = tkfont.Font(family="PingFang TC", size=18, weight="bold")
        self.font_body = tkfont.Font(family="PingFang TC", size=13)
        self.font_small = tkfont.Font(family="PingFang TC", size=11)
        self.font_score = tkfont.Font(family="PingFang TC", size=40, weight="bold")

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    # ════════════════════════════════════
    # 歡迎頁
    # ════════════════════════════════════
    def _show_welcome(self):
        self._clear()
        self._stop_camera()

        frame = tk.Frame(self, bg=BG)
        frame.pack(expand=True)

        tk.Label(frame, text="🏃 AI 體能教練", font=self.font_title,
                 bg=BG, fg=GREEN).pack(pady=(40, 10))
        tk.Label(frame, text="STEAM in PE 體育科學體驗站",
                 font=self.font_h2, bg=BG, fg=WHITE).pack(pady=5)
        tk.Label(frame, text="測試你的深蹲 · 平衡力 · 反應力\n獲取個人化訓練報告！",
                 font=self.font_body, bg=BG, fg=GREY, justify="center").pack(pady=20)

        # 輸入欄
        input_frame = tk.Frame(frame, bg=CARD, padx=30, pady=25)
        input_frame.pack(pady=20, padx=40, fill="x")

        self._labeled_entry(input_frame, "你的名字：", self.player_name, 0)
        self._labeled_entry(input_frame, "年齡：", self.player_age, 1)
        self._labeled_entry(input_frame, "班別（如 5A）：", self.player_class, 2)

        tk.Button(frame, text="▶  開始挑戰！", font=self.font_h2,
                  bg=GREEN, fg=WHITE, relief="flat", padx=30, pady=12,
                  cursor="hand2", command=self._start_squat).pack(pady=20)

        # 排行榜預覽
        self._mini_leaderboard(frame)

    def _labeled_entry(self, parent, label, var, row):
        tk.Label(parent, text=label, font=self.font_body, bg=CARD, fg=WHITE,
                 anchor="w").grid(row=row, column=0, sticky="w", pady=6, padx=(0, 15))
        tk.Entry(parent, textvariable=var, font=self.font_body, width=20,
                 bg="#2a3a4a", fg=WHITE, insertbackground=WHITE,
                 relief="flat").grid(row=row, column=1, sticky="w", pady=6)

    def _mini_leaderboard(self, parent):
        lb = get_leaderboard(5)
        if not lb:
            return
        frame = tk.Frame(parent, bg=CARD, padx=20, pady=15)
        frame.pack(pady=10, padx=40, fill="x")
        tk.Label(frame, text="🏆 排行榜 Top 5", font=self.font_body,
                 bg=CARD, fg=YELLOW).pack(anchor="w")
        for i, row in enumerate(lb, 1):
            name, cls, total, _, _, _, _ = row
            tk.Label(frame, text=f"  {i}. {name} ({cls})  ─  {total} 分",
                     font=self.font_small, bg=CARD, fg=WHITE).pack(anchor="w")

    # ════════════════════════════════════
    # 深蹲關卡
    # ════════════════════════════════════
    def _start_squat(self):
        name = self.player_name.get().strip()
        if not name:
            self._toast("請先輸入你的名字！")
            return

        self._clear()
        self.squat_detector = SquatDetector()
        self._show_phase_ui(
            title="第一關：深蹲挑戰",
            instructions="站在鏡頭前，準備好就按「開始」！\n10秒內盡量做多幾個標準深蹲！",
            btn_text="開始深蹲計時！",
            btn_cmd=self._begin_squat_timer,
            phase="squat"
        )

    def _begin_squat_timer(self):
        self.squat_detector.start_timer(10)
        self._squat_timer_check()

    def _squat_timer_check(self):
        if self.squat_detector and self.squat_detector.time_left() <= 0:
            self.squat_result = self.squat_detector.get_summary()
            self._stop_camera()
            self._start_balance()
        else:
            self.after(200, self._squat_timer_check)

    # ════════════════════════════════════
    # 平衡力關卡
    # ════════════════════════════════════
    def _start_balance(self):
        self._clear()
        self.balance_detector = BalanceDetector()
        self._show_phase_ui(
            title="第二關：平衡力挑戰",
            instructions="單腳站立，維持越久越好！\n按「開始」後有 15 秒時間。",
            btn_text="開始平衡測試！",
            btn_cmd=self._begin_balance_timer,
            phase="balance"
        )

    def _begin_balance_timer(self):
        self._balance_end_time = time.time() + 15
        self._balance_timer_check()

    def _balance_timer_check(self):
        if time.time() >= self._balance_end_time:
            self.balance_result = self.balance_detector.get_summary()
            self._stop_camera()
            self._start_reaction()
        else:
            self.after(200, self._balance_timer_check)

    # ════════════════════════════════════
    # 反應力關卡
    # ════════════════════════════════════
    def _start_reaction(self):
        self._clear()
        self._stop_camera()
        self.reaction_times = []
        self.current_phase = "reaction"

        frame = tk.Frame(self, bg=BG)
        frame.pack(expand=True, fill="both")

        tk.Label(frame, text="第三關：反應力測試",
                 font=self.font_title, bg=BG, fg=GREEN).pack(pady=20)
        tk.Label(frame, text="看到綠燈就立刻按空格鍵！共 5 次",
                 font=self.font_body, bg=BG, fg=WHITE).pack()

        self.reaction_light = tk.Label(frame, text="⬛", font=tkfont.Font(size=100),
                                       bg=BG, fg=GREY)
        self.reaction_light.pack(pady=30)

        self.reaction_info = tk.Label(frame, text="準備好了嗎？",
                                      font=self.font_h2, bg=BG, fg=WHITE)
        self.reaction_info.pack()

        self.reaction_times_label = tk.Label(frame, text="",
                                             font=self.font_body, bg=BG, fg=YELLOW)
        self.reaction_times_label.pack(pady=10)

        self.bind("<space>", self._on_spacebar)
        self.after(1500, self._reaction_next_round)

    def _reaction_next_round(self):
        if len(self.reaction_times) >= 5:
            self.unbind("<space>")
            avg = sum(self.reaction_times) / len(self.reaction_times)
            score = max(0, round(100 - (avg - 0.15) * 400))
            score = min(100, max(0, score))
            self.reaction_result = {"reaction_time": round(avg, 3), "score": score}
            self._show_results()
            return

        self.reaction_active = False
        self.reaction_light.config(text="⬛", fg=GREY)
        self.reaction_info.config(text=f"注意！第 {len(self.reaction_times)+1} 次")
        # 隨機延遲 1-3 秒後亮燈
        delay = int((1 + 2 * __import__("random").random()) * 1000)
        self.after(delay, self._reaction_light_on)

    def _reaction_light_on(self):
        self.reaction_light.config(text="🟢", fg=GREEN)
        self.reaction_start = time.time()
        self.reaction_active = True
        # 2秒內沒反應算超時
        self.after(2000, self._reaction_timeout)

    def _reaction_timeout(self):
        if self.reaction_active:
            self.reaction_active = False
            self.reaction_times.append(2.0)
            self.reaction_light.config(text="⏰", fg=RED)
            self.reaction_info.config(text="太慢了！")
            self.after(800, self._reaction_next_round)

    def _on_spacebar(self, event):
        if self.reaction_active:
            rt = time.time() - self.reaction_start
            self.reaction_active = False
            self.reaction_times.append(rt)
            self.reaction_light.config(text="✅", fg=GREEN)
            self.reaction_info.config(text=f"反應時間：{rt:.3f} 秒！")
            times_text = "  ".join([f"{t:.3f}s" for t in self.reaction_times])
            self.reaction_times_label.config(text=times_text)
            self.after(800, self._reaction_next_round)
        elif self.current_phase == "reaction":
            self.reaction_light.config(text="❌", fg=RED)
            self.reaction_info.config(text="等綠燈！")

    # ════════════════════════════════════
    # 相機共用 UI
    # ════════════════════════════════════
    def _show_phase_ui(self, title, instructions, btn_text, btn_cmd, phase):
        self.current_phase = phase
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True)

        # 左側：相機
        left = tk.Frame(main, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        tk.Label(left, text=title, font=self.font_h2, bg=BG, fg=GREEN).pack(pady=5)
        self.camera_label = tk.Label(left, bg="black")
        self.camera_label.pack(fill="both", expand=True)

        # 右側：資訊面板
        right = tk.Frame(main, bg=CARD, width=280)
        right.pack(side="right", fill="y", padx=10, pady=10)
        right.pack_propagate(False)

        tk.Label(right, text=instructions, font=self.font_small,
                 bg=CARD, fg=WHITE, wraplength=250, justify="center").pack(pady=20, padx=10)

        tk.Button(right, text=btn_text, font=self.font_body,
                  bg=GREEN, fg=WHITE, relief="flat", padx=15, pady=10,
                  cursor="hand2", command=btn_cmd).pack(pady=10)

        # 即時數據標籤
        self.live_label = tk.Label(right, text="", font=self.font_body,
                                   bg=CARD, fg=YELLOW, wraplength=250, justify="left")
        self.live_label.pack(pady=10, padx=10)

        # 啟動相機
        self._start_camera(phase)

    def _start_camera(self, phase):
        self.camera_running = True
        self.cap = cv2.VideoCapture(0)
        self._update_camera(phase)

    def _update_camera(self, phase):
        if not self.camera_running or self.cap is None:
            return
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            if phase == "squat" and self.squat_detector:
                annotated, result = self.squat_detector.process_frame(frame)
                self.live_label.config(
                    text=f"深蹲次數：{result['count']}\n"
                         f"標準次數：{result['correct_count']}\n"
                         f"剩餘時間：{int(result['time_left'])}s\n"
                         f"{result.get('feedback', '')}"
                )
            elif phase == "balance" and self.balance_detector:
                annotated, result = self.balance_detector.process_frame(frame)
                self.live_label.config(
                    text=f"目前：{result['current_time']}s\n"
                         f"最佳：{result['best_time']}s\n"
                         f"{result.get('feedback', '')}"
                )
            else:
                annotated = frame

            # 顯示到 tkinter
            img = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            img = img.resize((640, 480))
            photo = ImageTk.PhotoImage(img)
            self.camera_label.config(image=photo)
            self.camera_label.image = photo

        if self.camera_running:
            self.after(30, lambda: self._update_camera(phase))

    def _stop_camera(self):
        self.camera_running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    # ════════════════════════════════════
    # 結果頁
    # ════════════════════════════════════
    def _show_results(self):
        self._clear()
        self._stop_camera()

        name = self.player_name.get().strip() or "同學"
        age = int(self.player_age.get()) if self.player_age.get().isdigit() else 10
        class_name = self.player_class.get().strip() or "未知"

        squat = self.squat_result or {"total_squats": 0, "correct_squats": 0,
                                      "accuracy": 0, "avg_knee_angle": 90, "score": 0}
        balance = self.balance_result or {"best_balance_time": 0, "score": 0}
        reaction = self.reaction_result or {"reaction_time": 0.3, "score": 50}

        # 儲存到資料庫
        player_id = save_player(name, age, class_name, squat, balance, reaction)
        rank, total = get_rank(player_id)
        percentile = get_age_percentile(player_id)

        from data_store import get_player
        player_data = get_player(player_id)
        feedback = generate_full_feedback(player_data)

        # ── UI ──
        canvas = tk.Frame(self, bg=BG)
        canvas.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(canvas, text=f"🎉 {name}，你的成績出爐了！",
                 font=self.font_title, bg=BG, fg=GREEN).pack(pady=(10, 5))

        # 總分卡片
        score_frame = tk.Frame(canvas, bg=CARD, padx=30, pady=20)
        score_frame.pack(pady=5)
        tk.Label(score_frame, text=str(feedback["total_score"]),
                 font=self.font_score, bg=CARD, fg=GREEN).grid(row=0, column=0, rowspan=2, padx=20)
        tk.Label(score_frame, text="綜合分數", font=self.font_body, bg=CARD, fg=GREY).grid(row=0, column=1, sticky="w")
        tk.Label(score_frame, text=f"{feedback['total_stars']}  {feedback['total_label']}",
                 font=self.font_h2, bg=CARD, fg=YELLOW).grid(row=1, column=1, sticky="w")
        if rank and total:
            tk.Label(score_frame, text=f"全場第 {rank} 名（共 {total} 人）",
                     font=self.font_body, bg=CARD, fg=WHITE).grid(row=0, column=2, padx=20)
        if percentile:
            tk.Label(score_frame, text=f"超越同齡 {percentile}% 的人！",
                     font=self.font_body, bg=CARD, fg=GREEN).grid(row=1, column=2, padx=20)

        # 三項目分數
        items_frame = tk.Frame(canvas, bg=BG)
        items_frame.pack(pady=10)
        items = [
            ("深蹲力量", feedback["squat_stars"], feedback["squat_score"]),
            ("平衡力", feedback["balance_stars"], feedback["balance_score"]),
            ("反應力", feedback["reaction_stars"], feedback["reaction_score"]),
        ]
        for label, stars, score in items:
            card = tk.Frame(items_frame, bg=CARD, padx=20, pady=15)
            card.pack(side="left", padx=10)
            tk.Label(card, text=label, font=self.font_body, bg=CARD, fg=GREY).pack()
            tk.Label(card, text=stars, font=self.font_body, bg=CARD, fg=YELLOW).pack()
            tk.Label(card, text=f"{score}分", font=self.font_h2, bg=CARD, fg=WHITE).pack()

        # AI 建議
        tk.Label(canvas, text="AI 教練說：", font=self.font_body, bg=BG, fg=GREY).pack(anchor="w", padx=30)
        tk.Label(canvas, text=feedback["summary_text"], font=self.font_body,
                 bg=BG, fg=WHITE, wraplength=900, justify="left").pack(anchor="w", padx=30)

        # 訓練建議摘要（顯示第一天）
        plan = feedback.get("training_plan", {})
        first_day = list(plan.keys())[0] if plan else ""
        if first_day:
            tk.Label(canvas, text=f"今日建議（{first_day}）：",
                     font=self.font_body, bg=BG, fg=GREY).pack(anchor="w", padx=30, pady=(10, 2))
            for ex in plan[first_day]:
                tk.Label(canvas, text=f"  • {ex}", font=self.font_small,
                         bg=BG, fg=GREEN).pack(anchor="w", padx=30)

        # 按鈕
        btn_frame = tk.Frame(canvas, bg=BG)
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="📄 生成完整 PDF 報告",
                  font=self.font_body, bg="#336699", fg=WHITE, relief="flat",
                  padx=15, pady=8, cursor="hand2",
                  command=lambda: self._generate_pdf(player_data, feedback, rank, total, percentile)
                  ).pack(side="left", padx=10)

        tk.Button(btn_frame, text="🔄 下一位挑戰者",
                  font=self.font_body, bg=GREEN, fg=WHITE, relief="flat",
                  padx=15, pady=8, cursor="hand2",
                  command=self._reset).pack(side="left", padx=10)

    def _generate_pdf(self, player_data, feedback, rank, total, percentile):
        self._toast("正在生成 PDF...")
        threading.Thread(
            target=self._pdf_thread,
            args=(player_data, feedback, rank, total, percentile),
            daemon=True
        ).start()

    def _pdf_thread(self, player_data, feedback, rank, total, percentile):
        try:
            path = generate_report(player_data, feedback, rank, total, percentile)
            self.after(0, lambda: self._toast(f"PDF 已儲存！\n{path}"))
            import subprocess
            subprocess.Popen(["open", path])
        except Exception as e:
            self.after(0, lambda: self._toast(f"生成失敗：{e}"))

    def _reset(self):
        self.player_name.set("")
        self.player_age.set("10")
        self.player_class.set("")
        self.squat_result = None
        self.balance_result = None
        self.reaction_result = None
        self.reaction_times = []
        self._show_welcome()

    def _toast(self, msg):
        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.configure(bg=CARD)
        tk.Label(toast, text=msg, font=self.font_body, bg=CARD, fg=WHITE,
                 padx=20, pady=15, wraplength=400).pack()
        # 置中
        self.update_idletasks()
        x = self.winfo_x() + self.winfo_width() // 2 - 200
        y = self.winfo_y() + self.winfo_height() // 2 - 50
        toast.geometry(f"+{x}+{y}")
        toast.after(3000, toast.destroy)

    def on_close(self):
        self._stop_camera()
        self.destroy()
