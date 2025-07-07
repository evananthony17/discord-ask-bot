from player_matching import has_multi_player_keywords

print("=== TESTING CONTEXT-AWARE MULTI-PLAYER KEYWORD DETECTION ===")

test_queries = [
    # Should be detected as multi-player (separating players)
    "Soto;Edman;trout",
    "Judge,Ohtani,Harper", 
    "Soto/Harper/Trout",
    "Judge&Ohtani&Trout",
    "Soto (Yankees) vs Harper (Phillies)",
    "[Judge] and [Ohtani]",
    "Soto and Harper",
    "Judge vs Ohtani",
    
    # Should NOT be detected as multi-player (commentary/clarification)
    "How is Juan Soto doing (I haven't been paying attention recently)",
    "Juan Soto stats (looking for projections)",
    "Harper performance (he's been struggling lately)",
    "Soto update (I've been watching him)",
    "Judge numbers (what do you think)",
    "Ohtani projections (I need help)",
    "Trout analysis (can you help me understand)",
    
    # Edge cases
    "Juan Soto stats",  # Should NOT have keywords
    "How is Harper doing",  # Should NOT have keywords
    "Soto, but I haven't been following",  # Should NOT (commentary after comma)
    "Judge, Ohtani, Harper stats",  # Should be multi-player (player names)
]

for query in test_queries:
    has_keywords = has_multi_player_keywords(query)
    expected = "MULTI-PLAYER" if has_keywords else "SINGLE-PLAYER"
    print(f"Query: '{query}'")
    print(f"Result: {expected}")
    print()
