import json, os, sys, re, time
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError

KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)
DATE_STR = NOW.strftime("%Y-%m-%d")
DATE_KR = NOW.strftime("%Y년 %m월 %d일")

def fetch(url):
    try:
        r = urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15)
        return r.read().decode("utf-8", errors="replace")
    except:
        return ""

def xnum(text, pats):
    for p in pats:
        m = re.search(p, text)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except:
                pass
    return None

def ask(api_key, q):
    msg = [{"role": "user", "content": q}]
    body = json.dumps({"model": "claude-sonnet-4-20250514", "max_tokens": 1024, "messages": msg}).encode()
    for i in range(3):
        try:
            req = Request(
                "https://api.anthropic.com/v1/messages",
                data=body,
                headers={"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
                method="POST",
            )
            with urlopen(req, timeout=90) as r:
                res = json.loads(r.read().decode())
            return "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text").strip()
        except HTTPError as e:
            if e.code == 429:
                time.sleep(60 * (i + 1))
                continue
            print(f"HTTP {e.code}")
            sys.exit(1)
    sys.exit(1)

def plines(t):
    r = {}
    for line in t.split("\n"):
        line = line.strip()
        for i in range(1, 10):
            for pfx in [f"{i}.", f"{i})", f"{i}:"]:
                if line.startswith(pfx):
                    r[i] = line[len(pfx):].strip()
    return r

