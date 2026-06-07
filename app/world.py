import io, contextlib, traceback, re, httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (WorldBestAI/1.0)"}

class WorldEngine:
    def predict(self, text: str) -> tuple[str, str]:
        clean = text.strip()
        t = clean.lower()

        # --- math ---
        if m := re.search(r'what is ([\d+\-*/().\s]+)', t):
            expr = m.group(1)
            if re.match(r'^[\d+\-*/().\s]+$', expr):
                try: return str(eval(expr, {"__builtins__":{}})), f"print({expr})"
                except: pass

        # --- SKILL 1: compound interest ---
        if m := re.search(r'calculate (\d+(?:\.\d+)?) at (\d+(?:\.\d+)?)% for (\d+(?:\.\d+)?) years?', t):
            p = float(m.group(1))
            rate = float(m.group(2)) / 100
            y = float(m.group(3))
            result = p * (1 + rate) ** y
            ans = f"{p:,.0f} at {m.group(2)}% for {y:g} years = {result:,.2f}"
            test = f"p={p}; r={rate}; y={y}; print(f'{{p}} at {m.group(2)}% for {{y:g}} years = {{p*(1+r)**y:,.2f}}')"
            return ans, test

        # --- string ops ---
        if m := re.search(r'reverse (.+)', t):
            s = m.group(1).strip(); safe = s.replace("'", "\\'")
            return s[::-1], f"print('{safe}'[::-1])"
        if m := re.search(r'uppercase (.+)', t):
            s = m.group(1).strip(); safe = s.replace("'", "\\'")
            return s.upper(), f"print('{safe}'.upper())"
        if m := re.search(r'lowercase (.+)', t):
            s = m.group(1).strip(); safe = s.replace("'", "\\'")
            return s.lower(), f"print('{safe}'.lower())"
        if m := re.search(r'(?:how many letters in|length of) (.+)', t):
            s = m.group(1).strip(); safe = s.replace("'", "\\'")
            return str(len(s.replace(' ',''))), f"print(len('{safe}'.replace(' ','')))"

        # --- clean summarizer ---
        if m := re.search(r'summarize (https?://\S+)', t):
            url = m.group(1)
            try:
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
                test = f"r=httpx.get('{url}',headers={{'User-Agent':'Mozilla/5.0'}}); h=r.text; h=__import__('re').sub(r'<script.*?</script>',' ',h,flags=__import__('re').DOTALL|__import__('re').IGNORECASE); h=__import__('re').sub(r'<style.*?</style>',' ',h,flags=__import__('re').DOTALL|__import__('re').IGNORECASE); t=__import__('re').sub(r'<[^>]+>',' ',h); t=' '.join(t.split()); s=__import__('re').split(r'(?<=[.!?])\\s+',t); print(' '.join(s[:3])[:400])"
                return f"Summary: {summary}", test
            except Exception:
                return f"Failed to fetch {url}", "# fetch failed"

        # --- web (Wikipedia) ---
        if t.startswith(("what is ","who is ","where is ","when is ")) or "capital of" in t:
            q = re.sub(r'^(what|who|where|when) is ', '', t)
            if "capital of" in t:
                q = "capital of " + t.split("capital of")[-1].strip()
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
                            return ans, test
            except: pass

        return f"Simulated future for: {clean}", "# no auto test"

    def act(self, text: str) -> str:
        out = io.StringIO()
        safe = {'print':print,'range':range,'len':len,'sum':sum,'min':min,'max':max,'abs':abs,'round':round,'str':str,'int':int,'float':float,'list':list,'dict':dict}
        try:
            with contextlib.redirect_stdout(out):
                exec(text, {'__builtins__': {**safe, '__import__': __import__}, 'httpx':httpx,'re':re}, {})
            return out.getvalue() or "code ran with no output"
        except:
            return "Error:\n"+traceback.format_exc()[-300:]