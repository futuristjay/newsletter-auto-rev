import json, os, re, sys
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request

KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)
DATE_STR = NOW.strftime("%Y-%m-%d")
DATE_KR = NOW.strftime("%Y년 %m월 %d일")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch(url, timeout=15):
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  warn: {url} -> {e}")
        return ""

def extract_number(text, patterns):
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            raw = m.group(1).replace(",", "")
            try:
                return float(raw)
            except ValueError:
                continue
    return None

def get_newcastle_coal():
    print("coal...")
    text = fetch("https://www.oilpriceapi.com/live/coal-price")
    price = extract_number(text, [r"Coal NOW: \$?([\d,.]+)"])
    return {"label": "Newcastle 6000", "value": price, "unit": "$/t", "source": "oilpriceapi.com", "date": DATE_STR}

def get_hba():
    print("hba...")
    text = fetch("https://coaltradeindo.com/hba-coal-index-price/")
    price = extract_number(text, [r"HBA.*?GAR 6322.*?\$([\d,.]+)", r"HBA 1.*?\$([\d,.]+)", r"HBA1.*?\$([\d,.]+)"])
    return {"label": "HBA Indonesia", "value": price, "unit": "$/t", "source": "Coaltradeindo/ESDM", "date": DATE_STR}

def get_coking_coal():
    print("coking...")
    text = fetch("https://tradingeconomics.com/commodity/coking-coal")
    price = extract_number(text, [r"Coking Coal.*?rose to ([\d,.]+)", r"Coking Coal.*?([\d,.]+) USD"])
    return {"label": "Coking Coal PLV", "value": price, "unit": "$/t", "source": "TradingEconomics", "date": DATE_STR}

def get_lme_copper():
    print("copper...")
    text = fetch("https://en.macromicro.me/series/17447/lme-copper-spot-price")
    price = extract_number(text, [r"([\d,]+\.\d+)\s*.*Commodities"])
    return {"label": "LME Copper", "value": price, "unit": "$/t", "source": "MacroMicro/LME", "date": DATE_STR}

def get_uranium():
    print("uranium...")
    text = fetch("https://tradingeconomics.com/commodity/uranium")
    price = extract_number(text, [r"Uranium.*?rose to ([\d,.]+)", r"fell to \$([\d,.]+)", r"([\d,.]+) USD/T"])
    return {"label": "Uranium", "value": price, "unit": "$/lb", "source": "TradingEconomics", "date": DATE_STR}

def get_usd_krw():
    print("usdkrw...")
    text = fetch("https://tradingeconomics.com/south-korea/currency")
    rate = extract_number(text, [r"USD/KRW.*?rose to ([\d,.]+)", r"USD/KRW.*?fell.*?([\d,.]+)"])
    return {"label": "USD/KRW", "value": rate, "unit": "KRW", "source": "TradingEconomics", "date": DATE_STR}

def get_dxy():
    print("dxy...")
    text = fetch("https://tradingeconomics.com/united-states/currency")
    val = extract_number(text, [r"DXY.*?rose to ([\d,.]+)", r"DXY.*?fell.*?([\d,.]+)"])
    return {"label": "DXY", "value": val, "unit": "", "source": "TradingEconomics", "date": DATE_STR}

def get_wti():
    print("wti...")
    text = fetch("https://tradingeconomics.com/commodity/crude-oil")
    price = extract_number(text, [r"WTI.*?closed.*?\+([\d,.]+)", r"crude.*?\$([\d,.]+)"])
    return {"label": "WTI", "value": price, "unit": "$/bbl", "source": "TradingEconomics", "date": DATE_STR}

def get_vix():
    print("vix...")
    text = fetch("https://tradingeconomics.com/vix:ind")
    val = extract_number(text, [r"VIX.*?([\d]+\.[\d]+)"])
    return {"label": "VIX", "value": val, "unit": "", "source": "TradingEconomics", "date": DATE_STR}

def get_sp500():
    print("sp500...")
    text = fetch("https://tradingeconomics.com/united-states/stock-market")
    val = extract_number(text, [r"S&P 500.*?([\d,]+\.[\d]+)"])
    return {"label": "S&P 500", "value": val, "unit": "", "source": "TradingEconomics", "date": DATE_STR}

def main():
    print(f"\n=== Market Data Collection: {DATE_KR} ===\n")
    collectors = [get_newcastle_coal, get_hba, get_coking_coal, get_lme_copper, get_uranium, get_wti, get_usd_krw, get_dxy, get_vix, get_sp500]
    results = {"date": DATE_STR, "date_kr": DATE_KR, "timestamp": NOW.isoformat(), "prices": {}}

    for fn in collectors:
        try:
            data = fn()
            results["prices"][data["label"]] = data
            print(f"  -> {data['value']}\n")
        except Exception as e:
            print(f"  ERROR: {fn.__name__}: {e}\n")

    os.makedirs("data", exist_ok=True)
    with open("data/raw_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    success = sum(1 for v in results["prices"].values() if v.get("value"))
    print(f"\n=== Done: {success}/{len(results['prices'])} collected ===\n")
    if success < 3:
        sys.exit(1)

if __name__ == "__main__":
    main()
