from player_matching import has_multi_player_keywords

print("=== TESTING MULTI-PLAYER KEYWORD DETECTION ===")

test_queries = [
    "Soto;Edman;trout",
    "Judge,Ohtani,Harper", 
    "Soto/Harper/Trout",
    "Judge&Ohtani&Trout",
    "Soto (Yankees) vs Harper (Phillies)",
    "[Judge] and [Ohtani]",
    "Soto and Harper",
    "Judge vs Ohtani",
    "Harper or Trout",
    "Soto with Harper",
    "Juan Soto stats",  # Should NOT have keywords
    "How is Harper doing"  # Should NOT have keywords
]

for query in test_queries:
    has_keywords = has_multi_player_keywords(query)
    print(f"Query: '{query}'")
    print(f"Has multi-player keywords: {has_keywords}")
    print()
