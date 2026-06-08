import os, re, json, urllib.request, urllib.parse

URL    = os.environ.get("PRODUCT_URL", "https://www.tennisdiscount.nl/tennis-rackets/wilson-blade-98-v10-16x19.html")
TARGET = os.environ.get("TARGET_SIZE", "L3").upper()
DEBUG  = os.environ.get("DEBUG") == "1"
BOT    = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT   = os.environ["TELEGRAM_CHAT_ID"]
STATE  = "state.txt"
UA     = "Mozilla/5.0 (compatible; StockMonitor/1.0)"

def http(url, xhr=False):
    h = {"User-Agent": UA}
    if xhr: h["X-Requested-With"] = "XMLHttpRequest"
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def telegram(text):
    api = f"https://api.telegram.org/bot{BOT}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": CHAT, "text": text[:4000]}).encode()
    urllib.request.urlopen(urllib.request.Request(api, data=body), timeout=30).read()

def discover(page):
    pm = re.search(r'name="id_product"[^>]*value="(\d+)"', page) or re.search(r'data-id-product="(\d+)"', page)
    gm = re.search(r'group\[(\d+)\]', page)
    id_product = pm.group(1) if pm else None
    group_id = gm.group(1) if gm else None
    sizes = {}

    # Strategy 1: <select> options -> <option value="X" ...>L3</option>
    for m in re.finditer(r'<option\b[^>]*\bvalue="(\d+)"[^>]*>(.*?)</option>', page, re.S):
        lab = re.search(r'\bL[1-4]\b', m.group(2))
        if lab:
            sizes.setdefault(lab.group(0).upper(), m.group(1))

    # Strategy 2: radio inputs for this group, label in attribute OR nearby text
    if group_id:
        inputs = []
        for m in re.finditer(r'<input\b[^>]*\bname="group\[' + group_id + r'\]"[^>]*>', page):
            tag = m.group(0)
            vm = re.search(r'\bvalue="(\d+)"', tag)
            if not vm:
                continue
            lab = re.search(r'(?:title|aria-label|data-original-title)="\s*(L[1-4])\b', tag)
            if lab:
                sizes.setdefault(lab.group(1).upper(), vm.group(1))
            else:
                inputs.append((m.start(), vm.group(1)))
        # nearest-neighbour: pair each remaining input with the closest >L#< label text
        if inputs:
            labels = [(m.start(), m.group(1).upper())
                      for m in re.finditer(r'>\s*(L[1-4])\b', page)]
            for ipos, val in inputs:
                if labels:
                    _, lab = min(labels, key=lambda x: abs(x[0] - ipos))
                    sizes.setdefault(lab, val)

    return id_product, group_id, sizes

def in_stock_for(id_product, group_id, attr_id):
    q = {"id_product": id_product, f"group[{group_id}]": attr_id,
         "quantity_wanted": "1", "ajax": "1", "action": "refresh"}
    raw = http(URL + "?" + urllib.parse.urlencode(q), xhr=True)
    try: data = json.loads(raw)
    except Exception: data = {"raw": raw}
    blob = json.dumps(data, ensure_ascii=False).lower()
    add = (data.get("product_add_to_cart", "") if isinstance(data, dict) else "").lower()
    oos = ("niet op voorraad" in blob or "no longer in stock" in blob
           or "out of stock" in blob or bool(re.search(r'add-to-cart[^>]*\bdisabled', add)))
    instock = (not oos) and ("op voorraad" in blob or "in winkelwagen" in add)
    return instock, blob

def main():
    page = http(URL)
    id_product, group_id, sizes = discover(page)
    if DEBUG:
        telegram(f"DEBUG\nid_product={id_product}\ngroup_id={group_id}\nsizes={sizes}")

    if not (id_product and group_id and TARGET in sizes):
        if DEBUG and group_id:
            idx = page.find(f'group[{group_id}]')
            if idx == -1:
                idx = page.lower().find("grip")
            snip = page[max(0, idx-300): idx+1800] if idx != -1 else page[:2000]
            telegram("DEBUG variant HTML:\n" + snip)
        telegram(f"⚠️ Could not find {TARGET}. Found sizes: {sizes}")
        return

    available, blob = in_stock_for(id_product, group_id, sizes[TARGET])
    if DEBUG:
        telegram(f"DEBUG {TARGET} in_stock={available}\n{blob[:1200]}")

    prev = open(STATE).read().strip() if os.path.exists(STATE) else "0"
    now = "1" if available else "0"
    if available and prev != "1":
        telegram(f"🎾 Wilson Blade 98 V10 — maat {TARGET} is weer op voorraad!\n{URL}")
    open(STATE, "w").write(now)

if __name__ == "__main__":
    main()
