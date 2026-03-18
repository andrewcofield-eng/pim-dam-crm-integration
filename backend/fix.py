with open('orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the broken print statement
content = content.replace('print(f"\n??', 'print(f"\n??')
content = content.replace('print(f"\n' + chr(10) + '??', 'print(f"\n??')

# More direct fix - replace the entire broken line
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'print(f"' in line and '??' not in line and i < len(lines) - 1:
        if '??' in lines[i+1]:
            # Merge the two lines
            lines[i] = lines[i] + '\n??' + lines[i+1].replace('??', '').lstrip()
            lines.pop(i+1)

content = '\n'.join(lines)

with open('orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed broken print')
