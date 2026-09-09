# database/db.py
import sqlite3
from datetime import datetime

DB_PATH = "database/compound.db"


def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT NOT NULL,
            vehicle_type TEXT,
            brand TEXT,
            color TEXT,
            entry_time TEXT,
            exit_time TEXT
        )
    """)

    conn.commit()
    conn.close()


def register_entry(plate, vehicle_type, brand, color):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO vehicles (plate, vehicle_type, brand, color, entry_time) VALUES (?, ?, ?, ?, ?)",
        (plate, vehicle_type, brand, color, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()


def register_exit(plate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE vehicles SET exit_time = ? WHERE plate = ? AND exit_time IS NULL",
        (datetime.now().strftime("%Y-%m-%d %H:%M"), plate)
    )
    conn.commit()
    conn.close()