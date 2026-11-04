"""Guest-only worker. Candidate source shares this process, so all output is untrusted."""
import importlib.util
import json
from pathlib import Path
from time import perf_counter_ns


def main():
    limits = json.loads(Path("/work/inputs.json").read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("candidate", "/work/candidate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    count = getattr(module, "count_primes")
    results, durations = [], []
    for limit in limits:
        start = perf_counter_ns()
        result = count(limit)
        elapsed = perf_counter_ns() - start
        results.append(result)
        durations.append(elapsed)
    print("PHIRSI_RESULT=" + json.dumps({
        "limits": limits, "results": results, "durations_ns": durations,
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
