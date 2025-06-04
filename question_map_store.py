import json
import os

STORE_FILE = "question_map.json"

def load_question_map():
    if not os.path.exists(STORE_FILE):
        return {}
    with open(STORE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        # KEEP KEYS AS STRINGS!
        return data

def save_question_map(question_map):
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(question_map, f)

def append_question(question_map, key, value):
    question_map[str(key)] = value  # ENSURE KEY IS STRING
    save_question_map(question_map)