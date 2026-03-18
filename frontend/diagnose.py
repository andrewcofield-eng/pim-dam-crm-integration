import re

html = open("index.html","r",encoding="utf-8").read()

# Find the exact broken chart block and print it so we can see it
idx = html.find("new Chart(ctx")
print("CHART BLOCK:")
print(repr(html[idx:idx+400]))
