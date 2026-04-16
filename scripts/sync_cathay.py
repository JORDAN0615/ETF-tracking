"""入口點：執行國泰對帳單同步"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.cathay_sync import run

if __name__ == "__main__":
    run()
