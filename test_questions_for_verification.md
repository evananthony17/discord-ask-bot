# Test Questions for Multi-Player Intent Detection Fix

## 🚫 Questions that SHOULD be BLOCKED (Multi-Player Intent)

### **Direct Comparisons with "or"**
1. `!ask who should I invest in caminero or Corey Seager`
2. `!ask should I start Harper or Trout today`
3. `!ask Soto or Judge for ROS`
4. `!ask who is better Acuna or Betts`
5. `!ask should I trade Cruz or keep Soto`

### **Direct Comparisons with "vs"**
6. `!ask Harper vs Trout who is better`
7. `!ask Ohtani vs Judge for fantasy`
8. `!ask Mookie vs Acuna ROS`
9. `!ask Tatis vs Lindor projection`

### **Direct Comparisons with "and"**
10. `!ask Judge and Ohtani outlook`
11. `!ask thoughts on Soto and Harper`
12. `!ask Acuna and Betts comparison`
13. `!ask between Judge and Trout who should I keep`

### **"Between" Constructions**
14. `!ask between Soto and Harper who is better`
15. `!ask between Judge and Ohtani who should I start`
16. `!ask choose between Acuna and Betts`

### **Multiple Players with Commas**
17. `!ask Soto, Harper, Trout rankings`
18. `!ask Judge, Ohtani, Acuna who to keep`
19. `!ask thoughts on Betts, Lindor, Tatis`

## ✅ Questions that SHOULD be ALLOWED

### **Single Player Questions**
20. `!ask Corey Seager stats`
21. `!ask Francisco Lindor projection`
22. `!ask how is Judge doing`
23. `!ask Ohtani outlook for ROS`
24. `!ask Soto update please`

### **"Or" with Non-Player Context (Should NOT be blocked)**
25. `!ask how is Corey or should I bench him`
26. `!ask is Harper playing or sitting today`
27. `!ask should I start Judge or sit him`
28. `!ask Trout update or any news`
29. `!ask Soto projection or should I trade`

### **Same Last Name Disambiguation (Should allow disambiguation)**
30. `!ask Suarez update` (multiple Suarez players - should show disambiguation)
31. `!ask how is Chapman doing` (multiple Chapman players)
32. `!ask Diaz projection` (multiple Diaz players)
33. `!ask thoughts on Rodriguez` (multiple Rodriguez players)

### **Questions with "and" but not comparisons**
34. `!ask Judge stats and projection`
35. `!ask Soto news and updates`
36. `!ask Harper injury and timeline`

## 🧪 Edge Cases to Test

### **Borderline Cases**
37. `!ask who should I pick up Caminero or someone else` (should be allowed - "someone else" not a player)
38. `!ask Harper or any other OF suggestions` (should be allowed - "any other OF" not specific player)
39. `!ask Soto trade value or hold` (should be allowed - "hold" not a player)

### **Complex Constructions**
40. `!ask if I have to choose between Soto and Harper who wins` (should be blocked)
41. `!ask Acuna vs Betts vs Judge who is best` (should be blocked - multiple players)
42. `!ask rank these players Soto Harper Trout` (should be blocked)

### **Punctuation Variations**
43. `!ask Harper/Trout comparison` (should be blocked)
44. `!ask Soto; Harper; who is better` (should be blocked)
45. `!ask Judge (Yankees) vs Ohtani (Dodgers)` (should be blocked)

## 📋 Expected Results Summary

**BLOCKED Queries (17 total):** 1-17, 40-45
- Should show message: "Your question appears to reference multiple players (Player1, Player2). Please ask about one player at a time."

**ALLOWED Single Player (6 total):** 20-24, 34-36
- Should proceed to normal question processing

**ALLOWED False Positive Prevention (5 total):** 25-29, 37-39
- Should proceed to normal question processing (intent detected but validation prevents blocking)

**ALLOWED Disambiguation (4 total):** 30-33
- Should show player selection prompt for same last name

## 🔍 How to Test

1. **Start the Discord bot**
2. **Go to the submission channel**
3. **Try each question above**
4. **Verify the expected behavior:**
   - BLOCKED = Message deleted + error message about multiple players
   - ALLOWED = Question posted to answering channel OR disambiguation prompt shown
   - DISAMBIGUATION = Selection prompt with multiple players with same last name

## 🎯 Key Test Cases for the Original Bug

**Most Important Tests:**
- Question #1: `!ask who should I invest in caminero or Corey Seager` 
  - **Before Fix**: Would be allowed (processed as single player)
  - **After Fix**: Should be BLOCKED (multi-player intent detected)

- Question #25: `!ask how is Corey or should I bench him`
  - **Should be ALLOWED**: "bench him" is not a player name

- Question #30: `!ask Suarez update`
  - **Should show DISAMBIGUATION**: Multiple Suarez players exist

This comprehensive test suite verifies that the intent-first detection system correctly identifies multi-player queries while preventing false positives and maintaining proper disambiguation functionality.
