"""Independent finite-matrix checks of the manuscript equations, not a CP2K run."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import expm, expm_frechet
from scipy.optimize import brentq
from scipy.special import expit, xlogy

ROOT = Path(__file__).resolve().parent
FIGURES = ROOT / "figures"
FIGURES.mkdir(exist_ok=True)
rng = np.random.default_rng(271828)


def hermitian(n):
    z = rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))
    z = 0.5 * (z + z.conj().T)
    return z / np.linalg.norm(z)


def occupations(energies, weights, number, temperature):
    def count(mu):
        return np.dot(weights, expit((mu - energies) / temperature)) - number
    lo, hi = energies.min() - 10, energies.max() + 10
    mu = brentq(count, lo, hi, xtol=1e-14)
    return expit((mu - energies) / temperature), mu


def scalar_free_energy(rayleigh, energy, weight, number, temperature):
    f, _ = occupations(energy, weight, number, temperature)
    entropy_term = xlogy(f, f) + xlogy(1 - f, 1 - f)
    return np.dot(weight, f * rayleigh + temperature * entropy_term)


weights = np.repeat([0.35, 0.65], 3)
energies = np.array([-0.4, 0.12, 0.12, -0.2, 0.2, 0.65])
temperature, number = 0.09, 1.4
f, mu = occupations(energies, weights, number, temperature)
chi = weights * f * (1 - f) / temperature
q = np.diag(chi) - np.outer(chi, chi) / chi.sum()
rayleigh = energies + 0.08 * rng.normal(size=6)
direction = rng.normal(size=6)
direction /= np.linalg.norm(direction)
gradient = -q @ (rayleigh - energies)

unitaries, hamiltonians, perturbations = [], [], []
for spectrum in energies.reshape(2, 3):
    z = rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3))
    u, _ = np.linalg.qr(z)
    unitaries.append(u)
    hamiltonians.append((u * spectrum) @ u.conj().T)
    perturbations.append(hermitian(3))


def projectors(hs):
    eigensystems = [np.linalg.eigh(h) for h in hs]
    e = np.concatenate([x[0] for x in eigensystems])
    fs, _ = occupations(e, weights, number, temperature)
    return [w * (u * occ) @ u.conj().T for w, (_, u), occ in
            zip([0.35, 0.65], eigensystems, fs.reshape(2, 3))]


def projector_derivative(hs, dhs):
    eigensystems = [np.linalg.eigh(h) for h in hs]
    es = np.concatenate([x[0] for x in eigensystems])
    fs, _ = occupations(es, weights, number, temperature)
    cs = weights * fs * (1 - fs) / temperature
    es, fs, cs = es.reshape(2, 3), fs.reshape(2, 3), cs.reshape(2, 3)
    ds = [u.conj().T @ dh @ u for (_, u), dh in zip(eigensystems, dhs)]
    dmu = sum(np.dot(c, d.diagonal().real) for c, d in zip(cs, ds)) / cs.sum()
    result = []
    for w, e, occ, c, (_, u), d in zip([0.35, 0.65], es, fs, cs, eigensystems, ds):
        z = np.zeros((3, 3), dtype=complex)
        for i in range(3):
            for j in range(3):
                if i == j:
                    z[i, i] = -c[i] * (d[i, i].real - dmu)
                else:
                    coeff = w * (occ[i] - occ[j]) / (e[i] - e[j]) if abs(e[i] - e[j]) > 1e-10 else -0.5 * (c[i] + c[j])
                    z[i, j] = coeff * d[i, j]
        result.append(u @ z @ u.conj().T)
    return result


dp = projector_derivative(hamiltonians, perturbations)
a = 0.55j * hermitian(3)
da = 1j * hermitian(3)
b = hermitian(3)
occ_rotation = np.array([0.94, 0.57, 0.08])
u, du = expm_frechet(a, da)
rotation_derivative = 2 * np.trace(np.diag(occ_rotation) @ u.conj().T @ b @ du).real


def rotation_energy(generator):
    ur = expm(generator)
    return np.trace(np.diag(occ_rotation) @ ur.conj().T @ b @ ur).real


steps = np.logspace(-2, -8, 13)
rows = []
for h in steps:
    gf = (scalar_free_energy(rayleigh, energies + h * direction, weights, number, temperature)
          - scalar_free_energy(rayleigh, energies - h * direction, weights, number, temperature)) / (2 * h)
    pp = projectors([x + h * dx for x, dx in zip(hamiltonians, perturbations)])
    pm = projectors([x - h * dx for x, dx in zip(hamiltonians, perturbations)])
    pe = max(np.linalg.norm((p - m) / (2 * h) - d) for p, m, d in zip(pp, pm, dp))
    rf = (rotation_energy(a + h * da) - rotation_energy(a - h * da)) / (2 * h)
    rows.append([float(h), float(abs(gf - gradient @ direction)), float(pe), float(abs(rf - rotation_derivative))])

# A pure basis rotation must cancel the induced spectral-projector motion.
ks = [1j * hermitian(3), 1j * hermitian(3)]
gauge_dh = [h @ k - k @ h for h, k in zip(hamiltonians, ks)]
gauge_dp = projector_derivative(hamiltonians, gauge_dh)
ps = projectors(hamiltonians)
gauge_error = max(np.linalg.norm(k @ p - p @ k + dp0) for k, p, dp0 in zip(ks, ps, gauge_dp))

# Frozen-H coupled Hessian at the canonical auxiliary-energy point.
basis = []
for i in range(3):
    for j in range(i + 1, 3):
        er = np.zeros((3, 3), dtype=complex)
        ei = np.zeros((3, 3), dtype=complex)
        er[i, j], er[j, i] = 1, -1
        ei[i, j], ei[j, i] = 1j, 1j
        basis.extend([er, ei])

eps0 = np.diag(u.conj().T @ b @ u).real
fc, _ = occupations(eps0, np.ones(3), 1.3, temperature)
cc = fc * (1 - fc) / temperature
qc = np.diag(cc) - np.outer(cc, cc) / cc.sum()


def rotation_gradient(generator, occ):
    ur = expm(generator)
    return np.array([2 * np.trace(np.diag(occ) @ ur.conj().T @ b @ expm_frechet(generator, e, compute_expm=False)).real for e in basis])


dh = 1e-4
ar = np.column_stack([(rotation_gradient(a + dh * e, fc) - rotation_gradient(a - dh * e, fc)) / (2 * dh) for e in basis])
ar = 0.5 * (ar + ar.T)
rr = np.column_stack([np.diag(expm_frechet(a, e, compute_expm=False).conj().T @ b @ u + u.conj().T @ b @ expm_frechet(a, e, compute_expm=False)).real for e in basis])
full = np.block([[ar, -rr.T @ qc], [-qc @ rr, qc]])
dtheta = rng.normal(size=6)
deps = rng.normal(size=3)
v = np.concatenate([dtheta, deps])
v /= np.linalg.norm(v)
dgen = sum((x * e for x, e in zip(v[:6], basis)), start=np.zeros((3, 3), dtype=complex))


def combined(alpha):
    ur = expm(a + alpha * dgen)
    hs = np.diag(ur.conj().T @ b @ ur).real
    return scalar_free_energy(hs, eps0 + alpha * v[6:], np.ones(3), 1.3, temperature)


hh = 2e-4
curvature_fd = (combined(hh) - 2 * combined(0) + combined(-hh)) / hh**2
schur = ar - rr.T @ qc @ rr
curvature_error = abs(curvature_fd - v @ full @ v)
summary = {
    "experiment": "Independent NumPy/SciPy matrix check; not CP2K timings or electronic-structure results",
    "seed": 271828,
    "temperature_energy_units": temperature,
    "weights": [0.35, 0.65],
    "target_electrons": number,
    "spectra": energies.reshape(2, 3).tolist(),
    "number_error": float(abs(weights @ f - number)),
    "constant_energy_gauge_error": float(np.linalg.norm(q @ np.ones(6))),
    "projector_trace_response_error": float(abs(sum(np.trace(x).real for x in dp))),
    "basis_gauge_cancellation_error": float(gauge_error),
    "coupled_curvature_error": float(curvature_error),
    "schur_symmetry_error": float(np.linalg.norm(schur - schur.T)),
    "columns": ["step", "auxiliary_gradient_absolute_error", "projector_Frobenius_error", "finite_rotation_gradient_absolute_error"],
    "finite_difference_scan": rows,
}
assert summary["constant_energy_gauge_error"] < 1e-12
assert summary["projector_trace_response_error"] < 1e-12
assert gauge_error < 1e-12
assert curvature_error < 2e-6
assert min(r[1] for r in rows) < 2e-8
assert min(r[2] for r in rows) < 2e-7
assert min(r[3] for r in rows) < 2e-8
(ROOT / "derivative-results.json").write_text(json.dumps(summary, indent=2) + "\n")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "pdf.fonttype": 42, "ps.fonttype": 42})
array = np.asarray(rows)
fig, ax = plt.subplots(figsize=(6.6, 3.5), constrained_layout=True)
for col, label, color, marker in [(1, "Auxiliary-energy gradient", "#2166ac", "o"),
                                 (2, "Fixed-N spectral projector", "#21845b", "s"),
                                 (3, "Finite rotation gradient", "#b13f54", "^")]:
    ax.loglog(array[:, 0], array[:, col], marker=marker, color=color, label=label, lw=1.5, ms=4)
ax.set(xlabel="Central-difference step", ylabel="Absolute derivative error")
ax.legend(frameon=False, fontsize=8)
ax.grid(which="major", alpha=0.2)
fig.savefig(FIGURES / "derivative-checks.pdf")
fig.savefig(FIGURES / "derivative-checks.png", dpi=180)
plt.close(fig)

data = json.loads((ROOT / "recorded-results.json").read_text())
fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.4), constrained_layout=True)
for ax, key, left, right, labels, title in [
    (axs[0], "al_cg_response", "baseline_steps", "response_steps", ["Kinetic", "S inverse", "Single inverse", "Full all"], "(a) Calibrated response, Al at 600 K"),
    (axs[1], "direct_hxc_kernel", "secant_steps", "kernel_steps", ["Al 600 K", "Al 3000 K", "Fe UKS", "Cu"], "(b) Direct Hxc kernel")]:
    block = data[key]
    y = np.arange(len(labels))
    ax.barh(y - 0.17, block[left], height=0.32, color="#69757a", label="Baseline")
    ax.barh(y + 0.17, block[right], height=0.32, color="#21845b", label="Response")
    for shift, name in [(-0.17, left), (0.17, right)]:
        for pos, value in zip(y + shift, block[name]):
            ax.text(value + 2, pos, str(value), va="center", fontsize=8)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, max(block[left]) * 1.2)
    ax.set_xlabel("OT iterations")
    ax.set_title(title, fontsize=9, loc="left")
    ax.xaxis.grid(True, alpha=0.2)
    ax.set_axisbelow(True)
axs[0].legend(frameon=False, fontsize=8, loc="upper right")
fig.savefig(FIGURES / "recorded-convergence.pdf")
fig.savefig(FIGURES / "recorded-convergence.png", dpi=180)
plt.close(fig)
print(json.dumps({k: v for k, v in summary.items() if k != "finite_difference_scan"}, indent=2))

# Text-only figures keep the Overleaf source self-contained and use the same data.
plot = [r"\begin{tikzpicture}",
        r"\begin{loglogaxis}[width=0.92\linewidth,height=7cm,",
        r"xlabel={Central-difference step},ylabel={Absolute derivative error},",
        r"grid=major,grid style={black!12},tick label style={font=\small},",
        r"legend style={font=\footnotesize,draw=none,at={(0.03,0.97)},anchor=north west}]",
        ]
for col, label, color, marker in [
    (1, "Auxiliary-energy gradient", "blue!65!black", "*"),
    (2, "Fixed-$N$ spectral projector", "green!45!black", "square*"),
    (3, "Finite rotation gradient", "red!65!black", "triangle*")
]:
    coords = " ".join(f"({r[0]:.16g},{r[col]:.16g})" for r in rows)
    plot += [rf"\addplot+[color={color},mark={marker},mark size=1.6pt,thick] coordinates {{{coords}}};",
             rf"\addlegendentry{{{label}}}"]
plot += [r"\end{loglogaxis}", r"\end{tikzpicture}"]
(ROOT / "derivative-plot.tex").write_text("\n".join(plot) + "\n")

plot = [r"\begin{tikzpicture}",
        r"\begin{groupplot}[group style={group size=1 by 2,vertical sep=2.2cm},",
        r"width=0.82\linewidth,height=5cm,xbar,/pgf/bar width=5pt,",
        r"xmin=0,ymin=-0.65,ymax=3.65,ytick={0,1,2,3},y dir=reverse,",
        r"xlabel={OT iterations},xmajorgrids,grid style={black!12},",
        r"tick label style={font=\footnotesize},title style={font=\small},",
        r"nodes near coords,nodes near coords style={font=\scriptsize,text=black},",
        r"point meta=x,every node near coord/.append style={/pgf/number format/precision=0},",
        r"legend style={font=\scriptsize,draw=none,at={(1,1)},anchor=north east}]"
        ]
for key, left, right, labels, title, xmax in [
    ("al_cg_response", "baseline_steps", "response_steps",
     "Kinetic,$S$ inverse,Single inverse,Full all", "(a) Al, 600 K", 250),
    ("direct_hxc_kernel", "secant_steps", "kernel_steps",
     "Al 600 K,Al 3000 K,Fe UKS,Cu", "(b) Direct Hxc kernel", 155)
]:
    plot.append(rf"\nextgroupplot[yticklabels={{{labels}}},title={{{title}}},xmax={xmax}]")
    for name, color, shift in [(left, "black!55", "3pt"),
                                (right, "green!45!black", "-3pt")]:
        coords = " ".join(f"({value},{i})" for i, value in enumerate(data[key][name]))
        plot.append(rf"\addplot[color={color},fill={color},draw=none,area legend,/pgf/bar shift={shift}] coordinates {{{coords}}};")
    if key == "al_cg_response":
        plot.append(r"\legend{Baseline,Response}")
plot += [r"\end{groupplot}", r"\end{tikzpicture}"]
(ROOT / "convergence-plot.tex").write_text("\n".join(plot) + "\n")
