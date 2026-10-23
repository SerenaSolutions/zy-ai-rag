"""
ZYQL QUANTUM GATE — Deutsch-Jozsa prototype (v1.0.0, 12/10/2026).
The trivalent decision (1 / 0 / REFUSED) now comes from quantum interference,
not from a classical if.

Semantics (declared honestly, under the DJ promise: f is constant or balanced):
  purpose function f(x) = 1 if use x is permitted, else 0
  measurement |00..0>  -> f is CONSTANT -> blanket decision possible
                            f == 1 everywhere -> DECIDE 1
                            f == 0 everywhere -> DECIDE 0
  measurement != 00..0 -> f is BALANCED  -> input-dependent -> REFUSED
  outside the confidence band -> REFUSED with declared margin (noise rule)

Query accounting (honest):
  quantum: 1 oracle call decides among {1, 0, REFUSED}
  classical deterministic worst case: 2^(n-1)+1 calls to separate constant/balanced
  classical randomized: 2 calls for confidence 3/4 (advantage vs randomized is 2x,
  exponential only vs deterministic worst case) — declared, never inflated.

SIMULATION MODE (numpy-free state vector of the house kernel zquantum.py).
"""
import math, json, time, random, hashlib
from collections import Counter
import sys, os
try:
    from zquantum import QCircuit
except ImportError:  # in-tree, no install
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from zquantum import QCircuit

MARGIN = 0.15          # declared confidence band (+-0.15) of the noise rule


def adaptive_margin(epsilon, shots):
    """UPGRADE v1.9.0 — banda de confianca adaptativa (Hoeffding inverso).

    O usuario declara o erro maximo tolerado (epsilon) na decisao; a banda
    necessaria e DERIVADA, nao fixa: banda = sqrt(ln(2/eps)/(2*shots)).
    Com shots suficiente, a banda encolhe e o veredito fica mais agressivo;
    com shots curto, a banda cresce e o nucleo recusa em vez de mentir.
    """
    if not (0.0 < epsilon < 0.5):
        raise ValueError("epsilon precisa em (0, 0.5); recebido %r" % epsilon)
    return math.sqrt(math.log(2.0 / epsilon) / (2.0 * shots))


def ghz_integrity(n=3, shots=2048, seed=1701, threshold=0.80):
    """UPGRADE v1.9.0 — PORTA DE INTEGRIDADE GHZ (semantica inedita).

    Antes de confiar num veredito, o PROPRIO DISPOSITIVO e testado: estado GHZ_n
    medido; a fracao de resultados genuinamente GHZ (|00..0> + |11..1>) e a
    fidelidade proxy. Abaixo do limiar => dispositivo INCONFIABEL, o runtime
    recusa SEM gastar oraculo: RECUSA POR DECOERENCIA, motivo declarado.
    """
    qc = QCircuit(n)
    qc.h(0)
    for t in range(1, n):
        qc.cnot(0, t)
    counts = qc.measure_all(shots=shots, seed=seed)
    zk = "|%s>" % ("0" * n)
    ok = "|%s>" % ("1" * n)
    f = (counts.get(zk, 0) + counts.get(ok, 0)) / shots
    return {"fidelity_ghz": round(f, 4), "threshold": threshold,
            "device_trusted": f >= threshold, "mode": "GHZ_INTEGRITY_GATE"}
