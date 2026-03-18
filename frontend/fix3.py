html = open("index.html","r",encoding="utf-8").read()

# The broken pattern from diagnose.py output
broken = '      :[{label:"Shopify Metrics",data:values,backgroundColor:colors,borderRadius:6}]},'
fixed  = '      data:{labels:labels,datasets:[{label:"Shopify Metrics",data:values,backgroundColor:colors,borderRadius:6}]},'

if broken in html:
    html = html.replace(broken, fixed)
    print("FIXED")
else:
    idx = html.find(":[{label")
    print("NOT FOUND - context:", repr(html[max(0,idx-30):idx+60]))

open("index.html","w",encoding="utf-8").write(html)
idx2 = html.find("new Chart(ctx")
print(repr(html[idx2:idx2+220]))
