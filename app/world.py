import io, contextlib, traceback, re, httpx, time

HEADERS = {"User-Agent": "Mozilla/5.0 (WorldBestAI/1.0)"}

class WorldEngine:
    def __init__(self):
        self._cache = {} # {query: (ans, test, timestamp)}

    def predict(self, text: str) -> tuple[str, str]:
        clean = text.strip()
        t = clean.lower()

        # --- cache check (5 min TTL) ---
        if clean in self._cache:
            ans, test, ts = self._cache[clean]
            if time.time() - ts < 300: # 5 minutes
                return ans, test

        def save(ans, test):
            self._cache[clean] = (ans, test, time.time())
            return ans, test

        # --- flashcard learning from images ---
        if m := re.search(r'([A-Z]{2,}|[A-Z][a-z]+(?:\s[A-Z][a-z]+)?) is the capital of ([A-Za-z\s]+?)(?:\.|$)', clean, re.IGNORECASE):
            city = m.group(1).strip().title()
            country = m.group(2).strip().rstrip('.')
            ans = f"{city} is the capital of {country}"
            test = f"print('{ans}')"
            return save(ans, test)

        # --- math ---
        if m := re.search(r'what is ([\d+\-*/().\s]+)', t):
            expr = m.group(1)
            if re.match(r'^[\d+\-*/().\s]+$', expr):
                try:
                    return save(str(eval(expr, {"__builtins__":{}})), f"print({expr})")
                except:
                    pass

        # --- compound interest ---
        if m := re.search(r'calculate (\d+(?:\.\d+)?) at (\d+(?:\.\d+)?)% for (\d+(?:\.\d+)?) years?', t):
            p = float(m.group(1)); rate = float(m.group(2)) / 100; y = float(m.group(3))
            result = p * (1 + rate) ** y
            ans = f"{p:,.0f} at {m.group(2)}% for {y:g} years = {result:,.2f}"
            test = f"p={p}; r={rate}; y={y}; print(f'{{p}} at {m.group(2)}% for {{y:g}} years = {{p*(1+r)**y:,.2f}}')"
            return save(ans, test)

        # --- weather ---
        if m := re.search(r'weather in ([a-zA-Z\s]+)', t):
            city = m.group(1).strip().title()
            try:
                url = f"https://wttr.in/{city}?format=%l:+%c+%t"
                r = httpx.get(url, headers=HEADERS, timeout=8.0)
                ans = ' '.join(r.text.strip().split())
                test = f"r=httpx.get('https://wttr.in/{city}?format=%l:+%c+%t',headers={{'User-Agent':'Mozilla/5.0'}}); print(' '.join(r.text.strip().split()))"
                return save(ans, test)
            except Exception:
                return save(f"Failed to get weather for {city}", "# weather failed")

        # --- string ops ---
        if m := re.search(r'reverse (.+)', t):
            s = m.group(1).strip(); safe = s.replace("'", "\\'")
            return save(s[::-1], f"print('{safe}'[::-1])")
        if m := re.search(r'uppercase (.+)', t):
            s = m.group(1).strip(); safe = s.replace("'", "\\'")
            return save(s.upper(), f"print('{safe}'.upper())")
        if m := re.search(r'lowercase (.+)', t):
            s = m.group(1).strip(); safe = s.replace("'", "\\'")
            return save(s.lower(), f"print('{safe}'.lower())")
        if m := re.search(r'(?:how many letters in|length of) (.+)', t):
            s = m.group(1).strip(); safe = s.replace("'", "\\'")
            return save(str(len(s.replace(' ',''))), f"print(len('{safe}'.replace(' ','')))")

        # --- summarizer ---
        if m := re.search(r'summarize (https?://\S+)', t):
            url = m.group(1)
            try:
                if 'wikipedia.org/wiki/' in url:
                    title = url.split('/wiki/')[-1].split('#')[0].split('?')[0]
                    api = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
                    r = httpx.get(api, headers=HEADERS, timeout=8.0)
                    if r.status_code == 200:
                        summary = r.json().get('extract','')[:400]
                        test = f"r=httpx.get('{api}',headers={{'User-Agent':'Mozilla/5.0'}}); print(r.json().get('extract','')[:400])"
                        return save(f"Summary: {summary}", test)
                r = httpx.get(url, headers=HEADERS, timeout=10.0, follow_redirects=True)
                html = r.text
                html = re.sub(r'<script.*?</script>', ' ', html, flags=re.DOTALL|re.IGNORECASE)
                html = re.sub(r'<style.*?</style>', ' ', html, flags=re.DOTALL|re.IGNORECASE)
                html = re.sub(r'<!--.*?-->', ' ', html, flags=re.DOTALL)
                text_only = re.sub(r'<[^>]+>', ' ', html)
                text_only = ' '.join(text_only.split())
                sentences = re.split(r'(?<=[.!?])\s+', text_only)
                summary = ' '.join(sentences[:3])[:400]
                if not summary: summary = text_only[:300]
                return save(f"Summary: {summary}", "# generic summary")
            except Exception:
                return save(f"Failed to fetch {url}", "# fetch failed")

        # --- web (Wikipedia) ---
        if t.startswith(("what is ","who is ","where is ","when is ")) or "capital of" in t:
            q = re.sub(r'^(what|who|where|when) is ', '', t)
            if "capital of" in t:
                if m := re.search(r'capital of ([a-z\s]+)', t):
                    country = m.group(1).strip().split('.')[0].split(',')[0].strip()
                    q = f"capital of {country}"
            try:
                sr = httpx.get("https://en.wikipedia.org/w/api.php",
                    params={"action":"query","list":"search","srsearch":q,"format":"json"},
                    headers=HEADERS, timeout=8.0)
                hits = sr.json().get("query",{}).get("search",[])
                if hits:
                    title = hits[0]["title"]
                    sm = httpx.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}",
                                   headers=HEADERS, timeout=8.0)
                    if sm.status_code == 200:
                        ans = sm.json().get("extract","")[:200]
                        if ans:
                            test = f"h={{'User-Agent':'Mozilla/5.0'}}; r=httpx.get('https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}',headers=h); print(r.json().get('extract','')[:200])"
                            return save(ans, test)
            except:
                pass

        return save(f"Simulated future for: {clean}", "# no auto test")

    def act(self, text: str) -> str:
        out = io.StringIO()
        safe = {'print':print,'range':range,'len':len,'sum':sum,'min':min,'max':max,'abs':abs,'round':round,'str':str,'int':int,'float':float,'list':list,'dict':dict}
        try:
            with contextlib.redirect_stdout(out):
                exec(text, {'__builtins__': {**safe, '__import__': __import__}, 'httpx':httpx,'re':re}, {})
            return out.getvalue() or "code ran with no output"
        except:
            return "Error:\n"+traceback.format_exc()[-300:]