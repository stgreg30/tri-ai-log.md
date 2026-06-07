import io
import contextlib
import traceback
import re

class WorldEngine:
    def predict(self, text: str) -> tuple[str, str]:
        clean = text.strip()
        t = clean.lower()

        # 1. MATH - "what is 7*7" or "12*12"
        m = re.search(r'what is ([\d+\-*/().\s]+)', t)
        expr = m.group(1) if m else t
        if re.match(r'^[\d+\-*/().\s]+$', expr) and expr.strip():
            try:
                result = eval(expr, {"__builtins__": {}}, {})
                return str(result), f"print({expr})"
            except:
                pass

        # 2. REVERSE - "reverse hello"
        m = re.search(r'reverse (.+)', t)
        if m:
            s = m.group(1).strip()
            # escape quotes for safe code
            safe = s.replace("'", "\\'")
            return s[::-1], f"print('{safe}'[::-1])"

        # 3. UPPERCASE - "uppercase ash"
        m = re.search(r'uppercase (.+)', t)
        if m:
            s = m.group(1).strip()
            safe = s.replace("'", "\\'")
            return s.upper(), f"print('{safe}'.upper())"

        # 4. LOWERCASE - "lowercase ASH"
        m = re.search(r'lowercase (.+)', t)
        if m:
            s = m.group(1).strip()
            safe = s.replace("'", "\\'")
            return s.lower(), f"print('{safe}'.lower())"

        # 5. LENGTH - "how many letters in banana" or "length of banana"
        m = re.search(r'(how many letters in|length of) (.+)', t)
        if m:
            s = m.group(2).strip()
            safe = s.replace("'", "\\'")
            count = len(s.replace(' ', ''))
            return str(count), f"print(len('{safe}'.replace(' ','')))"

        # fallback - your original
        return f"Simulated future for: {clean}", "# no auto test"

    def act(self, text: str) -> str:
        # YOUR SAFE SANDBOX - unchanged
        code = text.strip()
        output = io.StringIO()
        
        safe_builtins = {
            'print': print,
            'range': range,
            'len': len,
            'sum': sum,
            'min': min,
            'max': max,
            'abs': abs,
            'round': round,
            'str': str,
            'int': int,
            'float': float,
            'list': list,
            'dict': dict,
        }
        
        safe_globals = {'__builtins__': safe_builtins}
        
        try:
            with contextlib.redirect_stdout(output):
                exec(code, safe_globals, {})
            result = output.getvalue()
            return result if result else "code ran with no output"
        except Exception:
            return "Error:\n" + traceback.format_exc()[-300:]