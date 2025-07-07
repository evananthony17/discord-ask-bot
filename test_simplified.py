from player_matching import simplified_player_detection

print("Testing simplified_player_detection with 'Juan Soto stats'")
result = simplified_player_detection('Juan Soto stats')
print(f'Result: {result}')
if result:
    if isinstance(result, list):
        print(f'Found: {[p["name"] for p in result]}')
    else:
        print(f'Found: {result["name"]}')
else:
    print('Found: None')
