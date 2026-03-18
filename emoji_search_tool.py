#!/usr/bin/env python3
"""
Emoji/Emote Search Tool for Discord Bot Files
Comprehensive tool to find, analyze, and manage emoji usage across the codebase
"""

import os
import re
import json
from collections import defaultdict, Counter

def find_all_emojis():
    """Find all emojis/emotes in Python files"""
    
    # Common emoji patterns used in the bot
    emoji_patterns = {
        'status_emojis': r'[🔴🟡🟢🟠🔵⚠️✅❌🚫❗💥]',
        'activity_emojis': r'[🎯🔧🚨📊📍🆔💾🧹🎉⭐]',
        'symbols': r'[🔗🛡️📋🏗️🔄🚀📈🤖🧪💡🔍📝]',
        'numbers': r'[1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣8️⃣9️⃣0️⃣]',
        'arrows': r'[⬆️⬇️⬅️➡️↗️↘️↙️↖️]',
        'faces': r'[😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🤩🥳😏😒😞😔😟😕🙁☹️😣😖😫😩🥺😢😭😤😠😡🤬🤯😳🥵🥶😱😨😰😥😓🤗🤔🤭🤫🤥😶😐😑😬🙄😯😦😧😮😲🥱😴🤤😪😵🤐🥴🤢🤮🤧😷🤒🤕🤑🤠😈👿👹👺🤡💩👻💀☠️👽👾🤖🎃😺😸😹😻😼😽🙀😿😾]',
        'hands': r'[👋🤚🖐️✋🖖👌🤌🤏✌️🤞🤟🤘🤙👈👉👆🖕👇☝️👍👎👊✊🤛🤜👏🙌👐🤲🤝🙏✍️💅🤳💪🦾🦿🦵🦶👂🦻👃🧠🫀🫁🦷🦴👀👁️👅👄💋🩸]',
        'people': r'[👶🧒👦👧🧑👱👨🧔👨‍🦰👨‍🦱👨‍🦳👨‍🦲👩👩‍🦰🧑‍🦰👩‍🦱🧑‍🦱👩‍🦳🧑‍🦳👩‍🦲🧑‍🦲👱‍♀️👱‍♂️🧓👴👵🙍🙍‍♂️🙍‍♀️🙎🙎‍♂️🙎‍♀️🙅🙅‍♂️🙅‍♀️🙆🙆‍♂️🙆‍♀️💁💁‍♂️💁‍♀️🙋🙋‍♂️🙋‍♀️🧏🧏‍♂️🧏‍♀️🙇🙇‍♂️🙇‍♀️🤦🤦‍♂️🤦‍♀️🤷🤷‍♂️🤷‍♀️]'
    }
    
    # Comprehensive emoji regex (covers most Unicode emoji ranges)
    comprehensive_emoji_pattern = re.compile(
        r'[\U0001F600-\U0001F64F]|'  # emoticons
        r'[\U0001F300-\U0001F5FF]|'  # symbols & pictographs
        r'[\U0001F680-\U0001F6FF]|'  # transport & map symbols
        r'[\U0001F1E0-\U0001F1FF]|'  # flags (iOS)
        r'[\U00002702-\U000027B0]|'  # dingbats
        r'[\U000024C2-\U0001F251]|'  # enclosed characters
        r'[\U0001F900-\U0001F9FF]|'  # supplemental symbols
        r'[\U0001FA70-\U0001FAFF]|'  # symbols and pictographs extended-A
        r'[\U00002600-\U000026FF]|'  # miscellaneous symbols
        r'[\U0000FE00-\U0000FE0F]'   # variation selectors
    )
    
    results = defaultdict(list)
    emoji_counts = Counter()
    file_emoji_counts = defaultdict(Counter)
    
    # Search through Python files
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        if any(skip_dir in root for skip_dir in ['.git', '__pycache__', 'venv', '.venv']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                        for line_num, line in enumerate(lines, 1):
                            # Find all emojis in the line
                            emojis_in_line = comprehensive_emoji_pattern.findall(line)
                            
                            if emojis_in_line:
                                for emoji in emojis_in_line:
                                    results[filepath].append({
                                        'line_number': line_num,
                                        'line_content': line.strip(),
                                        'emoji': emoji,
                                        'context': line.strip()
                                    })
                                    emoji_counts[emoji] += 1
                                    file_emoji_counts[filepath][emoji] += 1
                                    
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return results, emoji_counts, file_emoji_counts

def categorize_emojis(emoji_counts):
    """Categorize emojis by their likely usage"""
    categories = {
        'Status Indicators': ['🔴', '🟡', '🟢', '🟠', '🔵', '⚠️', '✅', '❌', '🚫', '❗', '💥'],
        'Activity/Process': ['🎯', '🔧', '🚨', '📊', '📍', '🆔', '💾', '🧹', '🎉', '⭐'],
        'System/Tech': ['🔗', '🛡️', '📋', '🏗️', '🔄', '🚀', '📈', '🤖', '🧪', '💡', '🔍', '📝'],
        'Numbers': ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '0️⃣'],
        'Debug/Trace': ['🔵', '🟡', '🟢', '🟠', '🔴', '📊', '🔍', '🆔'],
        'Success/Error': ['✅', '❌', '⚠️', '🚫', '💥', '🎉'],
        'Emergency/Critical': ['🚨', '💥', '🔴', '⚠️', '🛡️']
    }
    
    categorized = defaultdict(list)
    uncategorized = []
    
    for emoji, count in emoji_counts.items():
        found_category = False
        for category, emoji_list in categories.items():
            if emoji in emoji_list:
                categorized[category].append((emoji, count))
                found_category = True
                break
        
        if not found_category:
            uncategorized.append((emoji, count))
    
    return categorized, uncategorized

