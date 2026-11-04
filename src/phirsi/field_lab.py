"""R9: expanded fixed-task local PhiServe evaluation and bounded field evidence.

All network calls reuse R4's direct loopback client. GPU evidence is imported
from a separately operator-initiated PhiServe field-run, NOT measured here.
GGUF SHA-256 hashes identify operator-selected local files; they cannot prove
that those files were the exact weights served. No promotion or code changes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from math import ceil, isfinite
from pathlib import Path
from statistics import median
from time import perf_counter_ns
from typing import Any

from .lab import InvalidExperiment, bounded_int, digest
from .phiserve_bench import (
    _config as r4_config, _extract_answer, _hash_answer, _validate_token,
    preflight, request_json,
)

PLAN_SCHEMA = "phirsi.field_plan.v1"
RECEIPT_SCHEMA = "phirsi.field_receipt.v1"
SUMMARY_SCHEMA = "phirsi.field_summary.v1"
SYSTEM = "Reply only with the requested literal answer, without punctuation or explanation."
# Public, fully versioned exact-match examples. Neither a hidden holdout nor a
# general capability test. Every response is compared to a literal expected.
CASES = (
    {"id":"upper", "category":"text", "prompt":"Write the word orbit in uppercase.", "expected":"ORBIT"},
    {"id":"lower", "category":"text", "prompt":"Write the word QUARTZ in lowercase.", "expected":"quartz"},
    {"id":"reverse", "category":"text", "prompt":"Reverse the letters in the word rotor.", "expected":"rotor"},
    {"id":"reverse2", "category":"text", "prompt":"Reverse the letters in the word star.", "expected":"rats"},
    {"id":"add", "category":"arithmetic", "prompt":"Calculate 37 + 58. Reply with only digits.", "expected":"95"},
    {"id":"subtract", "category":"arithmetic", "prompt":"Calculate 94 - 27. Reply with only digits.", "expected":"67"},
    {"id":"multiply", "category":"arithmetic", "prompt":"Calculate 9 * 8. Reply with only digits.", "expected":"72"},
    {"id":"divide", "category":"arithmetic", "prompt":"Calculate 144 / 12. Reply with only digits.", "expected":"12"},
    {"id":"sort", "category":"ordering", "prompt":"Sort 9, 2, 5 in ascending order. Reply as comma-separated digits with no spaces.", "expected":"2,5,9"},
    {"id":"alpha", "category":"ordering", "prompt":"Which is alphabetically first: kiwi, apple, plum? Reply with the word only.", "expected":"apple"},
    {"id":"extract", "category":"extraction", "prompt":"In 'Nora owns seven blue pens', name the color. One word only.", "expected":"blue"},
    {"id":"literal", "category":"instruction", "prompt":"Reply with exactly the five characters PHI69.", "expected":"PHI69"},
)
CASE_HASH = digest(list(CASES))
NO_AUTHORITY = {
    "automatic_promotion": False,
    "human_review_required": True,
    "exact_match_on_public_toy_tasks_only": True,
    "independent_execution_attestation": False,
    "model_weight_binding_verified": False,
    "gpu_execution_independently_verified": False,
    "vram_from_independently_witnessed_measurement": False,
    "statistical_significance_claim": False,
    "intelligence_improvement_claim": False,
    "external_network_or_model_download": False,
}
PLAN_KEYS = {"schema","model_a","model_b","port","rounds","max_tokens","timeout_seconds",
             "seed","task_sha256","created_utc","plan_sha256"}
ROW_KEYS = {"round","case_id","category","role","position","answer_sha256",
            "exact_match","http_elapsed_ms","provider_tokens"}
MAX_GGUF_BYTES = 64 * 1024**3


def _timestamp(value: Any) -> None:
    if type(value) is not str or len(value) > 64:
        raise InvalidExperiment("invalid timestamp")
    try:
        date = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidExperiment("invalid timestamp") from exc
    if date.utcoffset() is None:
        raise InvalidExperiment("timestamp must have an offset")


def make_plan(*, model_a: str, model_b: str, port: int = 11435, rounds: int = 1,
              max_tokens: int = 32, timeout_seconds: int = 30, seed: int = 369):
    r4_config(model_a, port, rounds, max_tokens, timeout_seconds, seed)
    r4_config(model_b, port, rounds, max_tokens, timeout_seconds, seed)
    bounded_int(rounds, 1, 2, "rounds")
    if model_a == model_b:
        raise InvalidExperiment("two distinct aliases required")
    result = {
        "schema": PLAN_SCHEMA, "model_a": model_a, "model_b": model_b,
        "port": port, "rounds": rounds, "max_tokens": max_tokens,
        "timeout_seconds": timeout_seconds, "seed": seed,
        "task_sha256": CASE_HASH,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    result["plan_sha256"] = digest(result)
    return result


def validate_plan(plan):
    if not isinstance(plan,dict) or set(plan) != PLAN_KEYS or plan["schema"] != PLAN_SCHEMA:
        raise InvalidExperiment("invalid R9 plan")
    original = r4_config(plan["model_a"],plan["port"],plan["rounds"],
                         plan["max_tokens"],plan["timeout_seconds"],plan["seed"])
    r4_config(plan["model_b"],plan["port"],plan["rounds"],plan["max_tokens"],
              plan["timeout_seconds"],plan["seed"])
    if plan["model_a"] == plan["model_b"] or not 1 <= plan["rounds"] <= 2:
        raise InvalidExperiment("invalid pair or rounds")
    for name in ("port","rounds","max_tokens","timeout_seconds","seed"):
        if type(plan[name]) is not int or plan[name] != original[name]:
            raise InvalidExperiment("noncanonical input budget")
    _timestamp(plan["created_utc"])
    if plan["task_sha256"] != CASE_HASH:
        raise InvalidExperiment("fixed task set changed")
    if plan["plan_sha256"] != digest({k:v for k,v in plan.items() if k!="plan_sha256"}):
        raise InvalidExperiment("plan digest mismatch")
    return plan


def fingerprint_gguf(path: Path):
    """Read an explicitly selected regular GGUF, no path or metadata disclosure.

    An operator-chosen file is not proof that PhiServe actually loaded it.
    """
    file = Path(path)
    if file.is_symlink() or not file.is_file():
        raise InvalidExperiment("GGUF must be a regular, non-symlink local file")
    before = file.stat()
    if not 32 <= before.st_size <= MAX_GGUF_BYTES:
        raise InvalidExperiment("GGUF file has unsupported size")
    checksum = sha256()
    count = 0
    with file.open("rb") as stream:
        if stream.read(4) != b"GGUF":
            raise InvalidExperiment("selected file lacks GGUF header")
        stream.seek(0)
        while chunk := stream.read(4*1024*1024):
            checksum.update(chunk)
            count += len(chunk)
            if count > MAX_GGUF_BYTES:
                raise InvalidExperiment("GGUF exceeds 64 GiB")
    after = file.stat()
    if (count != before.st_size or before.st_size != after.st_size or
        before.st_mtime_ns != after.st_mtime_ns or before.st_ino != after.st_ino):
        raise InvalidExperiment("GGUF changed while being hashed")
    return {
        "sha256": checksum.hexdigest(), "size_bytes": count,
        "header": "GGUF", "declared_by_operator": True,
        "bound_to_running_phiserve_process": False,
    }


def field_observation(receipt: Any, alias: str):
    """Conservative, bounded projection of PhiServe's independent field-run JSON."""
    if not isinstance(receipt, dict) or receipt.get("schema") != "PHISERVE_LOCAL_INFERENCE_RECEIPT_V1" \
       or receipt.get("status") != "LOCAL_TEXT_OUTPUT_OBSERVED" or receipt.get("model_alias") != alias \
       or receipt.get("raw_prompt_or_output_stored") is not False \
       or receipt.get("gpu_execution_verified") is not False:
        raise InvalidExperiment("PhiServe field-run identity or evidence flags invalid")
    memory = receipt.get("gpu_process_telemetry")
    if memory is None:
        return {"source_schema": receipt["schema"], "alias": alias,
                "driver_status": "NOT_SAMPLED", "driver_peak_process_memory_mib": None,
                "independently_attested": False, "same_execution_as_r9": False}
    if (not isinstance(memory,dict) or memory.get("schema") != "PHISERVE_NVIDIA_PROCESS_SAMPLE_V1"
        or memory.get("cuda_kernel_execution_independently_verified") is not False
        or memory.get("gpu_model_weights_residency_verified") is not False
        or memory.get("physical_hardware_witnessed") is not False):
        raise InvalidExperiment("malformed GPU field provenance claims")
    allowed = {"PROCESS_MEMORY_DRIVER_SELF_REPORT","PROCESS_PRESENT_MEMORY_UNAVAILABLE",
               "NVIDIA_SMI_UNAVAILABLE","NVIDIA_SMI_QUERY_FAILED",
               "NO_MATCHING_COMPUTE_PROCESS_OBSERVED","SAMPLER_DID_NOT_STOP"}
    status=memory.get("status")
    peak=memory.get("peak_driver_reported_process_memory_mib")
    attempts=memory.get("sample_attempts")
    matched=memory.get("matching_pid_samples")
    numeric=memory.get("numeric_memory_samples")
    if (status not in allowed or any(type(n) is not int or n<0 for n in (attempts,matched,numeric))
        or matched>attempts or numeric>matched
        or ((type(peak) is int and 0<=peak<=1_000_000) if numeric else peak is None) is False
        or (status == "PROCESS_MEMORY_DRIVER_SELF_REPORT") != (numeric>0)):
        raise InvalidExperiment("inconsistent driver memory sample")
    return {
        "source_schema": receipt["schema"], "alias": alias,
        "driver_status": status, "driver_peak_process_memory_mib": peak,
        "independently_attested": False, "same_execution_as_r9": False,
    }


