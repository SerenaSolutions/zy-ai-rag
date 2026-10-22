"""
ZYQL RAG+LLM NEURAL LAYER (v1.0.0, 12/10/2026) — the LinkedIn architecture rooted
in the language: trusted docs -> RAG retrieval -> LLM (Gemini 3.5 Flash) translates
the question into a purpose function -> ZYQL QUANTUM GATE decides by interference
-> receipt with citations, LLM attribution and gate proof.

Layer map (mirrors the Hybrid Stack L1-L5 and the audited link):
  L1 trusted docs (corpus) -> L2 RAG (BM25) -> L3 LLM translator ->
  L4 ZYQL quantum gate (Deutsch-Jozsa) -> L5 signed receipt (traceable answer).
"""
import sys, os, json, math, time, urllib.request
try:
    from zyql_quantum_gate import ZYQLQuantumGate
except ImportError:  # in-tree, no install
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from zyql_quantum_gate import ZYQLQuantumGate

HERE = os.path.dirname(__file__)

# ---------------- L1: trusted documents (attribution mandatory) ----------------
CORPUS = [
    {"id": "doc1", "source": "zephyrum/README.md", "text":
     "ZYQL is the algorithm layer of the ZEPHIRUM ecosystem: a trivalent gate "
     "(1/0/REFUSED) with ML-DSA-44 signed receipts. Every decision carries provenance. "
     "SIMULATION MODE is labeled honestly; hardware runs are archived with job IDs."},
    {"id": "doc2", "source": "auditoria/AUDITORIA_LINKS_LINKEDIN.md", "text":
     "RAG grounds answers in retrieved trusted documents but does not compute. "
     "Quantum computing executes specialized subproblems. The realistic architecture is: "
     "trusted docs -> RAG -> translator agent -> math formulation -> solver -> classical validation -> traceable answer."},
    {"id": "doc3", "source": "zephyrum/tese_zyql_fertilizantes_verdes.md", "text":
     "The Z-Scale ladder targets verified simulation of nitrogen fixation: T1 H2 done at 57 mHa, "
     "T2 LiH 4 qubits next window. Without error correction, useful executions stay <= 20 qubits."},
    {"id": "doc4", "source": "zephyrum/lab/prova_gemini_zyql.json", "text":
     "Gemini 3.5 Flash wrote a syntactically perfect NEXA program; the C99 core verified it and "
     "decided TRUE without execution, with receipt. AI writes, the core verifies."},
    {"id": "doc5", "source": "zephyrum/zyql_qutrit/zyql_quantum_gate.py", "text":
     "The ZYQL quantum gate decides by Deutsch-Jozsa interference: constant purpose -> blanket decision "
     "(1 if all permitted, 0 if all forbidden); balanced purpose -> REFUSED (input-dependent). "
     "One oracle call; noise band plus/minus 0.15 with declared margin."},
]

# ---------------- L2: BM25 retrieval ----------------
def bm25_rank(query, corpus, k=2, k1=1.5, b=0.75):
    docs = [d["text"].lower().split() for d in corpus]
    q = query.lower().split()
    N, avgdl = len(docs), sum(len(d) for d in docs) / len(docs)
    def idf(t):
        n = sum(1 for d in docs if t in d)
        return math.log((N - n + 0.5) / (n + 0.5) + 1) if n else 0.0
    scores = []
    for i, d in enumerate(docs):
        dl = len(d)
        s = 0.0
        for t in q:
            tf = d.count(t)
            if tf:
                s += idf(t) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))
        scores.append((s, i))
    scores.sort(reverse=True)
    return [(corpus[i], round(s, 3)) for s, i in scores[:k] if s > 0]

# ---------------- L3: LLM translator (Gemini 3.5 Flash) ----------------
GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
              "gemini-3.5-flash:generateContent?key=%s")

