import io, contextlib, traceback, re, httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (WorldBestAI/1.0)"}

class WorldEngine:
    def predict(self, text: str) -> tuple[str, str]:
        clean = text.strip()
        t = clean.lower()

        # math
        if m := re.search(r'what is ([\d+\-*/().\s]+)', t):
            expr = m.group(1)
            if re.match(r'^[\d+\-*/().\s]+$', expr):
                try: return str(eval(expr, {"__builtins__":{}})), f"print({expr})"
                except: pass

        # string ops
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
            return str(len(s.replace(' ',' '))), f"print(len('{safe}'.replace(' ','')))"

        # web
        if t.startswith(("what is ","who is ","where is ","when is ")) or "capital of" in t:
            q = re.sub(r'^(what|who|where|when) is ', '', t)
            if "capital of" in t:
                q = "capital of " + t.split("capital of")[-1].strip()

            # try Wikipedia with headers
            try:
                sr = httpx.get("https://en.wikipedia.org/w/api.php",
                    params={"action":"query","list":"search","srsearch":q,"format":"json"},
                    headers=HEADERS, timeout=8.0)
                hits = sr.json().get("query",{}).get("search",[])
                if hits:
                    title = hits[0]["title"]
                    sm = httpx.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ','_')}",
                                   headers=HEADERS, timeout=8.0)
                    if sm.status_code == 200:
                        ans = sm.json().get("extract","")[:200]
                        if ans:
                            test = f"import httpx; h={{'User-Agent':'Mozilla/5.0'}}; r=httpx.get('https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ','_')}',headers=h); print(r.json().get('extract','')[:200])"
                            return ans, test
            except Exception as e:
                pass

            # DuckDuckGo fallback
            try:
                r = httpx.get("https://api.duckduckgo.com/", params={"q":q,"format":"json","no_html":1},
                              headers=HEADERS, timeout=8.0)
                ans = r.json().get("AbstractText","")[:200]
                if ans:
                    safe = q.replace("'", "\\'")
                    test = f"import httpx; print(httpx.get('https://api.duckduckgo.com/', params={{'q':'{safe}','format':'json'}}, headers={{'User-Agent':'Mozilla/5.0'}}).json().get('AbstractText','')[:200])"
                    return ans, test
            except: pass

        return f"Simulated future for: {clean}", "# no auto test"

    def act(self, text: str) -> str:
        out = io.StringIO()
        safe = {'print':print,'range':range,'len':len,'sum':sum,'min':min,'max':max,'abs':abs,'round':round,'str':str,'int':int,'float':float,'list':list,'dict':dict}
        try:
            with contextlib.redirect_stdout(out):
                exec(text, {'__builtins__':safe,'httpx':httpx}, {})
            return out.getvalue() or "code ran with no output"
        except: return "Error:\n"+traceback.format_exc()[-300:]