def main():
    # SCRAPE
    print("=== SCRAPING ===")
    data = {}
    for name, url, pats, unit in [
        ("Newcastle 6000", "https://www.oilpriceapi.com/live/coal-price", [r"Coal NOW: \$?([\d,.]+)"], "$/t"),
        ("HBA Indonesia", "https://coaltradeindo.com/hba-coal-index-price/", [r"HBA.*?GAR 6322.*?\$([\d,.]+)", r"HBA1.*?\$([\d,.]+)"], "$/t"),
        ("Coking Coal", "https://tradingeconomics.com/commodity/coking-coal", [r"Coking Coal.*?rose to ([\d,.]+)", r"Coking Coal.*?([\d,.]+) USD"], "$/t"),
    ]:
        v = xnum(fetch(url), pats)
        data[name] = {"value": v, "unit": unit, "source": url.split("/")[2]}
        print(f"  {name}: {v}")

    # ANALYZE
    print("\n=== ANALYZING ===")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("NO KEY")
        sys.exit(1)

    dp = json.dumps(data, ensure_ascii=False)
    print("Asking coal...")
    coal_text = ask(api_key, f"오늘은 {DATE_KR}. 석탄 데이터: {dp}\n\n한국어로 답해. 번호만:\n1.석탄 헤드라인\n2.인도네시아\n3.중국\n4.인도\n5.전망")
    print(f"  Got {len(coal_text)} chars")
    time.sleep(5)
    print("Asking sectors...")
    sector_text = ask(api_key, f"오늘은 {DATE_KR}. 데이터: {dp}\n\n한국어로 답해. 번호만:\n1.구리\n2.우라늄\n3.삼성전자\n4.LS Electric\n5.현대차\n6.K-Beauty\n7.Tesla/테크\n8.매크로")
    print(f"  Got {len(sector_text)} chars")

    cl = plines(coal_text)
    sl = plines(sector_text)

    # BUILD TICKER
    ticker = []
    for k, v in data.items():
        if v.get("value"):
            ticker.append({"label": k, "value": f"{v['unit']}{v['value']}", "source": v["source"], "date": DATE_STR})

    # ASSEMBLE
    newsletter = {
        "date": DATE_STR,
        "date_kr": DATE_KR,
        "ticker": ticker,
        "coal": {
            "briefHeadline": cl.get(1, "석탄 시장 업데이트"),
            "briefText": cl.get(1, ""),
            "countryIndonesia": cl.get(2, ""),
            "countryChina": cl.get(3, ""),
            "countryIndia": cl.get(4, ""),
            "outlook": [cl.get(5, "")],
        },
        "copper": {"headline": sl.get(1, ""), "summary": sl.get(1, "")},
        "uranium": {"headline": sl.get(2, ""), "summary": sl.get(2, "")},
        "samsung": {"headline": sl.get(3, ""), "summary": sl.get(3, "")},
        "lsElectric": {"headline": sl.get(4, ""), "summary": sl.get(4, "")},
        "hyundai": {"headline": sl.get(5, ""), "summary": sl.get(5, "")},
        "kBeauty": {"headline": sl.get(6, ""), "summary": sl.get(6, "")},
        "teslaTech": {"headline": sl.get(7, ""), "summary": sl.get(7, "")},
        "macro": {"headline": sl.get(8, ""), "summary": sl.get(8, "")},
        "miniReport": {"title": "오늘의 시장", "content": cl.get(1, "")},
    }

    os.makedirs("data", exist_ok=True)
    with open("data/newsletter.json", "w", encoding="utf-8") as f:
        json.dump(newsletter, f, ensure_ascii=False, indent=2)
    print(f"\n=== NEWSLETTER SAVED ===")

    # BUILD HTML
    n = newsletter
    c = n.get("coal", {})
    h = '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Market Intelligence</title>'
    h += '<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:sans-serif;background:#0d0b09;color:#e2d9ce;padding:20px}'
    h += '.t{font-family:monospace;font-size:16px;color:#ff8a65;font-weight:700;margin-bottom:20px}'
    h += '.s{background:#1a1612;border:1px solid rgba(148,163,184,.1);border-radius:10px;padding:16px;margin-bottom:12px}'
    h += '.hd{font-size:15px;color:#faf6f1;margin-bottom:8px}.p{font-size:13px;color:#a8a29e;line-height:1.6}'
    h += '.tk{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px}'
    h += '.ti{background:#1a1612;border:1px solid rgba(148,163,184,.1);border-radius:8px;padding:8px 12px;font-family:monospace;font-size:12px}'
    h += '.sec{font-family:monospace;font-size:11px;color:#e64a19;margin:20px 0 10px}</style></head><body>'
    h += '<div class="t">MARKET INTELLIGENCE</div>'
    h += f'<div style="font-family:monospace;font-size:11px;color:#57534e;margin-bottom:20px">{n["date_kr"]}</div>'
    h += '<div class="tk">'
    for t in n.get("ticker", []):
        h += f'<div class="ti"><div style="color:#57534e;font-size:10px">{t["label"]}</div><div style="color:#faf6f1;font-weight:600">{t["value"]}</div></div>'
    h += '</div><div class="sec">COAL</div>'
    h += f'<div class="s"><div class="hd">{c.get("briefHeadline","")}</div>'
    h += f'<div class="p">ID: {c.get("countryIndonesia","")}</div>'
    h += f'<div class="p">CN: {c.get("countryChina","")}</div>'
    h += f'<div class="p">IN: {c.get("countryIndia","")}</div></div>'
    for key, icon in [("copper","COPPER"),("uranium","URANIUM"),("samsung","SAMSUNG"),("lsElectric","LS ELECTRIC"),("hyundai","HYUNDAI"),("kBeauty","K-BEAUTY"),("teslaTech","TESLA/TECH"),("macro","MACRO")]:
        sec = n.get(key, {})
        h += f'<div class="s"><div class="hd">{icon}: {sec.get("headline","")}</div><div class="p">{sec.get("summary","")}</div></div>'
    h += f'<div style="text-align:center;padding:20px;font-size:11px;color:#2a2420;font-family:monospace">MARKET INTELLIGENCE - {n["date_kr"]}</div></body></html>'

    os.makedirs("dist", exist_ok=True)
    with open("dist/index.html", "w", encoding="utf-8") as f:
        f.write(h)
    print(f"=== HTML SAVED === {len(h)} bytes")

if __name__ == "__main__":
    main()