def _order(round_idx,case_idx):
    return ("A","B") if ((round_idx*len(CASES)+case_idx) % 2 == 0) else ("B","A")


def _metrics(rows,plan):
    group={}
    for role in ("A","B"):
        data=[r for r in rows if r["role"]==role]
        duration=[r["http_elapsed_ms"] for r in data]
        usage=[r["provider_tokens"] for r in data]
        group[role]={
            "alias": plan["model_a"] if role=="A" else plan["model_b"],
            "request_count":len(data),
            "correct_count":sum(int(r["exact_match"]) for r in data),
            "exact_match_fraction":round(sum(int(r["exact_match"]) for r in data)/len(data),6),
            "median_http_ms":round(median(duration),3),
            "p95_http_ms":sorted(duration)[ceil(len(duration)*.95)-1],
            "provider_tokens_total":sum(usage) if all(x is not None for x in usage) else None,
            "approx_total_http_tokens_per_second":round(sum(usage)/(sum(duration)/1000),3)
                if all(x is not None for x in usage) else None,
        }
    cats={}
    for cat in sorted({x["category"] for x in CASES}):
        cats[cat]={role:{
            "correct":sum(int(x["exact_match"]) for x in rows
                          if x["category"]==cat and x["role"]==role),
            "attempted":sum(1 for x in rows if x["category"]==cat and x["role"]==role),
        } for role in ("A","B")}
    return {
        "models":group, "categories":cats, "cases_per_model":len(CASES)*plan["rounds"],
        "total_post_requests":len(rows), "decision":"DESCRIPTIVE_ONLY_NO_WINNER",
        "statistical_significance_calculated":False, "model_intelligence_gain_claim":False,
        "independent_replication":False, "automatic_promotion":False,
    }


