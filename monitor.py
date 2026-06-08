import os, re, urllib.request

URL = os.environ.get("PRODUCT_URL", "https://www.tennisdiscount.nl/tennis-rackets/wilson-blade-98-v10-16x19.html")
UA  = "Mozilla/5.0 (compatible; StockMonitor/1.0)"

def http(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

page = http(URL)
print("PAGE LENGTH:", len(page))
print("ID_PRODUCT:", re.findall(r'name="id_product"[^>]*value="(\d+)"', page)[:3])
print("GROUP MATCHES:", re.findall(r'group\[(\d+)\]', page)[:10])
print("HAS data-product attr:", bool(re.search(r'data-product\s*=', page)))
print("HAS 'combinations':", "combinations" in page.lower())

def dump(label, idx, before=250, after=1600):
    print("\n========== " + label + " (idx=%s) ==========" % idx)
    if idx == -1:
        print("...not found...")
    else:
        print(page[max(0, idx-before): idx+after])

dump("AROUND first group[", page.find("group["))
dump("AROUND 'Grip'", page.find("Grip"))
for size in ("L1", "L2", "L3", "L4"):
    dump("AROUND first '%s'" % size, page.find(">"+size))
