import io
import contextlib
import traceback

class WorldEngine:
    def predict(self, text: str) -> str:
        # keep prediction simple for now
        return f"Simulated future for: {text.strip()}"

    def act(self, text: str) -> str:
        # SAFE PYTHON SANDBOX
        # Only allows basic operations, blocks imports and file access
        code = text.strip()
        output = io.StringIO()
        
        # very restricted builtins
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
            return "Error:\n" + traceback.format_exc()[-300:]  # last 300 chars