import json, os, sys, urllib.request, time

def ask(api_key, question):
    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": question}],
    }).encode("utf-8")
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=body,
                headers={"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90) as r:
                res = json.loads(r.read().decode("utf-8"))
            return "".join(b.get("text","") for b in res.get("content",[]) if b.get("type")=="text").strip()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"  429, waiting {60*(attempt+1)}s...")
                time.sleep(60*(attempt+1))
                continue
            print(f"  HTTP {e.code}")
            sys.exit(1)
        except Exception as e:
            print(f"  Error: {e}")
            sys.exit(1)
    sys.exit(1)

def main():
    print("\n=== Newsletter Gen v3 ===\n")
    with open("data/raw_data.json","r",encoding="utf-8") as f:
        raw = json.load(f)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key: print("No key"); sys.exit(1)

    prices = raw.get("prices", {})
    dk = raw.get("date_kr","")
    dt = raw.get("date","")
    p = json.dumps(prices, ensure_ascii=False)

    # Build ticker directly from scraped data - NO Claude needed
    print("Step 1: Building ticker from scraped data...")
    ticker = []
    for key, val in prices.items():
        if val.get("value"):
            v = val["value"]
            unit = val.get("unit","")
            ticker.append({
                "label": val.get("label", key),
                "value": f"{unit}{v}" if unit and not str(v).startswith(unit) else str(v),
                "change": "—",
                "trend": "STABLE",
                "source": val.get("source",""),
                "date": val.get("date","")
            })
    print(f"  Ticker: {len(ticker)} items")

    # Ask Claude for SHORT text commentary only - no JSON
    print("Step 2: Coal commentary...")
    coal_text = ask(api_key, f"오늘은 {dk}. 석탄 시장 데이터: {p}\n\n한국어로 답해. 아래 5개 항목을 각각 한 줄로, 번호만 붙여서 답해:\n1. 오늘의 석탄 시장 핵심 헤드라인\n2. 인도네시아 동향\n3. 중국 동향\n4. 인도 동향\n5. 향후 1-4주 전망")
    print(f"  Got {len(coal_text)} chars")
    time.sleep(3)

    print("Step 3: Other sectors...")
    other_text = ask(api_key, f"오늘은 {dk}. 시장 데이터: {p}\n\n한국어로 답해. 아래 8개 항목을 각각 한 줄로, 번호만 붙여서 답해:\n1. 구리 시장 요약\n2. 우라늄 시장 요약\n3. 삼성전자/반도체 요약\n4. LS Electric 요약\n5. 현대차 요약\n6. K-Beauty 요약\n7. Tesla/기술주 요약\n8. 매크로/거시경제 요약")
    print(f"  Got {len(other_text)} chars")

    # Parse numbered lines
    def parse_lines(text):
        lines = {}
        for line in text.split("\n"):
            line = line.strip()
            for i in range(1, 10):
                if line.startswith(f"{i}.") or line.startswith(f"{i})"):
                    lines[i] = line[2:].strip().lstrip(".").lstrip(")").strip()
        return lines

    coal_lines = parse_lines(coal_text)
    other_lines = parse_lines(other_text)

    # Assemble newsletter JSON in Python
    newsletter = {
        "date": dt,
        "date_kr": dk,
        "ticker": ticker,
        "coal": {
            "briefHeadline": coal_lines.get(1, "석탄 시장 업데이트"),
            "briefText": coal_lines.get(1, ""),
            "articles": [],
            "countryIndonesia": coal_lines.get(2, ""),
            "countryChina": coal_lines.get(3, ""),
            "countryIndia": coal_lines.get(4, ""),
            "outlook": [coal_lines.get(5, "")]
        },
        "copper": {"headline": other_lines.get(1, ""), "summary": other_lines.get(1, "")},
        "uranium": {"headline": other_lines.get(2, ""), "summary": other_lines.get(2, "")},
        "samsung": {"headline": other_lines.get(3, ""), "summary": other_lines.get(3, "")},
        "lsElectric": {"headline": other_lines.get(4, ""), "summary": other_lines.get(4, "")},
        "hyundai": {"headline": other_lines.get(5, ""), "summary": other_lines.get(5, "")},
        "kBeauty": {"headline": other_lines.get(6, ""), "summary": other_lines.get(6, "")},
        "teslaTech": {"headline": other_lines.get(7, ""), "summary": other_lines.get(7, "")},
        "macro": {"headline": other_lines.get(8, ""), "summary": other_lines.get(8, "")},
        "miniReport": {"title": "오늘의 시장", "content": coal_lines.get(1, "") + " " + other_lines.get(8, "")}
    }

    os.makedirs("data", exist_ok=True)
    with open("data/newsletter.json","w",encoding="utf-8") as f:
        json.dump(newsletter, f, ensure_ascii=False, indent=2)
    print(f"\nDone! Keys: {list(newsletter.keys())}")

if __name__ == "__main__":
    main()
