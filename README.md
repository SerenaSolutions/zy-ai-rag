# ZY-AI-RAG

![zyql](https://img.shields.io/badge/decision-trivalent%201%2F0%2FREFUSED-green) ![license](https://img.shields.io/badge/license-MIT-blue)

**Trivalent AI decision for CI.** BM25 retrieval over your trusted docs, an optional LLM translator (Gemini, via `GOOGLE_API_KEY` secret), and the ZYQL quantum-gate verdict — **1 / 0 / REFUSED** — sealed with a Z-QEA SHA3-256 receipt with citations. *Nothing decides silently.*

Two declared modes (the receipt always records which ran):
- **LLM** — with `GOOGLE_API_KEY`: the translator formulates the purpose rule from retrieved context
- **OFFLINE** — without a key: you pass the rule explicitly (`{"kind":"constant","value":1}` / `{"kind":"parity"}`); no LLM call happens

```yaml
- name: Trivalent AI decision
  uses: SerenaSolutions/zy-ai-rag@v1
  with:
    question: "Is every permitted use covered by a receipt?"
    rule: '{"kind":"constant","value":1}'
```

The gate itself runs on the declared local statevector kernel (SIMULATION, honestly labeled) — the receipt says so.

Free forever, MIT. ZEPHIRUM product line: [zqea-verify](https://github.com/marketplace/actions/z-qea-receipt-verifier), [z-anyon-lab](https://github.com/SerenaSolutions/z-anyon-lab), [zq-gate](https://github.com/SerenaSolutions/zq-gate), [zqea-seal](https://github.com/SerenaSolutions/zqea-seal).

## Prova de conceito (hardware real)

Porta ZYQL trivalente com recuperação BM25: consulta fraca → RECUSADO, forte → 1 — decisões lidas do hardware real (job `dbcnp4s24mrc73ck0v80`).

Recibo selado: [`poc/receipt_zyai_hw.json`](poc/receipt_zyai_hw.json) — verificável com `python3 zqea_verify.py poc/receipt_zyai_hw.json --strict-pq`.

Bateria completa do confronto multilíngue (OpenQASM 3, Qiskit, Cirq, PennyLane, Braket, Q#): [SerenaSolutions/quantum-poc](https://github.com/SerenaSolutions/quantum-poc).
