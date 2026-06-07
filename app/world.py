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

        # --- NEW SKILL: summarize URL ---
        if m := re.search(r'summarize (https?://\S+)', t):
            url = m.group(1)
            try:
                r = httpx.get(url, headers=HEADERS, timeout=10.0, follow_redirects=True)
                text_only = re.sub(r'<[^>]+>', ' ', r.text)
                summary = ' '.join(text_only.split())[:300]
                # NO import here - we use the globals passed to act()
                test = f"r=httpx.get('{url}',headers={{'User-Agent':'Mozilla/5.0'}}); t=re.sub(r'<[^>]+>',' ',r.text); print(' '.join(t.split())[:300])"
                return f"Summary: {summary}...", test
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
                exec(text, {'__builtins__':safe,'httpx':httpx,'re':re}, {})
            return out.getvalue() or "code ran with no output"
        except:
            return "Error:\n"+traceback.format_exc()[-300:]