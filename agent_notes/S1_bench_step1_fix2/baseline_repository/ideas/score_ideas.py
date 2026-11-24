"""Recomputes the Total column of IDEA_BANK.md from N, F, P, E, O and rewrites the ranking line."""
import re
from pathlib import Path

W = {"N": 0.30, "F": 0.25, "P": 0.25, "E": 0.10, "O": 0.10}
path = Path(__file__).with_name("IDEA_BANK.md")
lines = path.read_text(encoding="utf-8").splitlines()
row = re.compile(r"^\| (\d+) \| (.+?) \| (.+?) \| (\d) \| (\d) \| (\d) \| (\d) \| (\d) \| [\d.]+ \|$")
scores = {}
out = []
for ln in lines:
    m = row.match(ln)
    if m:
        n, f, p, e, o = map(int, m.groups()[3:8])
        total = W["N"] * n + W["F"] * f + W["P"] * p + W["E"] * e + W["O"] * o
        scores[int(m.group(1))] = (round(total, 2), m.group(2))
        ln = f"| {m.group(1)} | {m.group(2)} | {m.group(3)} | {n} | {f} | {p} | {e} | {o} | {total:.2f} |"
    out.append(ln)
ranked = sorted(scores.items(), key=lambda kv: -kv[1][0])
top = ", ".join(f"{i} ({s:.2f})" for i, (s, _) in ranked[:12])
text = "\n".join(out)
text = re.sub(r"(## Top of the ranking \(before merging\)\n).*?\n", rf"\g<1>{top}.\n", text, flags=re.S)
path.write_text(text + "\n", encoding="utf-8")
print(f"{len(scores)} ideas scored")
for i, (s, t) in ranked[:12]:
    print(f"{i:>3} {s:.2f} {t}")
