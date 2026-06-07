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

        # 6. WEB FACTS - Path 2 (fixed)
        if t.startswith(("what is ", "who is ", "where is ", "when is ")) or "capital of" in t:
            try:
                r = httpx.get(
                    "https://api.duckduckgo.com/",
                    params={"q": clean, "format": "json", "no_html": 1, "skip_disambig": 1},
                    timeout=5.0
                )
                data = r.json()
                abstract = data.get("AbstractText", "").strip()

                if not abstract and data.get("RelatedTopics"):
                    first = data["RelatedTopics"][0]
                    if isinstance(first, dict):
                        abstract = first.get("Text", "").strip()

                if abstract:
                    abstract = abstract[:200]
                    safe = clean.replace("\\", "\\\\").replace("'", "\\'")
                    # clean test code - no broken braces
                    test_code = (
                        f"import httpx; "
                        f"r = httpx.get('https://api.duckduckgo.com/', "
                        f"params={{'q': '{safe}', 'format': 'json', 'no_html': 1}}); "
                        f"d = r.json(); "
                        f"a = d.get('AbstractText') or ''; "
                        f"if not a and d.get('RelatedTopics'): a = d['RelatedTopics'][0].get('Text',''); "
                        f"print(a[:200])"
                    )
                    return abstract, test_code
            except Exception as e:
                # fail silently to fallback
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

        # allow httpx for web tests
        safe_globals = {'__builtins__': safe_builtins, 'httpx': httpx}

        try:
            with contextlib.redirect_stdout(output):
                exec(code, safe_globals, {})
            result = output.getvalue()
            return result if result else "code ran with no output"
        except Exception:
            return "Error:\n" + traceback.format_exc()[-300:]