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
                result = eval(expr, {"__builtins__": {}})
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
            q = re.sub(r'^(what|who|where|when) is ', '', t)
            if "capital of" in t:
                q = "capital of " + t.split("capital of")[-1].strip()

            try:
                # Wikipedia search
                sr = httpx.get("https://en.wikipedia.org/w/api.php",
                    params={"action": "query", "list": "search", "srsearch": q, "format": "json"},
                    timeout=6.0)
                results = sr.json().get("query", {}).get("search", [])
                if results:
                    title = results[0]["title"]
                    sm = httpx.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}", timeout=6.0)
                    if sm.status_code == 200:
                        ans = sm.json().get("extract", "")[:200]
                        if ans:
                            test = f"import httpx; r=httpx.get('https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}'); print(r.json().get('extract','')[:200])"
                            return ans, test
            except Exception:
                pass

        return f"Simulated future for: {clean}", "# no auto test"

    def act(self, text: str) -> str:
        output = io.StringIO()
        safe_builtins = {
            'print': print, 'range': range, 'len': len, 'sum': sum,
            'min': min, 'max': max, 'abs': abs, 'round': round,
            'str': str, 'int': int, 'float': float, 'list': list, 'dict': dict,
        }
        try:
            with contextlib.redirect_stdout(output):
                exec(text, {'__builtins__': safe_builtins, 'httpx': httpx}, {})
            return output.getvalue() or "code ran with no output"
        except Exception:
            return "Error:\n" + traceback.format_exc()[-300:]