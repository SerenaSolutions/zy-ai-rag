# ZY-AI-RAG

![zyql](https://img.shields.io/badge/decision-trivalent%201%2F0%2FREFUSED-green) ![license](https://img.shields.io/badge/license-Apache--2.0-blue)

**Trivalent AI decision for CI.** BM25 retrieval over your trusted docs, an optional LLM translator (Gemini, via the `GOOGLE_API_KEY` secret), and the ZYQL quantum-gate verdict — **1 / 0 / REFUSED** — sealed in a Z-QEA SHA3-256 receipt with citations. *Nothing decides silently.*

## Use it

```yaml
- name: Trivalent AI decision
  id: rag
  uses: SerenaSolutions/zy-ai-rag@v1.1.0
  with:
    question: "Is every permitted use covered by a receipt?"
    rule: '{"kind":"constant","value":1}'
- run: echo "decision ${{ steps.rag.outputs.decision }} · seal ${{ steps.rag.outputs.seal }}"
```

| input | required | meaning |
|-------|----------|---------|
| `question` | yes | the question the pipeline must answer trivalently |
| `rule` | no | OFFLINE mode: purpose rule as JSON (`{"kind":"constant","value":1}` or `{"kind":"parity"}`) |
| `corpus` | no | corpus JSON file for BM25 retrieval (default: house corpus) |
| `shots` | no (`4096`) | shots for the statevector gate battery |

Outputs: `decision` (`1` / `0` / `REFUSED`) and `seal` (SHA3-256 seal of the receipt).

## Two declared modes

The receipt always records which one ran, so a decision can never be read out of context.

| mode | when | what happens |
|------|------|--------------|
| **LLM** | `GOOGLE_API_KEY` is set | the translator formulates the purpose rule from the retrieved context (`gemini-3.5-flash`) |
| **OFFLINE** | no key, `rule` given | the rule comes from your explicit input; no LLM call happens, nothing leaves the runner |

## What runs where

- **Retrieval** — BM25 over the corpus you provide, locally. Citations (`source` + `score`) go into the receipt.
- **Translator** — optional, only in LLM mode; retrieved context is sent to the model provider in that mode.
- **Gate** — the declared local statevector kernel of ZYQL v1.9.0 (**SIMULATION**, stated inside the receipt, no hardware involved).
- **Receipt** — Z-QEA with SHA3-256 seal and the seal rule written into the receipt itself, so it can be re-derived.

## Exit codes

| code | meaning |
|------|---------|
| `0` | decision reached and sealed; `decision` and `seal` are exported as outputs |
| `2` | usage error (no `rule` in OFFLINE mode, malformed input) |
| `3` | device integrity gate failed: `REFUSED_DEVICE_DECOHERED`, oracle not spent |

## Scope and honest limits

- **The gate is a simulation**, and the receipt says so in the `kernel` field. Hardware evidence in this repository is the separate proof of concept below.
- **Seal is integrity, not authorship.** SHA3-256 proves the receipt was not edited; it does not prove who issued it. Receipts here are not yet signed with ML-DSA-44, so a third party can regenerate the same seal from the same content.
- **Retrieval is lexical.** BM25 ranks documents by term overlap. It is not an embedding search and makes no semantic claim.
- **LLM mode has a data flow.** The retrieved context is sent to the model provider. OFFLINE mode is the zero-egress path.
- **`REFUSED` is a result, not an error.** It means the shots did not separate the hypotheses well enough to justify a claim.

Free forever. Apache-2.0 (see [LICENSE](LICENSE)). ZEPHIRUM product line: [zqea-verify](https://github.com/marketplace/actions/z-qea-receipt-verifier), [z-anyon-lab](https://github.com/SerenaSolutions/z-anyon-lab), [zq-gate](https://github.com/SerenaSolutions/zq-gate), [zqea-seal](https://github.com/SerenaSolutions/zqea-seal).

## Proof of concept (real hardware)

Trivalent ZYQL gate with BM25 retrieval: weak query → `REFUSED`, strong query → `1`, decisions read from real hardware (job identifiers kept in internal evidence).

Sealed receipt: [`poc/receipt_zyai_hw.json`](poc/receipt_zyai_hw.json), re-verifiable without trusting this repository:

```console
$ python3 zqea_verify.py poc/receipt_zyai_hw.json --strict-pq
selo declarado    : 3a0b00a972fbba8aabac8f78819e001d2d3c1e08358a090456413504c2fafed9
selo recalculado  : 3a0b00a972fbba8aabac8f78819e001d2d3c1e08358a090456413504c2fafed9
Z-QEA: SELO ÍNTEGRO
```

Full multilingual confrontation battery (OpenQASM 3, Qiskit, Cirq, PennyLane, Braket, Q#): [SerenaSolutions/quantum-poc](https://github.com/SerenaSolutions/quantum-poc).

## Changelog

### v1.1.0 (2026-10-23)
- Kernel ZYQL v1.9.0: `--epsilon` (adaptive Hoeffding margin, error declared in the receipt) and `--require-trust` (GHZ integrity gate: untrusted device → `REFUSED` without spending the oracle, mode `REFUSED_DEVICE_DECOHERED`).