def generate_emoji_report(results, emoji_counts, file_emoji_counts):
    """Generate a comprehensive emoji usage report"""
    
    print("🔍 EMOJI/EMOTE USAGE REPORT")
    print("=" * 60)
    
    # Overall statistics
    total_emoji_instances = sum(emoji_counts.values())
    unique_emojis = len(emoji_counts)
    files_with_emojis = len(results)
    
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"   Total emoji instances: {total_emoji_instances}")
    print(f"   Unique emojis used: {unique_emojis}")
    print(f"   Files containing emojis: {files_with_emojis}")
    
    # Most used emojis
    print(f"\n🏆 TOP 10 MOST USED EMOJIS:")
    for emoji, count in emoji_counts.most_common(10):
        print(f"   {emoji} - {count} times")
    
    # Categorized usage
    categorized, uncategorized = categorize_emojis(emoji_counts)
    
    print(f"\n📋 EMOJI USAGE BY CATEGORY:")
    for category, emoji_list in categorized.items():
        if emoji_list:
            total_in_category = sum(count for _, count in emoji_list)
            print(f"\n   {category} ({total_in_category} total):")
            for emoji, count in sorted(emoji_list, key=lambda x: x[1], reverse=True):
                print(f"      {emoji} - {count} times")
    
    if uncategorized:
        print(f"\n   🤔 UNCATEGORIZED ({sum(count for _, count in uncategorized)} total):")
        for emoji, count in sorted(uncategorized, key=lambda x: x[1], reverse=True):
            print(f"      {emoji} - {count} times")
    
    # File-by-file breakdown
    print(f"\n📁 EMOJI USAGE BY FILE:")
    for filepath, file_results in results.items():
        file_total = len(file_results)
        unique_in_file = len(set(result['emoji'] for result in file_results))
        print(f"\n   {filepath} ({file_total} instances, {unique_in_file} unique):")
        
        # Show top emojis in this file
        file_emoji_counter = Counter(result['emoji'] for result in file_results)
        for emoji, count in file_emoji_counter.most_common(5):
            print(f"      {emoji} - {count} times")
    
    return categorized, uncategorized