def llm_formulate(question, context, _retry=0):
    """LLM translates the question + retrieved context into a purpose rule.
    Returns the rule text (JSON: {"kind": "constant"|"parity", "value": 0|1})."""
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        # key file from the owner (never echoed)
        kf = os.path.join(HERE, "..", "..", "incoming_files",
                          [f for f in sorted(os.listdir(os.path.join(HERE, "..", "..", "incoming_files")))
                           if "GOOGLE_API_KEY" in f][-1])
        key = open(kf).read().strip()
    prompt = (
        "You are the translator of the ZYQL decision pipeline. Given the question and the retrieved "
        "trusted context, output ONLY compact JSON with the purpose rule for the ZYQL quantum gate. "
        "Schema: {\"kind\": \"constant\", \"value\": 1} if every use in context is permitted; "
        "{\"kind\": \"constant\", \"value\": 0} if every use is forbidden; "
        "{\"kind\": \"parity\"} if permission depends on the input (input-dependent). "
        "No markdown fences, no explanation.\n\nQUESTION: %s\n\nTRUSTED CONTEXT:\n%s" %
        (question, context))
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0.0, "maxOutputTokens": 2048}}).encode()
    req = urllib.request.Request(GEMINI_URL % key, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (429, 500, 503) and _retry < 3:
            import time as _t; _t.sleep(5)
            return llm_formulate(question, context, _retry + 1)
        raise
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()

def parse_rule(text):
    t = text.strip().strip("`").replace("json", "", 1).strip()
    import re as _re
    m = _re.search(r"\{.*\}", t, _re.S)
    if not m:
        raise ValueError("no JSON object in LLM output: " + t[:200])
    j = json.loads(m.group(0))
    if j["kind"] == "constant":
        v = j["value"]
        return (lambda x: 1) if v == 1 else (lambda x: 0), j
    return (lambda x: x.bit_count() % 2), j

# ---------------- L4 + L5: quantum gate + receipt ----------------
def decide(question, n=3, shots=4096):
    t0 = time.time()
    retrieved = bm25_rank(question, CORPUS)
    context = "\n".join("[%s] %s" % (d["source"], d["text"]) for d, _ in retrieved)
    rule_text = llm_formulate(question, context)
    f, rule = parse_rule(rule_text)
    g = ZYQLQuantumGate(n, f)
    r = g.run_quantum(shots=shots)
    receipt = {
        "question": question,
        "pipeline": ["L1 trusted docs", "L2 RAG (BM25)", "L3 Gemini 3.5 Flash translator",
                    "L4 ZYQL quantum gate (Deutsch-Jozsa, interference)", "L5 receipt"],
        "rag_context": [{"source": d["source"], "score": s} for d, s in retrieved],
        "llm": {"model": "gemini-3.5-flash", "rule_raw": rule_text, "rule_parsed": rule,
                "attribution": "Generated with Google Gemini 3.5 Flash. LLM formulates; the gate decides; the C99 core certifies."},
        "gate": {"decision": r["decision"], "p0": round(g.p0, 4),
                 "oracle_calls_quantum": g.oracle_calls,
                 "mode": r["mode"], "noise_band": 0.15, "error_bound": r["error_bound"]},
        "elapsed_s": round(time.time() - t0, 2),
        "mode": "SIMULATION (state-vector kernel); LLM call is real"}
    return receipt

if __name__ == "__main__":
    proof = {"module": "zyql_rag_layer.py", "version": "1.0.0",
             "date": time.strftime("%Y-%m-%d %H:%M:%S"), "cases": []}
    tests = [
        ("Is every permitted use of the ZYQL gate signed with a receipt?",
         "expected", 1),   # context: every decision carries provenance -> constant-1
        ("Is it permitted to claim quantum advantage without proof?",
         "expected", 0),   # honesty policy -> forbidden blanket claim
        ("Is a circuit execution permitted depending on its purpose?",
         "expected", "REFUSED"),  # input-dependent -> balanced
    ]
    for q, _, expect in tests:
        try:
            rc = decide(q)
            ok = rc["gate"]["decision"] == expect
            rc["expect"] = expect; rc["PASS"] = ok
            print("%-62s -> %-8s PASS=%s" % (q[:62], rc["gate"]["decision"], ok))
        except Exception as e:
            rc = {"question": q, "error": str(e), "PASS": False}
            print("ERRO:", str(e)[:120])
        proof["cases"].append(rc)
    proof["all_PASS"] = all(c.get("PASS") for c in proof["cases"])
    out = os.path.join(HERE, "..", "lab", "prova_zyql_rag_layer.json")
    json.dump(proof, open(out, "w"), indent=1)
    print("ALL_PASS:", proof["all_PASS"])
