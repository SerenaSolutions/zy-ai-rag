#!/usr/bin/env python3
"""ZY-AI-RAG — trivalent AI decision for CI: BM25 retrieval, optional LLM
translator, ZYQL quantum-gate verdict, sealed Z-QEA receipt.

Two declared modes (the receipt always records which one ran):
  LLM     — GOOGLE_API_KEY present: the translator formulates the purpose rule.
  OFFLINE — no key: the rule comes from --rule (explicit JSON input).
Nothing pretends: the receipt declares its mode, its citations, its seal rule.
Exit 0 = decision reached and sealed; 2 = usage/malformed.
"""
import sys, os, json, argparse, hashlib, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zyql_rag_layer import bm25_rank, llm_formulate, parse_rule, CORPUS
from zyql_quantum_gate import ZYQLQuantumGate, ghz_integrity

def seal(rec):
    payload = {k: v for k, v in rec.items() if k != "selo_sha3_256"}
    return hashlib.sha3_256(json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str).encode()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True)
    ap.add_argument("--rule", help='purpose rule JSON: {"kind":"constant","value":1} | {"kind":"parity"}')
    ap.add_argument("--corpus", help="corpus JSON file (default: house corpus)")
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--out", default="zy_ai_rag_receipt.json")
    ap.add_argument("--epsilon", type=float, default=None,
                    help="v1.9.0 — erro máximo declarado (banda adaptativa Hoeffding)")
    ap.add_argument("--require-trust", action="store_true",
                    help="v1.9.0 — porta de integridade GHZ: testa o dispositivo antes do veredito")
    a = ap.parse_args()
    corpus = json.load(open(a.corpus)) if a.corpus else CORPUS
    retrieved = bm25_rank(a.question, corpus)
    context = "\n".join("[%s] %s" % (d["source"], d["text"]) for d, _ in retrieved)
    key = os.environ.get("GOOGLE_API_KEY", "")
    if key:
        mode = "LLM (gemini-3.5-flash translator; key provided as secret)"
        rule_text = llm_formulate(a.question, context)
    elif a.rule:
        mode = "OFFLINE (rule given as explicit input; no LLM call happened)"
        rule_text = a.rule
    else:
        print("ZY-AI-RAG: need --rule (offline) or GOOGLE_API_KEY (LLM mode)"); return 2
    f, rule = parse_rule(rule_text)
    device_gate = None
    if a.require_trust:
        device_gate = ghz_integrity(n=3, shots=1024, seed=1701)
        if not device_gate["device_trusted"]:
            rec = {"spec": "Z-QEA", "modulo": "zy_ai_rag.py (SerenaSolutions/zy-ai-rag)",
                   "data": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                   "question": a.question, "mode": mode,
                   "gate": {"decision": "REFUSED", "modo": "REFUSED_DEVICE_DECOHERED (v1.9.0)",
                            "device_gate": device_gate, "oracle_calls_quantum": 0}}
            rec["selo_sha3_256"] = seal(rec)
            json.dump(rec, open(a.out, "w"), ensure_ascii=True, indent=1)
            print("ZY-AI-RAG decisao: REFUSED (dispositivo inconfiável — GHZ", 
                  device_gate["fidelity_ghz"], ") sem gastar oráculo")
            return 3
    g = ZYQLQuantumGate(3, f)
    r = g.run_quantum(shots=a.shots, epsilon=a.epsilon)
    rec = {"spec": "Z-QEA", "modulo": "zy_ai_rag.py (SerenaSolutions/zy-ai-rag)",
           "data": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "question": a.question, "mode": mode, "mode_llm": bool(key),
           "rag_context": [{"source": d["source"], "score": s} for d, s in retrieved],
           "llm": {"model": "gemini-3.5-flash" if key else None, "rule_parsed": rule},
           "gate": {"decision": r["decision"], "p0": round(g.p0, 4), "oracle_calls_quantum": g.oracle_calls,
                    "kernel": "ZYQL v1.9.0 (SIMULATION statevector local) — declared honestly, no hardware",
                    "epsilon_declared": a.epsilon, "error_bound": r.get("error_bound"),
                    "device_gate": device_gate},
           "selo_regra": "selo = SHA3-256 sobre json.dumps(recibo, sort_keys=True, ensure_ascii=True, default=str) com selo_sha3_256 REMOVIDO da entrada"}
    rec["selo_sha3_256"] = seal(rec)
    json.dump(rec, open(a.out, "w"), ensure_ascii=True, indent=1)
    print("ZY-AI-RAG decisao:", r["decision"], "| modo:", ("LLM" if key else "OFFLINE"),
          "| selo:", rec["selo_sha3_256"][:16] + "...")
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            fh.write("decision=%s\nseal=%s\n" % (r["decision"], rec["selo_sha3_256"]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
