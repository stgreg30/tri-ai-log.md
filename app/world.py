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

        # 2-5. string ops (same as before)
        m = re.search(r'reverse (.+)', t)
        if m:
            s = m.group(1).strip()
            return s[::-1], f"print('{s.replace(\"'\",\"\\\\'\")}'[::-1])"
        m = re.search(r'uppercase (.+)', t)
        if m:
            s = m.group(1).strip()
            return s.upper(), f"print('{s.replace(\"'\",\"\\\\'\")}'.upper())"
        m = re.search(r'lowercase (.+)', t)
        if m:
            s = m.group(1).strip()
            return s.lower(), f"print('{s.replace(\"'\",\"\\\\'\")}'.lower())"
        m = re.search(r'(how many letters in|length of) (.+)', t)
        if m:
            s = m.group(2).strip()
            return str(len(s.replace(' ', ''))), f"print(len('{s.replace(\"'\",\"\\\\'\")}'.replace(' ','')))"

        # 6. WEB FACTS - improved
        if t.startswith(("what is ", "who is ", "where is ", "when is ")) or "capital of" in t:
            # try simplified query
            query = re.sub(r'^(what|who|where|when) is ', '', t).strip()
            for q in [clean, query, query.title()]:
                # DuckDuckGo
                try:
                    r = httpx.get("https://api.duckduckgo.com/", params={"q": q, "format": "json", "no_html": 1}, timeout=5.0)
                    d = r.json()
                    ans = d.get("AbstractText", "").strip()
                    if not ans and d.get("RelatedTopics"):
                        ans = d["RelatedTopics"][0].get("Text", "") if isinstance(d["RelatedTopics"][0], dict) else ""
                    if ans:
                        ans = ans[:200]
                        safe = q.replace("\\", "\\\\").replace("'", "\\'")
                        test = f"import httpx; r=httpx.get('https://api.duckduckgo.com/',params={{'q':'{safe}','format':'json'}}); d=r.json(); a=d.get('AbstractText') or ''; print(a[:200] if a else 'no DDG')"
                        return ans, test
                except:
                    pass
                # Wikipedia fallback
                try:
                    w = httpx.get("https://en.wikipedia.org/api/rest_v1/page/summary/" + q.replace(" ", "_"), timeout=5.0)
                    if w.status_code == 200:
                        js = w.json()
                        ans = js.get("extract", "")[:200]
                        if ans:
                            safe = q.replace("\\", "\\\\").replace("'", "\\'")
                            test = f"import httpx; r=httpx.get('https://en.wikipedia.org/api/rest_v1/page/summary/{safe.replace(' ', '_')}'); print(r.json().get('extract','')[:200])"
                            return ans, test
                except:
                    pass

        return f"Simulated future for: {clean}", "# no auto test"

    def act(self, text: str) -> str:
        code = text.strip()
        output = io.StringIO()
        safe_builtins = {'print': print, 'range': range, 'len': len, 'sum': sum, 'min': min, 'max': max, 'abs': abs, 'round': round, 'str': str, 'int': int, 'float': float, 'list': list, 'dict': dict}
        safe_globals = {'__builtins__': safe_builtins, 'httpx': httpx}
        try:
            with contextlib.redirect_stdout(output):
                exec(code, safe_globals, {})
            return output.getvalue() or "code ran with no output"
        except Exception:
            return "Error:\n" + traceback.format_exc()[-300:]