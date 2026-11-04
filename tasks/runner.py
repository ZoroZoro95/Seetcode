import sys
import uuid
import subprocess
from pathlib import Path
import json

def run_python(source_path: Path, stdin: str, timeout_seconds: float) -> dict:
    container_name = f"judge-{uuid.uuid4().hex}"
    # print(f"The generated container name is: {container_name}")

    # command construction for subprocess
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--name", container_name,
        "--network", "none",
        "--memory", "128m",
        "--cpus", "0.5",
        "--pids-limit", "32",
        "--read-only",
        "--user", "65534:65534",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--tmpfs", "/tmp:size=16m",
        "-i",
        "-v", f"{source_path}:/code/sum_numbers.py:ro",
        "python:3.13-slim",
        "python", "-B", "/code/sum_numbers.py"
    ]
    try :
        run_result = subprocess.run(
            docker_cmd,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        rc = run_result.returncode
    except subprocess.TimeoutExpired:
        cleanup_stderr = ""
        try:
            cleanup = subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if cleanup.returncode != 0:
                cleanup_stderr = cleanup.stderr.strip() or f"docker rm exited with code {cleanup.returncode}"
        except subprocess.TimeoutExpired:
            cleanup_stderr = "docker rm timed out"
        except OSError as e:
            cleanup_stderr = f"docker rm failed: {e}"

        return {
            "status": "TIME_LIMIT_EXCEEDED",
            "exit_code": None,
            "stdout": "",
            "stderr": cleanup_stderr,
        }
    except OSError as e:
        cleanup_stderr = f"failed to create a docker container: {e}"

        return {
            "status": "INTERNAL_ERROR",
            "exit_code": None,
            "stdout": "",
            "stderr": cleanup_stderr,
        }
    
    #rc with meaning
    if rc == 0:
        status = "OK"
    elif rc in (125, 126, 127):
        status = "INTERNAL_ERROR"
    else:
        status = "RUNTIME_ERROR"    
    return {
        "status" : status,
        "exit_code": run_result.returncode,
        "stdout": run_result.stdout,
        "stderr": run_result.stderr,
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python runner.py <source.py> <stdin>", file=sys.stderr)
        sys.exit(1)

    stdin = sys.argv[2]

    # Convert source arg to absolute path
    source = Path(sys.argv[1]).resolve()

    # Check that it's an existing regular file with a .py suffix
    if not source.is_file():
        print(f"Error: '{source}' is not an existing regular file.", file=sys.stderr)
        sys.exit(1)

    if source.suffix != ".py":
        print(f"Error: '{source}' does not have a .py suffix.", file=sys.stderr)
        sys.exit(1)

    result = run_python(source, stdin, timeout_seconds=2)
    
    print(json.dumps(result))
    # print(result["stdout"], end="")

    # if result["stderr"]:
    #     print("stderr:", result["stderr"])

    # print("returncode:", result["exit_code"])
