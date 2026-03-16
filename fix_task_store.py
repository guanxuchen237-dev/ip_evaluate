import os

file_path = "d:/ip-lumina-main/integrated_system/backend/virtual_reader/task_store.py"

with open(file_path, 'rb') as f:
    lines = f.readlines()

new_lines = []
fixed = False
for line in lines:
    # Check for the mojibake lines by looking for specific SQL patterns
    if b"comment NOT LIKE" in line and b"%%" in line:
        if b"system" in line.lower(): # Skip the line checking for 'system' if it has NOT LIKE '%%...
             # The system line is: AND (reader_name IS NULL OR LOWER(reader_name) <> 'system')
             # It doesn't have %% usually.
             pass
        
        # Identify the specific lines
        # Line 369: ... '%%task submitted garbled%%'
        # Line 370: ... '%%simulation paused garbled%%'
        
        # We replace them based on order or content
        # To be safe, let's just replace any line with "comment NOT LIKE '%%" with empty string or the correct logic if we can distinguish.
        # But we need to preserve logic.
        
        # Let's inspect the line content in hex to be sure, or just replace blindly?
        # Better: Replace the entire block if we find the start matches.
        
        # Actually, let's just look for the known unique signatures
        try:
            s_line = line.decode('utf-8', errors='ignore')
            if "comment NOT LIKE" in s_line and "%%" in s_line:
                if "浠诲姟" in s_line or "任务" in s_line or b'\xe6\xb5' in line: # Try to match parts of mojibake
                    # This is likely the "Task Submitted" line
                    prefix = line[:line.find(b'AND')]
                    indent = b"                      "
                    new_line = indent + b"AND (comment IS NULL OR comment NOT LIKE '%%" + "任务已提交".encode('utf-8') + b"%%')\r\n"
                    new_lines.append(new_line)
                    fixed = True
                    print("Fixed 'Task Submitted' line")
                    continue
                elif "宸叉殏" in s_line or "暂停" in s_line or b'\xe5\xae' in line:
                    # likely "Simulation Paused"
                    indent = b"                      "
                    new_line = indent + b"AND (comment IS NULL OR comment NOT LIKE '%%" + "已暂停模拟".encode('utf-8') + b"%%')\r\n"
                    new_lines.append(new_line)
                    fixed = True
                    print("Fixed 'Simulation Paused' line")
                    continue
                else:
                    # Fallback for other potential matches, just print valid generic logic
                    # Or maybe it is just the garbled text.
                    # Let's replace ANY line with `comment NOT LIKE '%%` followed by high-bit chars
                     indent = b"                      "
                     # We can't easily know which is which if they are totally garbled.
                     # But we know the order.
                     pass 
        except:
            pass
            
    new_lines.append(line)

# Alternative Strategy: Read file as text with errors='ignore', find lines, replace.
# But writing back might be tricky.
# Let's stick to the simpler text replacement if we can identify the lines.
# The lines are:
# AND (comment IS NULL OR comment NOT LIKE '%%浠诲姟宸叉彁浜?%')
# AND (comment IS NULL OR comment NOT LIKE '%%宸叉殏鍋滄ā鎷?%')

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Pattern match replacement
import re
# Match: AND (comment IS NULL OR comment NOT LIKE '%%<garbage>%%')
replacement1 = "AND (comment IS NULL OR comment NOT LIKE '%%任务已提交%%')"
replacement2 = "AND (comment IS NULL OR comment NOT LIKE '%%已暂停模拟%%')"

# We use regex to match the structure roughly
# Escape for regex: ( ) %
pattern = r"AND \(comment IS NULL OR comment NOT LIKE '%%[^']+%%'\)"

# Find all matches
matches = re.findall(pattern, content)

if len(matches) >= 2:
    print(f"Found {len(matches)} bad lines.")
    # Assume first is task submitted, second is suspended.
    # This is a bit risky but standard for this codebase.
    
    # We replace the first one
    content = content.replace(matches[0], replacement1, 1)
    # Replace the second one (which used to be matches[1], but now it's the first match of the old pattern remaining)
    content = content.replace(matches[1], replacement2, 1)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Successfully patched task_store.py")
else:
    print("❌ Could not find the expected bad lines.")
    print("Matches found:", matches)

