import json
import os

STORE_FILE = "question_map.json"

def load_question_map():
    if not os.path.exists(STORE_FILE):
        return {}
    with open(STORE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Convert keys back to int if needed
        return {int(k): v for k, v in data.items()}

def save_question_map(question_map):
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(question_map, f)

def append_question(question_map, key, value):
    question_map[key] = value
    save_question_map(question_map)