import json, os, sys, urllib.request, time

def main():
    print("\n=== Claude API Newsletter Generation ===\n")

    if not os.path.exists("data/raw_data.json"):
        print("ERROR: run scraper.py first")
        sys.exit(1)

    with open("data/raw_data.json", "r", encoding="utf-8") as f:
        raw = json.load(f)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    prices_str = json.dumps(raw.get("prices", {}), ensure_ascii=False, indent=2)
    date_kr = raw.get("date_kr", "")

    system = f"""You are a market analyst. Today: {date_kr}.
Scraped data:
{prices_str}

Return ONLY a JSON object. No explanation before or after. No markdown.
Keep each text field under 80 characters. All text in Korean.

STRICT JSON FORMAT:
{{
  "date": "{raw.get('date','')}",
  "date_kr": "{date_kr}",
  "ticker": [
    {{"label":"뉴캐슬 6000","value":"$XXX/t","change":"±X%","trend":"UP","source":"src","date":"MM/DD"}}
  ],
  "coal": {{
    "briefHeadline": "short headline",
    "briefText": "2 sentences max",
    "articles": [
      {{"title":"title","source":"src","date":"MM/DD","summary":"1 sentence","relevance":"HIGH","investmentImplication":"1 sentence"}}
    ],
    "countryIndonesia": "1 sentence",
    "countryChina": "1 sentence",
    "countryIndia": "1 sentence",
    "outlook": ["point1","point2","point3"]
  }},
  "copper": {{"headline":"1 line","summary":"2 sentences","peers":"1 sentence"}},
  "uranium": {{"headline":"1 line","summary":"2 sentences","peers":"1 sentence"}},
  "samsung": {{"headline":"1 line","summary":"2 sentences","peers":"1 sentence"}},
  "lsElectric": {{"headline":"1 line","summary":"1 sentence"}},
  "hyundai": {{"headline":"1 line","summary":"1 sentence"}},
  "kBeauty": {{"headline":"1 line","summary":"1 sentence"}},
  "teslaTech": {{"headline":"1 line","summary":"1 sentence"}},
  "macro": {{"headline":"1 line","summary":"2 sentences"}},
  "miniReport": {{"title":"issue title","content":"2-3 sentences"}}
}}

RULES:
- ticker: 8 items using scraped values
- coal articles: exactly 4
- Keep ALL text fields SHORT
- Return raw JSON only, no text before or after"""

    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "system": system,
        "messages": [{"role": "user", "content": "Generate the newsletter JSON now."}],
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

    # Retry logic
    for attempt in range(3):
        print(f"Calling Claude API (attempt {attempt+1}/3)...")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 30 * (attempt + 1)
                print(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"HTTP error: {e.code}")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print("Failed after 3 attempts")
        sys.exit(1)

    # Extract text
    texts = [b["text"] for b in result.get("content", []) if b.get("type") == "text"]
    if not texts:
        print("ERROR: no text in response")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:500])
        sys.exit(1)

    cleaned = "\n".join(texts).strip()

    # Remove any text before first {
    first = cleaned.find("{")
    if first > 0:
        cleaned = cleaned[first:]

    # Remove any text after last }
    last = cleaned.rfind("}")
    if last > 0:
        cleaned = cleaned[:last + 1]

    # Remove markdown fences
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    try:
        newsletter = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"JSON error: {e}")
        print(f"First 300 chars: {cleaned[:300]}")
        print(f"Last 300 chars: {cleaned[-300:]}")
        sys.exit(1)

    with open("data/newsletter.json", "w", encoding="utf-8") as f:
        json.dump(newsletter, f, ensure_ascii=False, indent=2)

    print(f"Success! Sections: {list(newsletter.keys())}")

if __name__ == "__main__":
    main()
