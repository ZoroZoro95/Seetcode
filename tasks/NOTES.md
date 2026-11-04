# runner.py — Concepts & Syntax Reference

## `sys.argv`
Command-line arguments passed to the script.
```python
# Running: python runner.py examples/input_sum.py "5 7"
sys.argv[0]  # "runner.py"          → the script itself
sys.argv[1]  # "examples/input_sum.py" → first argument
sys.argv[2]  # "5 7"               → second argument
```

---

## `Path(x).resolve()`
Converts a relative path string into an absolute path.
```python
from pathlib import Path
source = Path("examples/input_sum.py").resolve()
# → /Users/siddharth/.../tasls/examples/input_sum.py
```
- `.is_file()` → True if the path exists and is a regular file (not a directory)
- `.suffix`    → file extension, e.g. `".py"`

---

## `uuid.uuid4().hex`
Generates a random, globally unique identifier as a 32-character hex string.
```python
import uuid
name = f"judge-{uuid.uuid4().hex}"
# → "judge-a3f1c2d4b5e6f7a8b9c0d1e2f3a4b5c6"
```
Used to give each Docker container a unique name so multiple runs don't collide.

---

## `subprocess.run()` — running a child process
```python
import subprocess
result = subprocess.run(
    ["python3", "script.py"],  # command as a list (safe, no shell injection)
    input="5 7",               # string sent to the child's stdin
    capture_output=True,       # capture stdout and stderr
    text=True,                 # decode bytes → str automatically
    timeout=10,                # raise TimeoutExpired if it takes too long
)
```

### Why a list, not a string?
| `["docker", "run", "--name", "x"]` | `"docker run --name x"` |
|---|---|
| Safe — no shell injection | Dangerous with user input |
| Spaces in values handled automatically | Must escape manually |
| Works with `shell=False` (default) | Needs `shell=True` |

### `CompletedProcess` — what `subprocess.run()` returns
```python
result.stdout      # everything the child printed to stdout
result.stderr      # everything the child printed to stderr
result.returncode  # exit code: 0 = success, non-zero = error
result.args        # the command that was run
```

---

## `file=sys.stderr` in `print()`
`print()` writes to `sys.stdout` by default. Pass `file=sys.stderr` to write to the error stream instead.
```python
print("Something went wrong", file=sys.stderr)  # → stderr
print(json.dumps(result))                        # → stdout (default)
```
**Why it matters:** Tools that pipe your output (shell scripts, CI, JSON parsers)
only read stdout. Errors on stderr won't corrupt the expected output.

---

## `json.dumps()` vs `json.dump()`
```python
import json

json.dumps(obj)        # → returns a JSON string (use inside print())
json.dump(obj, file)   # → writes JSON directly to a file object, returns None
```
Always use `json.dumps()` when you want to print JSON to stdout.

---

## Docker command structure
```
docker run [OPTIONS] IMAGE [COMMAND]
```
As a Python list:
```python
docker_cmd = [
    "docker", "run",
    "--rm",                            # auto-remove container after exit
    "--name", container_name,          # unique container name
    "-i",                              # keep stdin open (needed to pipe input)
    "-v", f"{source}:/code/sol.py:ro", # mount file into container (read-only)
    "python:3.13-slim",                # Docker image to use
    "python", "-B", "/code/sol.py"    # command to run inside container
]
# -B tells Python not to write .pyc bytecode cache files
```

---

## Security restrictors (Docker flags)
| Flag | Purpose |
|---|---|
| `--network none` | No internet access |
| `--memory 128m` | Max RAM (prevents memory exhaustion) |
| `--cpus 0.5` | Max CPU (prevents runaway loops from hogging host) |
| `--pids-limit 32` | Max processes (prevents fork bombs) |
| `--read-only` | Filesystem is read-only |
| `--user 65534:65534` | Run as `nobody` — lowest privilege user, not root |
| `--cap-drop ALL` | Drops all Linux capabilities (no mounting, no raw sockets, etc.) |
| `--security-opt no-new-privileges` | Process can't escalate its own privileges |
| `--tmpfs /tmp:size=16m` | Small RAM-backed writable scratch space (needed because `--read-only` blocks all writes) |

---

## Return code → status mapping
| `returncode` | Status | Reason |
|---|---|---|
| `0` | `OK` | Ran successfully |
| `125` | `INTERNAL_ERROR` | Docker itself failed |
| `126` | `INTERNAL_ERROR` | Container command could not be invoked |
| `127` | `INTERNAL_ERROR` | Container command not found |
| Any other non-zero | `RUNTIME_ERROR` | Program crashed (exception, bad input, etc.) |

> **Note:** Submitted code can deliberately exit with 125/126/127 too.
> This mapping is a policy choice, not a perfect distinction.

---

## `if __name__ == "__main__":`
Code inside this block only runs when the file is executed directly (`python runner.py`).
It does **not** run when the file is imported as a module (`import runner`).
This lets `run_python()` be reused by other files without triggering the CLI logic.
