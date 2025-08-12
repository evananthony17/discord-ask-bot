# 🤖 Discord Baseball Bot - System Wireframe & Architecture

## 📋 Overview
This Discord bot helps baseball fans ask questions about specific players and routes them to expert channels for answers. It's designed to prevent spam, ensure single-player focus, and provide a smooth Q&A experience.

---

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DISCORD BASEBALL BOT                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Types: !ask How is Alex Bregman doing?                   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 SUBMISSION CHANNEL                      │   │
│  │                (#ask-questions)                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   BOT PROCESSING                        │   │
│  │                                                         │   │
│  │  1. Question Validation                                 │   │
│  │  2. Player Detection                                    │   │
│  │  3. Multi-Player Check                                  │   │
│  │  4. Recent Mention Check                                │   │
│  │  5. Profanity Filter                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                    ┌──────┴──────┐                             │
│                    ▼             ▼                             │
│  ┌─────────────────────┐ ┌─────────────────────┐               │
│  │    APPROVED         │ │      BLOCKED        │               │
│  │   (Single Player)   │ │   (Multi/Invalid)   │               │
│  └─────────────────────┘ └─────────────────────┘               │
│            │                        │                          │
│            ▼                        ▼                          │
│  ┌─────────────────────┐ ┌─────────────────────┐               │
│  │  ANSWERING CHANNEL  │ │   ERROR MESSAGE     │               │
│  │   (#questions)      │ │  (Auto-deleted)     │               │
│  └─────────────────────┘ └─────────────────────┘               │
│            │                                                   │
│            ▼                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                EXPERT ANSWERS                           │   │
│  │                                                         │   │
│  │  Expert replies to question in answering channel       │   │
│  └─────────────────────────────────────────────────────────┘   │
│            │                                                   │
│            ▼                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              FINAL ANSWER CHANNEL                       │   │
│  │                (#final-answers)                         │   │
│  │                                                         │   │
│  │  "User asked: How is Alex Bregman doing?"               │   │
│  │  "Expert replied: He's been hitting well lately..."     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Detailed Flow Diagram

```
USER INPUT: !ask How is Alex Bregman doing?
│
├─ CHANNEL CHECK ──────────────────────────────────────┐
│  │                                                   │
│  ├─ ✅ Submission Channel (#ask-questions)           │
│  └─ ❌ Wrong Channel → Delete + Error Message        │
│                                                      │
├─ BASIC VALIDATION ───────────────────────────────────┤
│  │                                                   │
│  ├─ ✅ Question provided                             │
│  ├─ ✅ Not duplicate processing                      │
│  └─ ❌ Missing/Invalid → Error Message               │
│                                                      │
├─ CONTENT VALIDATION ─────────────────────────────────┤
│  │                                                   │
│  ├─ Profanity Filter                                 │
│  ├─ Length Check (not too long/short)                │
│  ├─ Banned Category Check                            │
│  └─ ❌ Invalid → Delete + Error Message              │
│                                                      │
├─ PLAYER DETECTION ───────────────────────────────────┤
│  │                                                   │
│  ├─ 1. Exact Match Check                             │
│  │   └─ "Alex Bregman" → Found immediately           │
│  │                                                   │
│  ├─ 2. Name Extraction                               │
│  │   └─ Extract potential player names from text     │
│  │                                                   │
│  ├─ 3. Fuzzy Matching                                │
│  │   └─ Match against 1800+ player database          │
│  │                                                   │
│  └─ 4. Validation                                    │
│      └─ Confirm matches are legitimate               │
│                                                      │
├─ DECISION LOGIC ─────────────────────────────────────┤
│  │                                                   │
│  ├─ NO PLAYERS FOUND ──────────────────────────────┐ │
│  │  └─ Check for potential player words             │ │
│  │      └─ Recent mention check                     │ │
│  │          ├─ Found recent → Block                 │ │
│  │          └─ Not found → Approve                  │ │
│  │                                                  │ │
│  ├─ SINGLE PLAYER FOUND ───────────────────────────┤ │
│  │  └─ Check recent mentions                       │ │
│  │      ├─ Found recent → Block                    │ │
│  │      └─ Not found → Approve                     │ │
│  │                                                 │ │
│  ├─ MULTIPLE PLAYERS FOUND ────────────────────────┤ │
│  │  │                                              │ │
│  │  ├─ Same Last Name → DISAMBIGUATION             │ │
│  │  │  └─ Show reaction menu for user to choose    │ │
│  │  │                                              │ │
│  │  └─ Different Last Names → BLOCK                │ │
│  │     └─ Multi-player policy violation            │ │
│  │                                                 │ │
│  └─ BLOCKED RESULT ────────────────────────────────┘ │
│     └─ Multi-player intent detected                  │
│                                                      │
├─ QUESTION PROCESSING ───────────────────────────────┤
│  │                                                   │
│  ├─ APPROVED QUESTIONS                               │
│  │  │                                                │
│  │  ├─ Delete original message                       │
│  │  ├─ Post to answering channel                     │
│  │  ├─ Add "Not Answered" status                     │
│  │  └─ Store question metadata                       │
│  │                                                   │
│  └─ BLOCKED QUESTIONS                                │
│     │                                                │
│     ├─ Delete original message                       │
│     ├─ Send error message                            │
│     └─ Auto-delete error after delay                 │
│                                                      │
├─ EXPERT INTERACTION ────────────────────────────────┤
│  │                                                   │
│  ├─ Expert sees question in answering channel        │
│  ├─ Expert replies to the message                    │
│  ├─ Bot detects reply                                │
│  ├─ Updates status to "Answered"                     │
│  └─ Posts formatted answer to final channel          │
│                                                      │
└─ FINAL OUTPUT ──────────────────────────────────────┤
   │                                                   │
   ├─ Final answer channel shows:                      │
   │  "User asked: How is Alex Bregman doing?"         │
   │  "Expert replied: He's been hitting well..."      │
   │                                                   │
   └─ Question lifecycle complete                      │
```

---

## 🧩 Core Components

### 1. **Bot Entry Point** (`bot.py`)
```python
# Main Discord bot setup
@bot.command(name="ask")
async def ask_question(ctx, *, question: str = None):
    # Process user questions
    # Handle validation and routing
```

### 2. **Player Detection Engine** (`player_matching.py`)
```python
# Core player detection logic
def check_player_mentioned(text):
    # 1. Exact match check
    # 2. Name extraction
    # 3. Fuzzy matching
    # 4. Validation
    return matched_players
```

### 3. **Validation System** (`validation.py` + `player_matching_validator.py`)
```python
# Question content validation
def validate_question(question):
    # Profanity filter
    # Length checks
    # Banned categories
    return is_valid, error_message

# Player match validation  
def validate_player_matches(text, matches):
    # Confirm legitimate player mentions
    return validated_matches
```

### 4. **Multi-Player Logic** (`bot_logic.py`)
```python
# Handle different player scenarios
def handle_single_player_question(ctx, question, players):
    # Process single player questions

def handle_multi_player_question(ctx, question, players):
    # Block or disambiguate multiple players
```

### 5. **Selection Handlers** (`selection_handlers.py`)
```python
# Handle user reactions for disambiguation
@bot.event
async def on_reaction_add(reaction, user):
    # Process user selections
    # Handle disambiguation choices
```

---

## 📊 Data Flow

### **Input Processing**
```
User Message → Channel Check → Validation → Player Detection → Decision Logic
```

### **Player Detection Pipeline**
```
Text Input → Name Extraction → Database Matching → Validation → Results
```

### **Decision Tree**
```
Results → Single Player? → Recent Check → Approve/Block
       → Multiple Players? → Same Name? → Disambiguate
                          → Different Names? → Block
       → No Players? → Fallback Check → Approve/Block
```

### **Output Generation**
```
Approved → Answering Channel → Expert Reply → Final Channel
Blocked → Error Message → Auto-Delete
```

---

## 🗃️ Key Data Structures

### **Player Database** (`players.json`)
```json
[
  {
    "name": "Alex Bregman",
    "team": "Astros",
    "position": "3B"
  }
]
```

### **Question Metadata** (`question_map_store.py`)
```python
{
  "message_id": {
    "question": "How is Alex Bregman doing?",
    "asker_id": 123456789,
    "asker_name": "User#1234",
    "timestamp": "2025-08-12T13:00:00Z"
  }
}
```

### **Pending Selections** (In-memory)
```python
{
  "user_id": {
    "type": "disambiguation_selection",
    "players": [player1, player2, player3],
    "message": discord_message_object,
    "original_question": "Question text"
  }
}
```

---

## 🔧 Configuration Files

### **Main Config** (`config.py`)
```python
# Discord settings
DISCORD_TOKEN = "your_bot_token"
SUBMISSION_CHANNEL = "ask-questions"
ANSWERING_CHANNEL = "questions"
FINAL_ANSWER_CHANNEL = "final-answers"

# Bot behavior
PRE_SELECTION_DELAY = 3
REACTIONS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

# Data
players_data = []  # Loaded from players.json
banned_categories = {}  # Loaded from profanity.json
```

### **Utilities** (`utils.py`)
```python
def normalize_name(name):
    # Standardize name formatting

def is_likely_player_request(text):
    # Determine if text is asking about a player

def expand_nicknames(text):
    # Convert nicknames to full names
```

---

## 🚨 Error Handling & Edge Cases

### **Rate Limiting Protection**
```python
# Prevent Discord API abuse
def check_rate_limit(operation):
    # Track API calls
    # Block excessive usage
    return allowed
```

### **Circuit Breakers**
```python
# Prevent infinite loops
def emergency_circuit_breaker():
    # Monitor processing load
    # Block when overloaded
    return safe_to_proceed
```

### **Validation Filters**
```python
# Prevent false positives
def emergency_validation_filter(player_name):
    # Block common English words
    # Ensure legitimate player names only
    return is_valid_player
```

---

## 🎯 Key Features

### **Single Player Policy**
- Only allows questions about one player at a time
- Blocks multi-player comparisons
- Provides disambiguation for same-name players

### **Recent Mention Protection**
- Prevents spam by checking recent questions
- Blocks duplicate topics within time window
- Maintains question quality

### **Expert Workflow**
- Clean interface for experts to answer
- Automatic status tracking
- Formatted final answers

### **User Experience**
- Clear error messages
- Reaction-based disambiguation
- Auto-cleanup of temporary messages

---

## 🔄 Deployment Architecture

### **Development Setup**
```
1. Clone repository
2. Install dependencies (discord.py, etc.)
3. Configure bot token and channels
4. Load player database
5. Run bot.py
```

### **Production Considerations**
```
- Rate limiting protection
- Error logging and monitoring
- Database backup and recovery
- Graceful shutdown handling
- Memory leak prevention
```

---

## 📈 Scalability & Performance

### **Optimization Strategies**
- Exact match priority (prevents unnecessary processing)
- Efficient player database lookups
- Caching for frequent queries
- Circuit breakers for overload protection

### **Monitoring Points**
- API call frequency
- Processing time per query
- Memory usage
- Error rates
- User satisfaction metrics

---

This wireframe provides a complete overview of how the Discord Baseball Bot works, from user input to final answer delivery, including all the critical components, data flows, and architectural decisions that make it function effectively.