def search_specific_emoji(emoji_to_find):
    """Search for a specific emoji across all files"""
    results = []
    
    for root, dirs, files in os.walk('.'):
        if any(skip_dir in root for skip_dir in ['.git', '__pycache__', 'venv', '.venv']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        
                        for line_num, line in enumerate(lines, 1):
                            if emoji_to_find in line:
                                results.append({
                                    'file': filepath,
                                    'line_number': line_num,
                                    'line_content': line.strip(),
                                    'context': line.strip()
                                })
                                
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return results

def create_emoji_replacement_guide():
    """Create a guide for replacing emojis with text alternatives"""
    
    replacements = {
        '✅': 'SUCCESS',
        '❌': 'ERROR',
        '⚠️': 'WARNING',
        '🚨': 'ALERT',
        '🔴': 'RED',
        '🟡': 'YELLOW', 
        '🟢': 'GREEN',
        '🟠': 'ORANGE',
        '🔵': 'BLUE',
        '📊': 'STATS',
        '🔍': 'SEARCH',
        '🎯': 'TARGET',
        '🔧': 'FIX',
        '💾': 'SAVE',
        '🧹': 'CLEANUP',
        '🎉': 'CELEBRATION',
        '💥': 'CRASH',
        '🆔': 'ID',
        '📍': 'LOCATION',
        '🛡️': 'SHIELD',
        '🚀': 'LAUNCH',
        '🤖': 'BOT',
        '🧪': 'TEST',
        '1️⃣': '1',
        '2️⃣': '2',
        '3️⃣': '3',
        '4️⃣': '4',
        '5️⃣': '5',
        '6️⃣': '6',
        '7️⃣': '7',
        '8️⃣': '8',
        '9️⃣': '9',
        '0️⃣': '0'
    }
    
    print("\n🔄 EMOJI REPLACEMENT GUIDE:")
    print("=" * 40)
    print("If you want to replace emojis with text alternatives:")
    print()
    
    for emoji, replacement in replacements.items():
        print(f"   {emoji} → {replacement}")
    
    return replacements

def export_emoji_data(results, emoji_counts, file_emoji_counts):
    """Export emoji data to JSON for further analysis"""
    
    export_data = {
        'summary': {
            'total_instances': sum(emoji_counts.values()),
            'unique_emojis': len(emoji_counts),
            'files_with_emojis': len(results)
        },
        'emoji_counts': dict(emoji_counts),
        'file_breakdown': {}
    }
    
    for filepath, file_results in results.items():
        export_data['file_breakdown'][filepath] = {
            'total_instances': len(file_results),
            'unique_emojis': len(set(result['emoji'] for result in file_results)),
            'emoji_counts': dict(Counter(result['emoji'] for result in file_results)),
            'details': file_results
        }
    
    with open('emoji_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Exported detailed emoji analysis to 'emoji_analysis.json'")

def main():
    """Main function to run emoji analysis"""
    
    print("🔍 Starting comprehensive emoji analysis...")
    print()
    
    # Find all emojis
    results, emoji_counts, file_emoji_counts = find_all_emojis()
    
    if not results:
        print("No emojis found in Python files.")
        return
    
    # Generate report
    categorized, uncategorized = generate_emoji_report(results, emoji_counts, file_emoji_counts)
    
    # Create replacement guide
    create_emoji_replacement_guide()
    
    # Export data
    export_emoji_data(results, emoji_counts, file_emoji_counts)
    
    # Interactive search option
    print(f"\n🔍 INTERACTIVE SEARCH:")
    print("You can also search for specific emojis by calling:")
    print("   search_specific_emoji('🎯')  # Replace with any emoji")
    
    return results, emoji_counts, file_emoji_counts, categorized, uncategorized

if __name__ == "__main__":
    results, emoji_counts, file_emoji_counts, categorized, uncategorized = main()
    
    # Example of searching for a specific emoji
    print(f"\n🎯 EXAMPLE: Searching for '🎯' emoji:")
    target_results = search_specific_emoji('🎯')
    for result in target_results[:3]:  # Show first 3 results
        print(f"   {result['file']}:{result['line_number']} - {result['line_content']}")
    
    if len(target_results) > 3:
        print(f"   ... and {len(target_results) - 3} more occurrences")
