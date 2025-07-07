from player_matching_validator import validate_player_mention_in_text
from utils import normalize_name

# Test the exact case from the logs
text = "Soto;Edman;trout"
player_name = "Juan Soto"

print(f"Testing validation:")
print(f"Text: '{text}'")
print(f"Player: '{player_name}'")

# Debug the normalization
text_normalized = normalize_name(text).lower()
player_normalized = normalize_name(player_name).lower()

print(f"Text normalized: '{text_normalized}'")
print(f"Player normalized: '{player_normalized}'")

# Debug the word splitting
text_words = text_normalized.split()
player_words = player_normalized.split()

print(f"Text words: {text_words}")
print(f"Player words: {player_words}")

# Debug the matching
matching_parts = sum(1 for part in player_words if part in text_words)
print(f"Matching parts: {matching_parts}")

# Test the validation
result = validate_player_mention_in_text(text, player_name)
print(f"Validation result: {result}")
