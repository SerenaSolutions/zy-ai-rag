"""
ZEPHYRUM OS — quantum-ready operating system simulation layer.
State-vector quantum circuit simulator. This is CLASSICAL SIMULATION
of quantum circuits, executed for real. No hardware claims beyond it.
"""
import math, random
from collections import Counter

I2 = [[1, 0], [0, 1]]
H = [[1 / math.sqrt(2), 1 / math.sqrt(2)], [1 / math.sqrt(2), -1 / math.sqrt(2)]]
X = [[0, 1], [1, 0]]
Y = [[0, -1j], [1j, 0]]
Z = [[1, 0], [0, -1]]
S = [[1, 0], [0, 1j]]
T = [[1, 0], [0, math.e ** (1j * math.pi / 4)]]

class QCircuit:
    def __init__(self, nqubits):
        self.n = nqubits
        self.state = [0.0] * (2 ** nqubits)
        self.state[0] = 1.0 + 0j
        self.gates_applied = []

    def _single(self, U, q):
        dim = 2 ** self.n
        mask = 1 << q
        new = list(self.state)
        for i in range(dim):
            if i & mask == 0:
                j = i | mask
                a, b = self.state[i], self.state[j]
                new[i] = U[0][0] * a + U[0][1] * b
                new[j] = U[1][0] * a + U[1][1] * b
        self.state = new

    def h(self, q):        self._single(H, q); self.gates_applied.append(f"H({q})")
    def x(self, q):        self._single(X, q); self.gates_applied.append(f"X({q})")
    def y(self, q):        self._single(Y, q); self.gates_applied.append(f"Y({q})")
    def z_(self, q):       self._single(Z, q); self.gates_applied.append(f"Z({q})")
    def s(self, q):        self._single(S, q); self.gates_applied.append(f"S({q})")
    def t(self, q):        self._single(T, q); self.gates_applied.append(f"T({q})")

    def cnot(self, c, t):
        cmask, tmask = 1 << c, 1 << t
        for i in range(2 ** self.n):
            if (i & cmask) and not (i & tmask):
                j = i ^ (1 << t)
                self.state[i], self.state[j] = self.state[j], self.state[i]
        self.gates_applied.append(f"CNOT({c}->{t})")

    def cz(self, c, t):
        cmask = 1 << c
        for i in range(2 ** self.n):
            if (i & cmask) and (i & (1 << t)):
                self.state[i] = -self.state[i]
        self.gates_applied.append(f"CZ({c},{t})")

    def measure_all(self, shots=1024, seed=None):
        rng = random.Random(seed)
        probs = [abs(a) ** 2 for a in self.state]
        total = sum(probs)
        norm = [p / total for p in probs]
        results = ["|{:0{}b}>".format(rng.choices(range(2 ** self.n), weights=norm)[0], self.n)
                   for _ in range(shots)]
        return dict(sorted(Counter(results).items()))

    def probabilities(self):
        return {"|{:0{}b}>".format(i, self.n): round(abs(a) ** 2, 4)
                for i, a in enumerate(self.state) if abs(a) ** 2 > 1e-9}

    # --- extended gate set (2026-10-09) ---
    def rx(self, q, theta):
        c, s2 = math.cos(theta / 2), math.sin(theta / 2)
        self._single([[c, -1j * s2], [-1j * s2, c]], q)
        self.gates_applied.append(f"RX({q},{theta})")

    def ry(self, q, theta):
        c, s2 = math.cos(theta / 2), math.sin(theta / 2)
        self._single([[c, -s2], [s2, c]], q)
        self.gates_applied.append(f"RY({q},{theta})")

    def rz(self, q, theta):
        e = math.e ** (-1j * theta / 2)
        self._single([[e, 0], [0, 1 / e]], q)
        self.gates_applied.append(f"RZ({q},{theta})")

    def swap(self, a, b):
        self.cnot(a, b); self.cnot(b, a); self.cnot(a, b)
        self.gates_applied.append(f"SWAP({a},{b})")

    def toffoli(self, c1, c2, t):
        m1, m2 = 1 << c1, 1 << c2
        for i in range(2 ** self.n):
            if (i & m1) and (i & m2) and not (i & (1 << t)):
                j = i ^ (1 << t)
                self.state[i], self.state[j] = self.state[j], self.state[i]
        self.gates_applied.append(f"TOFFOLI({c1},{c2}->{t})")

    # --- Zephyron circuit loader (parses gate strings) ---
    @classmethod
    def from_gates(cls, n, gates):
        qc = cls(n)
        for g in gates:
            qc.apply(g)
        return qc

    def apply(self, g):
        name, rest = g.split("(", 1)
        args = [a for a in rest.rstrip(")").replace(" ", "").split(",") if a != ""]
        if "->" in args[0] if args else False:
            pass
        if name == "H": self.h(int(args[0]))
        elif name == "X": self.x(int(args[0]))
        elif name == "Y": self.y(int(args[0]))
        elif name == "Z": self.z_(int(args[0]))
        elif name == "S": self.s(int(args[0]))
        elif name == "T": self.t(int(args[0]))
        elif name == "RX": self.rx(int(args[0]), float(args[1]))
        elif name == "RY": self.ry(int(args[0]), float(args[1]))
        elif name == "RZ": self.rz(int(args[0]), float(args[1]))
        elif name == "SWAP": self.swap(int(args[0]), int(args[1]))
        elif name == "CNOT":
            c, t = args[0].split("->"); self.cnot(int(c), int(t))
        elif name == "CZ": self.cz(int(args[0]), int(args[1]))
        elif name == "TOFFOLI":
            ctr, t = args[0].split("->"); c1, c2 = ctr.split(","); self.toffoli(int(c1), int(c2), int(t))
        else:
            raise ValueError(f"unknown Zephyron gate: {g}")

    # --- noisy sampling (Monte Carlo, shot-by-shot) ---
    def measure_noisy(self, shots=1024, p2=0.01, p1=0.001, readout=0.02, seed=None):
        """Per-shot Monte Carlo with depolarizing-style Pauli errors after
        each gate and readout bit flips. p2 = error prob after 2-qubit
        gates, p1 = after 1-qubit gates. Honest hardware-like results."""
        rng = random.Random(seed)
        PAULIS = [X, Y, Z]
        out = []
        for _ in range(shots):
            qc = QCircuit(self.n)
            for g in self.gates_applied:
                qc.apply(g)
                p = p2 if ("->" in g or "," in g) else p1
                if rng.random() < p:
                    q = rng.randrange(self.n)
                    qc._single(rng.choice(PAULIS), q)
            # sample from this noisy state
            probs = [abs(a) ** 2 for a in qc.state]
            idx = rng.choices(range(2 ** self.n), weights=probs)[0]
            # readout error: flip each bit with prob `readout`
            for b in range(self.n):
                if rng.random() < readout:
                    idx ^= 1 << b
            out.append("|{:0{}b}>".format(idx, self.n))
        return dict(sorted(Counter(out).items()))
