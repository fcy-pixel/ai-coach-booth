"""
main.py
程式入口點
"""

from ui import AICoachApp

if __name__ == "__main__":
    app = AICoachApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
