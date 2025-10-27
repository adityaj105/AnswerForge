# answerforge/verifier/docker_sandbox.py
import subprocess, tempfile, os, textwrap
from typing import Dict

def run_in_docker(code: str, timeout: int = 5) -> Dict:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
        tmp.write(textwrap.dedent(code))
        tmp_path = tmp.name
    try:
        cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", "64m",
            "--cpus", "0.5",
            "-v", f"{tmp_path}:/sandbox/code.py:ro",
            "answerforge-sandbox",
            "python3", "/sandbox/code.py"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"ok": proc.returncode == 0, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip(), "return_code": proc.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "stdout": "", "stderr": ""}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
