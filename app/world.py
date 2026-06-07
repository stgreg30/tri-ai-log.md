import io
import contextlib
import traceback
import re
import httpx

class WorldEngine:
    def predict(self, text: str) -> tuple[str, str]:
        clean = text.strip()
        t = clean.lower()

        # 1. MATH
        m = re.search(r'what is ([\d+\-*/().\s]+)', t)
        expr = m.group(1) if m else t
        if re.match(r'^[\d+\-*/().\s]+$', expr) and expr.strip():
            try:
                result = eval(expr, {"__builtins__": {}}, {})
                return str(result), f"print({expr})"
            except:
                pass

        # 2. REVERSE
        m = re.search(r'reverse (.+)', t)
        if m:
            s = m.group(1).strip()
            safe = s.replace("'", "\\'")
            return s[::-1], f"print('{safe}'[::-1])"

        # 3. UPPERCASE
        m = re.search(r'uppercase (.+)', t)
        if m:
            s = m.group(1).strip()
            safe = s.replace("'", "\\'")
            return s.upper(), f"print('{safe}'.upper())"

        # 4. LOWERCASE
        m = re.search(r'lowercase (.+)', t)
        if m:
            s = m.group(1).strip()
            safe = s.replace("'", "\\'")
            return s.lower(), f"print('{safe}'.lower())"

        # 5. LENGTH
        m = re.search(r'(how many letters in|length of) (.+)', t)
        if m:
            s = m.group(2).strip()
            safe = s.replace("'", "\\'")
            count = len(s.replace(' ', ''))
            return str(count), f"print(len('{safe}'.replace(' ','')))"

        # 6. WEB FACTS
        if t.startswith(("what is ", "who is ", "where is ", "when is ")) or "capital of" in t:
            query = re.sub(r'^(what|who|where|when) is ', '', t).strip()
            for q in [clean, query]:
                # DuckDuckGo
                try:
                    r = httpx.get("https://api.duckduckgo.com/", params={"q": q, "format": "json", "no_html": 1}, timeout=5.0)
                    d = r.json()
                    ans = d.get("AbstractText", "").strip()
                    if not ans and d.get("RelatedTopics"):
                        first = d["RelatedTopics"][0]
                        if isinstance(first, dict):
                            ans = first.get("Text", "")
                    if ans:
                        ans = ans[:200]
                        safe = q.replace("'", "\\'")
                        test = f"import httpx; r=httpx.get('https://api.duckduckgo.com/', params={{'q':'{safe}','format':'json'}}); print(r.json().get('AbstractText','')[:200])"
                        return ans, test
                except:
                    pass
                # Wikipedia
                try:
                    w = httpx.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{q.replace(' ', '_')}", timeout=5.0)
                    if w.status_code == 200:
                        ans = w.json().get("extract", "")[:200]
                        if ans:
                            safe = q.replace("'", "\\'")
                            test = f"import httpx; r=httpx.get('https://en.wikipedia.org/api/rest_v1/page/summary/{q.replace(' ', '_')}'); print(r.json().get('extract','')[:200])"
                            return ans, test
                except:
                    pass

        return f"Simulated future for: {clean}", "# no auto test"

    def act(self, text: str) -> str:
        code = text.strip()
        output = io.StringIO()
        safe_builtins = {
            'print': print, 'range': range, 'len': len, 'sum': sum,
            'min': min, 'max': max, 'abs': abs, 'round': round,
            'str': str, 'int': int, 'float': float, 'list': list, 'dict': dict,
        }
        safe_globals = {'__builtins__': safe_builtins, 'httpx': httpx}
        try:
            with contextlib.redirect_stdout(output):
                exec(code, safe_globals, {})
            return output.getvalue() or "code ran with no output"
        except Exception:
            return "Error:\n" + traceback.format_exc()[-300:]