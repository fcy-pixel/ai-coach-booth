"""
pose_detector.py
AI 姿勢偵測模組 - 深蹲評分 + 平衡力測試
使用 MediaPipe Tasks API (v0.10+)
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import os

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision import drawing_utils as mp_drawing
from mediapipe.tasks.python.vision import drawing_styles as mp_drawing_styles

MODEL_PATH = os.path.join(os.path.dirname(__file__), "pose_landmarker.task")

# 關節索引（MediaPipe Pose Landmarker）
_LEFT_HIP = 23
_LEFT_KNEE = 25
_LEFT_ANKLE = 27
_RIGHT_HIP = 24
_RIGHT_KNEE = 26
_RIGHT_ANKLE = 28
_LEFT_SHOULDER = 11
_RIGHT_SHOULDER = 12


def calculate_angle(a, b, c):
    """計算三點之間的角度（以 b 為頂點）"""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - \
              np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle


def get_squat_feedback(knee_angle, hip_angle):
    """根據角度給出深蹲姿勢評語"""
    if knee_angle < 70:
        return "太深！膝蓋超過腳趾", False
    elif knee_angle > 130:
        return "再蹲低一點！", False
    elif hip_angle < 60:
        return "上身太前傾！", False
    else:
        return "完美深蹲！", True


def _make_landmarker(running_mode):
    """建立 PoseLandmarker，支援 IMAGE 或 VIDEO 模式"""
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=running_mode,
        min_pose_detection_confidence=0.6,
        min_tracking_confidence=0.6,
        num_poses=1
    )
    return mp_vision.PoseLandmarker.create_from_options(options)


def _draw_pose_landmarks(image, pose_landmarks_list):
    """在影像上繪製骨架（使用 MediaPipe Tasks API）"""
    connections = mp_vision.PoseLandmarkerResult.__annotations__  # dummy
    landmark_style = mp_drawing_styles.get_default_pose_landmarks_style()
    for pose_landmarks in pose_landmarks_list:
        mp_drawing.draw_landmarks(
            image,
            pose_landmarks,
            mp_vision.pose_landmarker.PoseLandmarksConnections.POSE_LANDMARKS,
            landmark_drawing_spec=landmark_style
        )


class SquatDetector:
    """深蹲偵測器 - 計算深蹲次數和姿勢評分"""

    def __init__(self):
        self.landmarker = _make_landmarker(mp_vision.RunningMode.VIDEO)
        self._frame_ts = 0
        self.reset()

    def reset(self):
        self.count = 0
        self.stage = None  # "up" or "down"
        self.correct_count = 0
        self.feedback = ""
        self.knee_angles = []
        self.start_time = None
        self.duration = 10

    def start_timer(self, duration=10):
        self.start_time = time.time()
        self.duration = duration

    def time_left(self):
        if self.start_time is None:
            return self.duration
        return max(0, self.duration - (time.time() - self.start_time))

    def process_frame(self, frame):
        """
        處理一幀影像，返回：
        - annotated_frame: 帶有骨架和資訊的影像
        - result: dict 包含 count, correct_count, feedback, knee_angle
        """
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        self._frame_ts += 33  # 模擬 ~30fps 時間戳
        detection = self.landmarker.detect_for_video(mp_image, self._frame_ts)

        result = {
            "count": self.count,
            "correct_count": self.correct_count,
            "feedback": self.feedback,
            "knee_angle": None,
            "detected": False,
            "time_left": self.time_left()
        }

        annotated = frame.copy()

        if detection.pose_landmarks:
            result["detected"] = True
            lms = detection.pose_landmarks[0]

            hip = [lms[_LEFT_HIP].x, lms[_LEFT_HIP].y]
            knee = [lms[_LEFT_KNEE].x, lms[_LEFT_KNEE].y]
            ankle = [lms[_LEFT_ANKLE].x, lms[_LEFT_ANKLE].y]
            shoulder = [lms[_LEFT_SHOULDER].x, lms[_LEFT_SHOULDER].y]

            knee_angle = calculate_angle(hip, knee, ankle)
            hip_angle = calculate_angle(shoulder, hip, knee)
            result["knee_angle"] = round(knee_angle, 1)

            # 深蹲計數邏輯
            if knee_angle > 160:
                self.stage = "up"
            if knee_angle < 90 and self.stage == "up":
                self.stage = "down"
                self.count += 1
                feedback_text, is_correct = get_squat_feedback(knee_angle, hip_angle)
                self.feedback = feedback_text
                if is_correct:
                    self.correct_count += 1
                self.knee_angles.append(knee_angle)

            result["count"] = self.count
            result["correct_count"] = self.correct_count
            result["feedback"] = self.feedback

            # 畫骨架
            _draw_pose_landmarks(annotated, detection.pose_landmarks)

            # 顯示膝蓋角度
            knee_px = (int(knee[0] * w), int(knee[1] * h))
            cv2.putText(annotated, f"{round(knee_angle)}°",
                        knee_px, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        self._draw_hud(annotated, result)
        return annotated, result

    def _draw_hud(self, image, result):
        h, w, _ = image.shape
        # 背景框
        cv2.rectangle(image, (0, 0), (300, 160), (0, 0, 0), -1)
        cv2.rectangle(image, (0, 0), (300, 160), (0, 200, 100), 2)

        cv2.putText(image, f"深蹲次數: {result['count']}", (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(image, f"標準次數: {result['correct_count']}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 100), 2)

        # 計時器
        time_left = result["time_left"]
        color = (0, 255, 0) if time_left > 5 else (0, 0, 255)
        cv2.putText(image, f"剩餘: {int(time_left)}s", (10, 105),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        # 姿勢 feedback
        fb = result["feedback"]
        if fb:
            fb_color = (0, 255, 100) if "完美" in fb else (0, 100, 255)
            cv2.putText(image, fb, (10, 140),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, fb_color, 2)

    def get_score(self):
        """計算最終深蹲分數 (0-100)"""
        if self.count == 0:
            return 0
        accuracy = self.correct_count / self.count
        count_score = min(self.count * 5, 50)  # 最多50分（10次）
        accuracy_score = accuracy * 50           # 最多50分
        return round(count_score + accuracy_score)

    def get_summary(self):
        avg_angle = round(np.mean(self.knee_angles), 1) if self.knee_angles else 0
        return {
            "total_squats": self.count,
            "correct_squats": self.correct_count,
            "accuracy": round(self.correct_count / self.count * 100) if self.count else 0,
            "avg_knee_angle": avg_angle,
            "score": self.get_score()
        }


class BalanceDetector:
    """平衡力偵測器 - 單腳站立計時"""

    def __init__(self):
        self.landmarker = _make_landmarker(mp_vision.RunningMode.VIDEO)
        self._frame_ts = 0
        self.reset()

    def reset(self):
        self.balance_start = None
        self.best_balance_time = 0
        self.current_balance_time = 0
        self.is_balancing = False
        self.feedback = "請單腳站立！"

    def process_frame(self, frame):
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        self._frame_ts += 33
        detection = self.landmarker.detect_for_video(mp_image, self._frame_ts)

        result = {
            "balancing": False,
            "current_time": 0,
            "best_time": self.best_balance_time,
            "feedback": self.feedback
        }

        annotated = frame.copy()

        if detection.pose_landmarks:
            lms = detection.pose_landmarks[0]

            left_hip_y = lms[_LEFT_HIP].y
            right_hip_y = lms[_RIGHT_HIP].y
            left_knee_y = lms[_LEFT_KNEE].y
            right_knee_y = lms[_RIGHT_KNEE].y

            # 判斷單腳：一隻腳的膝蓋明顯高於臀部
            one_leg_raised = (left_knee_y < left_hip_y - 0.05) or \
                             (right_knee_y < right_hip_y - 0.05)

            if one_leg_raised:
                if not self.is_balancing:
                    self.balance_start = time.time()
                    self.is_balancing = True
                self.current_balance_time = round(time.time() - self.balance_start, 1)
                if self.current_balance_time > self.best_balance_time:
                    self.best_balance_time = self.current_balance_time
                self.feedback = f"保持！{self.current_balance_time}s"
                result["balancing"] = True
            else:
                if self.is_balancing:
                    self.is_balancing = False
                self.feedback = "請單腳站立！"

            result["current_time"] = self.current_balance_time
            result["best_time"] = self.best_balance_time
            result["feedback"] = self.feedback

            _draw_pose_landmarks(annotated, detection.pose_landmarks)

        self._draw_hud(annotated, result)
        return annotated, result

    def _draw_hud(self, image, result):
        cv2.rectangle(image, (0, 0), (320, 120), (0, 0, 0), -1)
        cv2.rectangle(image, (0, 0), (320, 120), (200, 100, 0), 2)
        cv2.putText(image, f"目前: {result['current_time']}s", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 200, 0), 2)
        cv2.putText(image, f"最佳: {result['best_time']}s", (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 200), 2)
        cv2.putText(image, result["feedback"], (10, 115),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    def get_score(self):
        """平衡力分數 (0-100)"""
        return min(round(self.best_balance_time * 5), 100)

    def get_summary(self):
        return {
            "best_balance_time": self.best_balance_time,
            "score": self.get_score()
        }
