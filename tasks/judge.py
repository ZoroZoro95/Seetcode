from pathlib import Path
from runner import run_python
import sys
import json
def judge_one(source_path: Path , input_path : Path, expected_output_path : Path, timeout_seconds:float)-> dict:
    input_text = input_path.read_text(encoding="utf-8")
    expected_output_text = expected_output_path.read_text(encoding="utf-8")

    execution = run_python(source_path,input_text,timeout_seconds)
    verdict = "WRONG_ANSWER"
    if execution['status'] != "OK":
        verdict = execution['status']
    else:
        if execution['stdout'] == expected_output_text:
            verdict = "ACCEPTED"
        else:
            verdict = "WRONG_ANSWER"

    return {
        "verdict"  : verdict,
        "execution" : execution
    }

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python judge.py <source.py> <input.txt> <expected.txt>", file=sys.stderr)
        sys.exit(1)
    
    source_path = Path(sys.argv[1]).resolve()
    input_path = Path(sys.argv[2]).resolve()
    expected_output_path = Path(sys.argv[3]).resolve()

    result = judge_one(source_path,input_path,expected_output_path,2)
    print(json.dumps(result))