def _source_hash():
    return sha256(Path(__file__).read_bytes()).hexdigest()


def run_field(plan, *, token=None, approved=False, gguf_paths=None, phiserve_fields=None):
    validate_plan(plan)
    if approved is not True:
        raise InvalidExperiment("explicit operator approval required")
    _validate_token(token)
    gguf_paths = gguf_paths or {}
    phiserve_fields = phiserve_fields or {}
    if not isinstance(gguf_paths,dict) or not set(gguf_paths).issubset({"A","B"}):
        raise InvalidExperiment("unsupported GGUF evidence role")
    if not isinstance(phiserve_fields,dict) or not set(phiserve_fields).issubset({"A","B"}):
        raise InvalidExperiment("unsupported PhiServe evidence role")
    fingerprints={role:fingerprint_gguf(path) for role,path in gguf_paths.items()}
    related={role:field_observation(value,plan["model_a"] if role=="A" else plan["model_b"])
             for role,value in phiserve_fields.items()}
    preflight(model=plan["model_a"],port=plan["port"],token=token)
    preflight(model=plan["model_b"],port=plan["port"],token=token)
    observations=[]
    for rnd in range(plan["rounds"]):
        for idx,task in enumerate(CASES):
            for position,role in enumerate(_order(rnd,idx),1):
                alias=plan["model_a"] if role=="A" else plan["model_b"]
                request={"model":alias,"stream":False,"temperature":0,"seed":plan["seed"],
                         "max_tokens":plan["max_tokens"],
                         "messages":[{"role":"system","content":SYSTEM},
                                     {"role":"user","content":task["prompt"]}]}
                before=perf_counter_ns()
                reply=request_json("POST","/v1/chat/completions",port=plan["port"],
                                   timeout_seconds=plan["timeout_seconds"],
                                   token=token,payload=request)
                elapsed=max(.001,round((perf_counter_ns()-before)/1e6,3))
                answer,tokens=_extract_answer(reply)
                h=_hash_answer(answer)
                observations.append({
                    "round":rnd+1,"case_id":task["id"],"category":task["category"],
                    "role":role,"position":position,"answer_sha256":h,
                    "exact_match":h==_hash_answer(task["expected"]),
                    "http_elapsed_ms":elapsed,"provider_tokens":tokens,
                })
    receipt={
        "schema":RECEIPT_SCHEMA,"plan":plan,"code_sha256":_source_hash(),
        "recorded_utc":datetime.now(timezone.utc).isoformat(),
        "observations":observations,"metrics":_metrics(observations,plan),
        "selected_local_file_fingerprints":fingerprints,
        "separate_phiserve_field_observations":related,
        "governance":dict(NO_AUTHORITY),
    }
    receipt["receipt_sha256"]=digest(receipt)
    return receipt


