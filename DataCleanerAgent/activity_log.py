"""Keeps a diary of everything the cleaner does, so nothing happens silently."""
from datetime import datetime

import pandas as pd


class ChangeLog:
    def __init__(self):
        self.rows = []
        self.context = ""   # e.g. "lookup table" while the second file is being cleaned

    def add(self, step, action, details="", rows_affected=0):
        if self.context:
            details = f"[{self.context}] {details}"
        self.rows.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "step": step,
            "action": action,
            "details": details,
            "rows_affected": int(rows_affected),
        })

    def to_frame(self):
        columns = ["time", "step", "action", "details", "rows_affected"]
        return pd.DataFrame(self.rows, columns=columns)
