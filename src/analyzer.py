import json, os, sys, urllib.request, time

def call_api(api_key, system, user_msg, max_retries=3):
    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "messages": [
            {"role": "user", "content": system + "\n\n" + user_msg}
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            texts = [b["text"] for b in result.get("content", []) if b.get("type") == "text"]
            raw = "\n".join(texts).strip()
            first = raw.find("{")
            last = raw.rfind("}")
            if first >= 0 and last > first:
                raw = raw[first:last+1]
            return json.loads(raw)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 60 * (attempt + 1)
                print(f"  Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"  HTTP {e.code}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"  JSON error: {e}")
            print(f"  Preview: {raw[:400]}")
            sys.exit(1)
        except Exception as e:
            print(f"  Error: {e}")
            sys.exit(1)
    print("Failed after retries")
    sys.exit(1)

def main():
    print("\n=== Newsletter Generation ===\n")
    if not os.path.exists("data/raw_data.json"):
        print("ERROR: run scraper.py first"); sys.exit(1)
    with open("data/raw_data.json", "r", encoding="utf-8") as f:
        raw = json.load(f)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set"); sys.exit(1)

    prices = json.dumps(raw.get("prices", {}), ensure_ascii=False)
    dt = raw.get("date", "")
    dk = raw.get("date_kr", "")

    # CALL 1: Coal detail
    print("Step 1: Coal section...")
    coal = call_api(api_key,
        f"Today: {dk}. Data: {prices}",
        """Return ONLY JSON. No other text. Korean only.
{
  "briefHeadline": "석탄 헤드라인 1문장",
  "briefText": "브리프 2문장",
  "articles": [
    {"title":"제목","source":"출처","date":"MM/DD","summary":"요약1문장","relevance":"HIGH","investmentImplication":"시사점1문장"},
    {"title":"제목2","source":"출처","date":"MM/DD","summary":"요약","relevance":"MEDIUM","investmentImplication":"시사점"},
    {"title":"제목3","source":"출처","date":"MM/DD","summary":"요약","relevance":"MEDIUM","investmentImplication":"시사점"}
  ],
  "countryIndonesia": "1문장",
  "countryChina": "1문장",
  "countryIndia": "1문장",
  "outlook": ["전망1","전망2","전망3"]
}""")
    print(f"  Coal OK: {list(coal.keys())}")

    time.sleep(5)

    # CALL 2: Everything else
    print("Step 2: Other sections...")
    others = call_api(api_key,
        f"Today: {dk}. Data: {prices}",
        """Return ONLY JSON. No other text. Korean only.
{
  "ticker": [
    {"label":"뉴캐슬 6000","value":"$XXX/t","change":"±X%","trend":"UP","source":"src","date":"MM/DD"},
    {"label":"HBA 인니","value":"$XX/t","change":"±X%","trend":"UP","source":"src","date":"MM/DD"},
    {"label":"LME 구리","value":"$XX,XXX/t","change":"±X%","trend":"DOWN","source":"src","date":"MM/DD"},
    {"label":"우라늄","value":"$XX/lb","change":"±X%","trend":"UP","source":"src","date":"MM/DD"},
    {"label":"WTI","value":"$XX/bbl","change":"±X%","trend":"UP","source":"src","date":"MM/DD"},
    {"label":"원/달러","value":"₩X,XXX","change":"±X%","trend":"UP","source":"src","date":"MM/DD"},
    {"label":"DXY","value":"XXX","change":"±X%","trend":"UP","source":"src","date":"MM/DD"},
    {"label":"VIX","value":"XX","change":"±X%","trend":"UP","source":"src","date":"MM/DD"}
  ],
  "copper": {"headline":"1줄","summary":"2문장"},
  "uranium": {"headline":"1줄","summary":"2문장"},
  "samsung": {"headline":"1줄","summary":"2문장"},
  "lsElectric": {"headline":"1줄","summary":"1문장"},
  "hyundai": {"headline":"1줄","summary":"1문장"},
  "kBeauty": {"headline":"1줄","summary":"1문장"},
  "teslaTech": {"headline":"1줄","summary":"1문장"},
  "macro": {"headline":"1줄","summary":"2문장"},
  "miniReport": {"title":"이슈제목","content":"2문장"}
}""")
    print(f"  Others OK: {list(others.keys())}")

    # Merge
    newsletter = {
        "date": dt,
        "date_kr": dk,
        "ticker": others.get("ticker", []),
        "coal": coal,
        "copper": others.get("copper", {}),
        "uranium": others.get("uranium", {}),
        "samsung": others.get("samsung", {}),
        "lsElectric": others.get("lsElectric", {}),
        "hyundai": others.get("hyundai", {}),
        "kBeauty": others.get("kBeauty", {}),
        "teslaTech": others.get("teslaTech", {}),
        "macro": others.get("macro", {}),
        "miniReport": others.get("miniReport", {}),
    }

    os.makedirs("data", exist_ok=True)
    with open("data/newsletter.json", "w", encoding="utf-8") as f:
        json.dump(newsletter, f, ensure_ascii=False, indent=2)
    print(f"\nDone! data/newsletter.json saved.")

if __name__ == "__main__":
    main()