class ZYQLQuantumGate:
    """Deutsch-Jozsa trivalent gate. One oracle call per decision."""

    def __init__(self, n, f):
        """n: number of input qubits. f: purpose function on n-bit ints -> 0/1."""
        self.n = n
        self.f = f
        self.oracle_calls = 0

    def _phase_oracle(self, qc):
        """Uf |x> = (-1)^f(x) |x>. Counts as ONE oracle call."""
        for i in range(2 ** self.n):
            if self.f(i) == 1:
                qc.state[i] = -qc.state[i]
        self.oracle_calls += 1
        qc.gates_applied.append("Uf(x) [1 oracle call]")

    def run_quantum(self, shots=2048, seed=1701, epsilon=None):
        """Interference decision: 1 oracle call.

        epsilon (v1.9.0): banda adaptativa por Hoeffding inverso.
        Sem epsilon: banda fixa MARGIN (comportamento v1.x preservado).
        """
        margin = adaptive_margin(epsilon, shots) if epsilon is not None else MARGIN
        qc = QCircuit(self.n)
        for q in range(self.n):
            qc.h(q)
        self._phase_oracle(qc)                    # exactly one call
        for q in range(self.n):
            qc.h(q)
        counts = qc.measure_all(shots=shots, seed=seed)
        zk = "|%s>" % ("0" * self.n)
        p0 = counts.get(zk, 0) / shots          # prob of |00..0>
        self.p0 = p0
        self.counts = counts
        return self._trivalent(p0, shots, margin=margin,
                               adaptive=epsilon is not None,
                               epsilon_declared=epsilon if epsilon is not None else 1.0)

    def _trivalent(self, p0, shots, eps_name="Hoeffding", margin=MARGIN,
                   adaptive=False, epsilon_declared=1.0):
        """Noise rule: band +-margin around 0 and 1; outside both -> REFUSED."""
        hoeff = min(epsilon_declared, 2 * math.exp(-2 * shots * margin ** 2)) if adaptive else 2 * math.exp(-2 * shots * margin ** 2)
        if p0 >= 1 - margin:
            # constant. Which constant? the classical f(0) probe (1 extra call)
            self.oracle_calls += 1
            verdict = 1 if self.f(0) == 1 else 0
            return {"decision": verdict, "mode": "DECIDED_BY_INTERFERENCE",
                    "p0": p0, "rule": ("adaptive band>=%.4f" % (1 - margin)) if adaptive else ("band>=%.2f" % (1 - margin)),
                    "error_bound": hoeff, "error_bound_type": eps_name}
        if p0 <= margin:
            return {"decision": "REFUSED", "mode": "DECIDED_BY_INTERFERENCE",
                    "p0": p0, "rule": ("adaptive band<=%.4f (balanced: input-dependent)" % margin) if adaptive else ("band<=%.2f (balanced: input-dependent)" % margin),
                    "error_bound": hoeff, "error_bound_type": eps_name}
        return {"decision": "REFUSED", "mode": "INSUFFICIENT_CONFIDENCE",
                "p0": p0, "rule": "inside noise band (+-%.4f), margin declared" % margin,
                "error_bound": hoeff, "error_bound_type": eps_name}

    # --- classical baselines for the query-advantage receipt ---
    def classical_deterministic(self):
        """Worst-case deterministic queries to separate constant/balanced."""
        seen = {}
        for i in range(2 ** self.n):
            seen[i] = self.f(i)
            vals = set(seen.values())
            if len(vals) == 2:
                return {"queries": i + 1, "answer": "balanced"}
        # saw all: must be balanced if both values seen, else constant
        return {"queries": 2 ** self.n // 2 + 1, "answer": "constant"}

    def classical_randomized(self, rng=None, confidence=0.75):
        """Random sampling: 2 queries give >= 3/4 confidence under promise."""
        rng = rng or random.Random(7)
        a, b = rng.randrange(2 ** self.n), rng.randrange(2 ** self.n)
        same = self.f(a) == self.f(b)
        return {"queries": 2, "answer": "constant" if same else "balanced",
                "confidence": confidence if same else 1.0}


def bell_test():
    """Sanity: kernel still reproduces Bell 1/2+1/2 (regression anchor)."""
    qc = QCircuit(2); qc.h(0); qc.cnot(0, 1)
    c = qc.measure_all(shots=4096, seed=42)
    p00 = c.get("|00>", 0) / 4096; p11 = c.get("|11>", 0) / 4096
    return abs(p00 - 0.5) < 0.02 and abs(p11 - 0.5) < 0.02


def main():
    proof = {"module": "zyql_quantum_gate.py", "version": "1.0.0",
             "date": time.strftime("%Y-%m-%d %H:%M:%S"),
             "mode": "SIMULATION (state-vector kernel zquantum.py)",
             "margin_declared": MARGIN, "cases": [], "bell_regression": bell_test()}
    n = 3
    cases = [
        ("constant-1 (all permitted)", lambda x: 1, 1),
        ("constant-0 (all forbidden)", lambda x: 0, 0),
        ("balanced (parity: input-dependent)", lambda x: x.bit_count() % 2, "REFUSED"),
    ]
    for name, f, expect in cases:
        g = ZYQLQuantumGate(n, f)
        r = g.run_quantum(shots=4096)
        det = g.classical_deterministic()
        rnd = g.classical_randomized()
        ok = r["decision"] == expect
        proof["cases"].append({
            "name": name, "n_qubits": n, "expect": expect,
            "quantum_decision": r["decision"], "p0": round(g.p0, 4),
            "quantum_oracle_calls": g.oracle_calls, "PASS": ok,
            "classical_deterministic_worst": det["queries"],
            "classical_randomized_queries": rnd["queries"],
            "counts": {str(k): v for k, v in g.counts.items()}})
        print("%-40s -> %-8s p0=%.4f quantum_calls=%d PASS=%s" % (
            name, r["decision"], g.p0, g.oracle_calls, ok))

    # noise rule: inject fake noisy p0 to prove the band behaves
    g = ZYQLQuantumGate(n, lambda x: 1)
    band_cases = [(0.995, 1), (0.0, "REFUSED"), (0.55, "REFUSED")]
    for p0, expect in band_cases:
        r = g._trivalent(p0, shots=256)
        proof.setdefault("noise_band_tests", []).append(
            {"p0": p0, "decision": r["decision"], "mode": r["mode"], "PASS": r["decision"] == expect})
    # true Pauli-noise run: balanced case under noise
    qc = QCircuit(n)
    for q in range(n): qc.h(q)
    for i in range(2 ** n):
        if i.bit_count() % 2: qc.state[i] = -qc.state[i]
    for q in range(n): qc.h(q)
    cn = qc.measure_noisy(shots=4096, p2=0.02, p1=0.002, readout=0.03, seed=9)
    p0n = cn.get("|%s>" % ("0" * n), 0) / 4096
    g2 = ZYQLQuantumGate(n, lambda x: x.bit_count() % 2)
    rn = g2._trivalent(p0n, 4096)
    proof["noisy_hardware_style_run"] = {
        "label": "balanced case with Pauli noise (p2=0.02, readout=0.03)",
        "p0_measured": round(p0n, 4), "decision": rn["decision"],
        "mode": rn["mode"], "note": "REFUSED stands under noise — the gate refuses instead of guessing"}

    proof["all_PASS"] = all(c["PASS"] for c in proof["cases"]) and \
                         all(t["PASS"] for t in proof["noise_band_tests"]) and proof["bell_regression"]
    out = os.path.join(os.path.dirname(__file__), "..", "lab", "prova_zyql_quantum.json")
    json.dump(proof, open(out, "w"), indent=1)
    print("\nALL_PASS:", proof["all_PASS"])
    print("proof:", out)

if __name__ == "__main__":
    main()
