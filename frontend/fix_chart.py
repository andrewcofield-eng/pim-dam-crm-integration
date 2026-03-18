html = open("index.html","r",encoding="utf-8").read()

old = 'type:"bar",\n      :[{label:"Shop,backgroundColor:colors,borderRadius:6}]},'
new = 'type:"bar",\n      data:{labels:labels,datasets:[{label:"Shopify Metrics",data:values,backgroundColor:colors,borderRadius:6}]},'

if old in html:
    html = html.replace(old, new)
    print("Fixed!")
else:
    print("Pattern not found")

with open("index.html","w",encoding="utf-8") as f:
    f.write(html)

# Verify
idx = html.find("new Chart(ctx")
print(repr(html[idx:idx+200]))
