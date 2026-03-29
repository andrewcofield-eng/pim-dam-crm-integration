with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Step 1: Find where var API is defined and print context
idx = html.find('var API')
print("var API context:")
print(repr(html[max(0,idx-50):idx+100]))

# Step 2: Find where generateAICampaign function was injected
idx2 = html.find('function generateAICampaign')
print("\ngenerateAICampaign context (first 200 chars):")
print(repr(html[idx2:idx2+200]))

# Step 3: Check if it's inside or outside a script tag
before_fn = html[:idx2]
open_scripts  = before_fn.count('<script')
close_scripts = before_fn.count('</script>')
print(f"\nScript tags opened before function: {open_scripts}")
print(f"Script tags closed before function: {close_scripts}")
print("=> Function is INSIDE a script block" if open_scripts > close_scripts else "=> Function is OUTSIDE all script blocks - THIS IS THE BUG")
