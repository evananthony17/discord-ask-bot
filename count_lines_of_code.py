#!/usr/bin/env python3

"""
Count lines of code in the Discord bot project
"""

import os
import glob

def count_lines_in_file(filepath):
    """Count lines in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            total_lines = len(lines)
            blank_lines = sum(1 for line in lines if line.strip() == '')
            comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
            code_lines = total_lines - blank_lines - comment_lines
            return {
                'total': total_lines,
                'code': code_lines,
                'comments': comment_lines,
                'blank': blank_lines
            }
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return {'total': 0, 'code': 0, 'comments': 0, 'blank': 0}

def count_project_lines():
    """Count lines of code in the entire project"""
    
    # Define file patterns to include
    python_files = glob.glob("*.py")
    json_files = glob.glob("*.json")
    md_files = glob.glob("*.md")
    
    # Exclude test files for main count
    main_python_files = [f for f in python_files if not f.startswith('test_')]
    test_files = [f for f in python_files if f.startswith('test_')]
    
    print("=" * 70)
    print("DISCORD BOT PROJECT - LINES OF CODE ANALYSIS")
    print("=" * 70)
    
    # Count main Python files
    print("\n📁 MAIN PYTHON FILES:")
    print("-" * 50)
    main_totals = {'total': 0, 'code': 0, 'comments': 0, 'blank': 0}
    
    for filepath in sorted(main_python_files):
        counts = count_lines_in_file(filepath)
        print(f"{filepath:<25} {counts['total']:>6} total  {counts['code']:>6} code  {counts['comments']:>6} comments  {counts['blank']:>6} blank")
        for key in main_totals:
            main_totals[key] += counts[key]
    
    print("-" * 50)
    print(f"{'MAIN TOTAL':<25} {main_totals['total']:>6} total  {main_totals['code']:>6} code  {main_totals['comments']:>6} comments  {main_totals['blank']:>6} blank")
    
    # Count test files
    if test_files:
        print("\n🧪 TEST FILES:")
        print("-" * 50)
        test_totals = {'total': 0, 'code': 0, 'comments': 0, 'blank': 0}
        
        for filepath in sorted(test_files):
            counts = count_lines_in_file(filepath)
            print(f"{filepath:<25} {counts['total']:>6} total  {counts['code']:>6} code  {counts['comments']:>6} comments  {counts['blank']:>6} blank")
            for key in test_totals:
                test_totals[key] += counts[key]
        
        print("-" * 50)
        print(f"{'TEST TOTAL':<25} {test_totals['total']:>6} total  {test_totals['code']:>6} code  {test_totals['comments']:>6} comments  {test_totals['blank']:>6} blank")
    
    # Count JSON files
    if json_files:
        print("\n📄 JSON DATA FILES:")
        print("-" * 50)
        json_totals = {'total': 0, 'code': 0, 'comments': 0, 'blank': 0}
        
        for filepath in sorted(json_files):
            counts = count_lines_in_file(filepath)
            print(f"{filepath:<25} {counts['total']:>6} total")
            json_totals['total'] += counts['total']
            json_totals['code'] += counts['total']  # JSON is all "code"
        
        print("-" * 50)
        print(f"{'JSON TOTAL':<25} {json_totals['total']:>6} total")
    
    # Count markdown files
    if md_files:
        print("\n📝 DOCUMENTATION FILES:")
        print("-" * 50)
        md_totals = {'total': 0, 'code': 0, 'comments': 0, 'blank': 0}
        
        for filepath in sorted(md_files):
            counts = count_lines_in_file(filepath)
            print(f"{filepath:<25} {counts['total']:>6} total")
            md_totals['total'] += counts['total']
        
        print("-" * 50)
        print(f"{'MARKDOWN TOTAL':<25} {md_totals['total']:>6} total")
    
    # Overall summary
    print("\n" + "=" * 70)
    print("📊 PROJECT SUMMARY")
    print("=" * 70)
    
    overall_total = main_totals['total']
    overall_code = main_totals['code']
    
    if test_files:
        overall_total += test_totals['total']
        overall_code += test_totals['code']
    
    if json_files:
        overall_total += json_totals['total']
        overall_code += json_totals['code']
    
    if md_files:
        overall_total += md_totals['total']
    
    print(f"Main Python Code:        {main_totals['code']:>6} lines")
    if test_files:
        print(f"Test Code:               {test_totals['code']:>6} lines")
    if json_files:
        print(f"JSON Data:               {json_totals['total']:>6} lines")
    if md_files:
        print(f"Documentation:           {md_totals['total']:>6} lines")
    print("-" * 40)
    print(f"Total Project Lines:     {overall_total:>6} lines")
    print(f"Total Code Lines:        {overall_code:>6} lines")
    
    # File breakdown
    print(f"\nFile Breakdown:")
    print(f"  • Main Python files:   {len(main_python_files):>3}")
    if test_files:
        print(f"  • Test files:          {len(test_files):>3}")
    if json_files:
        print(f"  • JSON files:          {len(json_files):>3}")
    if md_files:
        print(f"  • Markdown files:      {len(md_files):>3}")
    
    total_files = len(main_python_files) + len(test_files) + len(json_files) + len(md_files)
    print(f"  • Total files:         {total_files:>3}")
    
    # Code quality metrics
    if main_totals['total'] > 0:
        code_ratio = (main_totals['code'] / main_totals['total']) * 100
        comment_ratio = (main_totals['comments'] / main_totals['total']) * 100
        print(f"\nCode Quality Metrics (Main Python Files):")
        print(f"  • Code ratio:          {code_ratio:>5.1f}%")
        print(f"  • Comment ratio:       {comment_ratio:>5.1f}%")
        print(f"  • Avg lines per file:  {main_totals['total'] / len(main_python_files):>5.1f}")

if __name__ == "__main__":
    count_project_lines()
