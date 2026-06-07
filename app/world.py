import io
import contextlib
import traceback
import re

class WorldEngine:
    def predict(self, text: str) -> tuple[str, str]:
        # returns (prediction, suggested_test_code)
        clean = text.strip()
        lowered = clean.lower().replace("what is", "").strip()
        
        # if it looks like simple math, solve it
        if re.match(r'^[0-9+\-*/().\s]+$', lowered) and lowered:
            try:
                result = eval(lowered, {"__builtins__": {}}, {})
                prediction = str(result)
                test_code = f"print({lowered})"
                return prediction, test_code
            except:
                pass
        
        # fallback for everything else
        prediction = f"Simulated future for: {clean}"
        test_code = "# no auto test"
        return prediction, test_code

    def act(self, text: str) -> str:
        # SAFE PYTHON SANDBOX
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