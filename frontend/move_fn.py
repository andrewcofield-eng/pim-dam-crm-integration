with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

fn_marker = 'function generateAICampaign'
fn_start = html.find(fn_marker)

# Find the end of the function (closing brace at root level)
depth = 0
fn_end = fn_start
for i, ch in enumerate(html[fn_start:], start=fn_start):
    if ch == '{': depth += 1
    elif ch == '}':
        depth -= 1
        if depth == 0:
            fn_end = i + 1
            break

# Extract the function
fn_body = html[fn_start:fn_end]

# Remove it from its current location (plus any leading newline)
html_without = html[:fn_start].rstrip('\n') + html[fn_end:]

# Re-inject it just before the closing </script> of the SECOND script block
# (the one that contains var API)
api_idx = html_without.find('var API')
second_script_close = html_without.find('</script>', api_idx)

html_fixed = (
    html_without[:second_script_close]
    + '\n\n' + fn_body + '\n'
    + html_without[second_script_close:]
)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_fixed)

print('Done - generateAICampaign moved into the var API script block')
print(f'Function length: {len(fn_body)} chars')