def verify_field(receipt):
    try:
        if not isinstance(receipt,dict) or set(receipt)!={
            "schema","plan","code_sha256","recorded_utc","observations","metrics",
            "selected_local_file_fingerprints","separate_phiserve_field_observations",
            "governance","receipt_sha256"}:
            raise InvalidExperiment("invalid receipt fields")
        if receipt["schema"] != RECEIPT_SCHEMA:
            raise InvalidExperiment("unknown R9 schema")
        if receipt["receipt_sha256"] != digest({k:v for k,v in receipt.items() if k!="receipt_sha256"}):
            raise InvalidExperiment("R9 receipt hash mismatch")
        plan=validate_plan(receipt["plan"])
        _timestamp(receipt["recorded_utc"])
        if receipt["code_sha256"] != _source_hash() or receipt["governance"] != NO_AUTHORITY:
            raise InvalidExperiment("source or authority mismatch")
        fingerprints=receipt["selected_local_file_fingerprints"]
        if not isinstance(fingerprints,dict) or not set(fingerprints).issubset({"A","B"}):
            raise InvalidExperiment("invalid file provenance roles")
        for value in fingerprints.values():
            if not isinstance(value,dict) or set(value)!={"sha256","size_bytes","header",
                    "declared_by_operator","bound_to_running_phiserve_process"} \
               or type(value["sha256"]) is not str or len(value["sha256"])!=64 \
               or any(c not in "0123456789abcdef" for c in value["sha256"]) \
               or type(value["size_bytes"]) is not int or not 32<=value["size_bytes"]<=MAX_GGUF_BYTES \
               or value["header"]!="GGUF" or value["declared_by_operator"] is not True \
               or value["bound_to_running_phiserve_process"] is not False:
                raise InvalidExperiment("invalid GGUF fingerprint format or attestation")
        related=receipt["separate_phiserve_field_observations"]
        if not isinstance(related,dict) or not set(related).issubset({"A","B"}):
            raise InvalidExperiment("invalid external field roles")
        for role,value in related.items():
            alias=plan["model_a"] if role=="A" else plan["model_b"]
            if not isinstance(value,dict) or set(value)!={
                "source_schema","alias","driver_status","driver_peak_process_memory_mib",
                "independently_attested","same_execution_as_r9"} \
               or value["source_schema"]!="PHISERVE_LOCAL_INFERENCE_RECEIPT_V1" \
               or value["alias"]!=alias \
               or value["driver_status"] not in {
                   "NOT_SAMPLED","PROCESS_MEMORY_DRIVER_SELF_REPORT",
                   "PROCESS_PRESENT_MEMORY_UNAVAILABLE","NVIDIA_SMI_UNAVAILABLE",
                   "NVIDIA_SMI_QUERY_FAILED","NO_MATCHING_COMPUTE_PROCESS_OBSERVED",
                   "SAMPLER_DID_NOT_STOP"} \
               or value["independently_attested"] is not False \
               or value["same_execution_as_r9"] is not False \
               or (value["driver_status"]=="PROCESS_MEMORY_DRIVER_SELF_REPORT") !=
                  (type(value["driver_peak_process_memory_mib"]) is int and
                   0 <= value["driver_peak_process_memory_mib"] <= 1_000_000) :
                raise InvalidExperiment("external field evidence invalid")
        rows=receipt["observations"]
        if not isinstance(rows,list) or len(rows)!=plan["rounds"]*len(CASES)*2:
            raise InvalidExperiment("missing R9 observations")
        n=0
        for rnd in range(plan["rounds"]):
            for idx,task in enumerate(CASES):
                for position,role in enumerate(_order(rnd,idx),1):
                    row=rows[n]; n+=1
                    if not isinstance(row,dict) or set(row)!=ROW_KEYS or \
                       row["round"]!=rnd+1 or type(row["round"]) is not int or \
                       row["case_id"]!=task["id"] or row["category"]!=task["category"] or \
                       row["role"]!=role or row["position"]!=position or type(row["position"]) is not int:
                        raise InvalidExperiment("R9 row order or fields changed")
                    h=row["answer_sha256"]
                    if type(h) is not str or len(h)!=64 or any(c not in "0123456789abcdef" for c in h) \
                       or type(row["exact_match"]) is not bool or row["exact_match"]!=(h==_hash_answer(task["expected"])):
                        raise InvalidExperiment("R9 answer evidence mismatch")
                    t=row["http_elapsed_ms"]
                    if type(t) not in (float,int) or not isfinite(t) or not 0<t<=plan["timeout_seconds"]*1000+1000:
                        raise InvalidExperiment("R9 latency invalid")
                    count=row["provider_tokens"]
                    if count is not None and (type(count) is not int or not 0<=count<=10000):
                        raise InvalidExperiment("invalid reported token count")
        if receipt["metrics"]!=_metrics(rows,plan):
            raise InvalidExperiment("derived score mismatch")
        return {"passed":True,"receipt_consistency_checked":True,
                "historical_inference_authenticated":False,"weight_binding_verified":False,
                "gpu_execution_verified":False,"automatic_promotion":False}
    except (InvalidExperiment,ValueError,KeyError,TypeError,IndexError,ZeroDivisionError,OverflowError):
        return {"passed":False,"receipt_consistency_checked":False,
                "historical_inference_authenticated":False,"weight_binding_verified":False,
                "gpu_execution_verified":False,"automatic_promotion":False}


def browser_summary(receipt):
    if not verify_field(receipt)["passed"]:
        raise InvalidExperiment("cannot export invalid R9 receipt")
    result={
        "schema":SUMMARY_SCHEMA,"source_receipt_sha256":receipt["receipt_sha256"],
        "aliases":{"A":receipt["plan"]["model_a"],"B":receipt["plan"]["model_b"]},
        "metrics":receipt["metrics"],
        "selected_file_fingerprints":receipt["selected_local_file_fingerprints"],
        "separate_driver_observations":receipt["separate_phiserve_field_observations"],
        "governance":dict(NO_AUTHORITY),
        "not_authenticating_source":True,"read_only_browser_preview":True,
    }
    result["summary_sha256"]=digest(result)
    return result
