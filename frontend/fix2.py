html = open("index.html","r",encoding="utf-8").read()

old = '      :[{label:"values,backgroundColor:colors,borderRadius:6}]},':labels,datasets:[{label:"Shopify Metrics",,borderRadius:6}]},'

if old in html:
    html = html.replace(old, new)
    print("FIXED")
else:
    print("Still not found - exact bytes:")
    idx = html.find(":[{label")
    print(repr(html[idx-20:idx+80]))

with open("index.html","w",encoding="utf-8") as f:
    f.write(html)

idx2 = html.find("new Chart(ctx")
print(repr(html[idx2:idx2+250]))
