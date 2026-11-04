# Python Docker runner — Task 1

A learning project that executes one Python source file in a restricted Docker
container, supplies standard input, and reports execution results as JSON.

This runner checks execution status. It does not compare output with an expected
answer, so `OK` does not mean a solution is correct. That comparison belongs to
Task 2.

## Requirements and setup

- Python 3 on your computer; no third-party Python packages are required.
- Docker installed and its engine running. On macOS, start Docker Desktop.
- The `python:3.13-slim` image available locally.

Download the image before testing, so the two-second waiting budget is not spent
downloading it:

```bash
docker pull python:3.13-slim
```

From the repository root, enter the task folder. All commands below assume this
working directory:

```bash
cd tasks
```

## Interface

```bash
python3 runner.py <source.py> "<stdin>"
```

The second argument is the entire input string. Quotes keep spaces inside one
command-line argument. Use `""` for empty input.

The reusable function is:

```python
def run_python(
    source_path: Path,
    stdin: str,
    timeout_seconds: float,
) -> dict:
    ...
```

The command-line interface uses a two-second timeout and prints one JSON result.
Invalid arguments or source paths produce a message on stderr and exit with code
1 instead of running Docker.

## Four execution checks

These commands reproduce the four execution cases we tested. The original
verification used a temporary harness to observe each unique container name;
the application commands below exercise the same runner and examples.

### 1. Normal execution

```bash
python3 runner.py examples/hello.py ""
```

Checks that a Python file can be mounted read-only, executed in the container,
and have its output captured in a JSON result.

Recorded result:

```json
{"status": "OK", "exit_code": 0, "stdout": "Hello user\n", "stderr": ""}
```

### 2. Standard input and calculation

```bash
python3 runner.py examples/input_sum.py "5 7"
```

Checks that the runner forwards the input string to the container's stdin. The
example reads two integers and prints their sum, including the final newline.

Recorded result:

```json
{"status": "OK", "exit_code": 0, "stdout": "12\n", "stderr": ""}
```

### 3. User-code runtime error

```bash
python3 runner.py examples/runtime_error.py ""
```

Checks that division by zero produces `RUNTIME_ERROR`, preserves the non-zero
exit code, and captures the Python traceback in stderr.

Recorded result:

```json
{"status": "RUNTIME_ERROR", "exit_code": 1, "stdout": "", "stderr": "Traceback (most recent call last):\n  File \"/code/sum_numbers.py\", line 4, in <module>\n    print(a/b)\n          ~^~\nZeroDivisionError: division by zero\n"}
```

`/code/sum_numbers.py` is the current container mount target for every submitted
file, so that path also appears in this traceback.

### 4. Timeout and cleanup

```bash
python3 runner.py examples/infinite_loop.py ""
```

Checks that a silent infinite loop exceeds the two-second host waiting limit,
then triggers forced removal of its uniquely named container. Cleanup has a
separate three-second timeout.

Recorded result:

```json
{"status": "TIME_LIMIT_EXCEEDED", "exit_code": null, "stdout": "", "stderr": ""}
```

The recorded run took approximately 2.11 seconds including cleanup. This is not
a guarantee that every invocation returns within exactly two seconds.

## Verify the container is gone

`TIME_LIMIT_EXCEEDED` alone does not prove the container was removed. During the
recorded test, the harness checked the exact generated name after the runner
returned:

```bash
docker ps -a --filter 'name=^/judge-9571a1616c49462dafa3d93d7194df62$' --format '{{.Names}}'
```

The command succeeded with **no output**: no running or stopped container with
that name remained. The runner's own cleanup succeeded; the test harness did
not need to remove a leftover container. That name belongs to the recorded run;
new executions generate new names.

For a simple manual check, list runner containers before and after a new test:

```bash
docker ps -a --filter 'name=^/judge-' --format '{{.Names}}\t{{.Status}}'
python3 runner.py examples/infinite_loop.py ""
docker ps -a --filter 'name=^/judge-' --format '{{.Names}}\t{{.Status}}'
```

With no other runner containers and no concurrent executions, both listings
should be empty. If other containers already exist, compare against the initial
listing; a shared prefix does not identify one execution. A Docker connection
error is not evidence of successful cleanup.

`docker ps` lists running containers. `docker ps -a` also includes stopped ones,
which is why the cleanup check uses `-a`.

## Container settings

| Setting | Purpose |
| --- | --- |
| `--rm` | Remove the container when it exits; retain the image. |
| `--name judge-<UUID>` | Give each execution a distinct name for targeted cleanup. |
| `-i` | Keep stdin open so the runner can supply input. |
| `-v <source>:/code/sum_numbers.py:ro` | Expose the source file through a read-only bind mount. |
| `--network none` | Disable external container networking; retain loopback. |
| `--memory 128m` | Limit RAM to 128 MiB; swap is controlled separately. |
| `--cpus 0.5` | Limit CPU capacity to approximately half of one CPU; does not impose a deadline. |
| `--pids-limit 32` | Limit simultaneous processes and threads to 32. |
| `--read-only` | Make the container's root filesystem read-only. |
| `--user 65534:65534` | Run under the specified non-root user and group IDs. |
| `--cap-drop ALL` | Remove Linux capabilities. |
| `--security-opt no-new-privileges` | Prevent gaining privileges through executing another program. |
| `--tmpfs /tmp:size=16m` | Supply a temporary writable filesystem at `/tmp`, capped at 16 MiB. |
| `python -B` | Disable writing Python bytecode files. |

## Result interpretation and limits

- `OK`: completed with exit code 0.
- `RUNTIME_ERROR`: completed non-zero, except for the special codes below.
- `TIME_LIMIT_EXCEEDED`: the host's wait for `docker run` expired.
- `INTERNAL_ERROR`: launching Docker raised `OSError`, or Docker returned 125,
  126, or 127 under this runner's basic classification policy.

Docker-code classification is ambiguous if user code deliberately exits with
125, 126, or 127. It is not definitive evidence of where a failure occurred.

Timing out the Docker client does not guarantee the engine-managed container
stops. The runner therefore requests `docker rm -f` using that execution's name.
Cleanup problems are reported in the timeout result's stderr. The timeout path
currently discards any output the submitted program produced before timing out.

The waiting budget includes container startup, not just submitted-code runtime.
Output capture is not size-limited, so these checks deliberately use a silent
infinite loop. No memory-limit verdict detection is implemented, and these
restrictions do not establish a complete sandbox for hostile submissions.

The four recorded demonstrations passed before the folder was renamed from
`tasls` to `tasks`. They verify those execution paths, rather than every possible
Docker failure or adversarial case.
