#!/usr/bin/env python3
"""
Patch de tests para agregar openrouter_risk_accepted=False a los ChatTurn.create() calls.
"""
import os
import re
import sys

FILES = [
    "home/test_chat.py",
    "home/test_chat_provider_routing.py", 
    "home/test_chat_cancellation.py",
    "home/test_chat_reattachment.py",
    "home/test_gemini_chat.py",
    "home/test_gemini_queue.py",
    "home/test_message_history.py",
    "home/test_t179_integration.py",
]

def patch_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    output = []
    in_create = False
    create_line_idx = -1
    open_parens = 0
    changes = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if stripped.startswith('ChatTurn.objects.create('):
            in_create = True
            create_line_idx = i
            open_parens = line.count('(') - line.count(')')
            output.append(line)
            continue
        
        if in_create:
            new_open = line.count('(') - line.count(')')
            open_parens += new_open
            
            if open_parens <= 0:
                if 'openrouter_risk_accepted' not in line:
                    if line.rstrip().endswith(')'):
                        line = line.rstrip()[:-1]
                        indent = line[:len(line) - len(line.lstrip())]
                        line = line.rstrip() + ',\n' + indent + '            openrouter_risk_accepted=False'
                    output.append(line)
                    changes += 1
                else:
                    output.append(line)
                in_create = False
                continue
            
            output.append(line)
            continue
        
        output.append(line)
    
    if changes > 0:
        with open(filepath, 'w') as f:
            f.write('\n'.join(output))
        print(f"  [OK] {filepath}: {changes} changes")
    else:
        print(f"  [SKIP] {filepath}: no changes needed")

def main():
    for filepath in FILES:
        if not os.path.exists(filepath):
            print(f"  [SKIP] {filepath}: no existe")
            continue
        patch_file(filepath)
    print("Done")

if __name__ == '__main__':
    main()
