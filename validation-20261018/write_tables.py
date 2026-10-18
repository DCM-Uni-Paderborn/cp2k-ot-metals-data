"""Generate the manuscript/SI numbers and editable plot from the raw-data analysis."""

import argparse
import json
from pathlib import Path

from campaign import ROOT


def sci(value, digits=2):
    if value is None:
        return "---"
    if value == 0:
        return "$0$"
    mantissa, exponent = f"{value:.{digits}e}".split("e")
    return rf"${mantissa}\times10^{{{int(exponent)}}}$"


def write(output):
    analysis = json.loads((ROOT / "analysis.json").read_text())
    rows = {r["case"]: r for r in analysis["cases"]}
    target = Path(output).resolve()
    target.mkdir(parents=True, exist_ok=True)
    pairs = {r["case"]: r for r in analysis["pairs"]}
    lines = [r"\begin{tabular}{llrrrr}\toprule",
             r"System & Solver & Steps & $-TS$ / Ha & $\Delta\Acal$ / Ha & Time / s\\\midrule"]
    base_names = []
    for element in ("al", "cu", "ni"):
        for method in ("cg", "lbfgs", "diag"):
            name = f"{element}-base-{method}" + ("-full-spin-space" if element == "ni" else "")
            row = rows.get(name)
            if not row:
                continue
            label = dict(cg="CG", lbfgs="L-BFGS", diag="Diagonalization")[method]
            if not row.get("converged"):
                iterations = str(row.get("last_scf_iteration") or "---") + r"$^{*}$"
                status = "Time limit" if row["stopping_status"] == "wall-time limit" else "SCF limit"
                lines.append(f"{element.title()} & {label} & {iterations} & --- & --- & {status}" + r"\\")
                continue
            base_names.append(name)
            difference = 0.0 if method == "diag" else pairs.get(name, {}).get("delta_free_energy_Ha")
            times = row["cp2k_times_s"]
            timing = f"{row['median_cp2k_time_s']:.2f}"
            lines.append(f"{element.title()} & {label} & {row['steps'][0][0]} & "
                         f"{row['minus_TS_Ha']:.6f} & {sci(abs(difference) if difference is not None else None)} & {timing}" + r"\\")
    lines += [r"\bottomrule\end{tabular}"]
    (target / "validation-base-table.tex").write_text("\n".join(lines) + "\n")
    lines = [r"\begin{tabular}{llrrrrl}\toprule",
             r"System & Solver & Samples & Median / s & Min / s & Max / s & Rebuilds\\\midrule"]
    for name in base_names:
        row = rows[name]
        label = "Diagonalization" if row["method"] == "DIAG" else row["method"]
        times = row["cp2k_times_s"]
        rebuilds = ",".join(str(x) for x in row["full_ks_subspace_rebuilds"])
        lines.append(f"{name[:2].title()} & {label} & {len(times)} & {row['median_cp2k_time_s']:.2f} & "
                     f"{min(times):.2f} & {max(times):.2f} & {rebuilds}" + r"\\")
    lines += [r"\bottomrule\end{tabular}"]
    (target / "validation-timing-table.tex").write_text("\n".join(lines) + "\n")
    lines = [r"\begin{tabular}{llrrrr}\toprule",
             r"System & Solver & $N$ & $N_\alpha-N_\beta$ & $\Acal$ / Ha & Repeat range / Ha\\\midrule"]
    for name in base_names:
        row = rows[name]
        spin = f"{row['integrated_spin']:.8f}" if row['integrated_spin'] is not None else "---"
        population = f"{row['electron_count']:.8f}" if row['electron_count'] is not None else "---"
        label = "Diagonalization" if row["method"] == "DIAG" else row["method"]
        lines.append(f"{name[:2].title()} & {label} & {population} & {spin} & "
                     f"{row['free_energy_Ha']:.11f} & {sci(row['free_energy_range_Ha'])}" + r"\\")
    lines += [r"\bottomrule\end{tabular}"]
    (target / "validation-endpoint-table.tex").write_text("\n".join(lines) + "\n")
    lines = [r"\begin{tabular}{lrrrr}\toprule",
             r"Quadrature & Points & $N$ & $-TS$ / Ha & $\Acal$ / Ha\\\midrule"]
    for name, label in (("al-canonical-full", "Full mesh"),
                        ("al-canonical-reduced", "Spatially reduced")):
        row = rows.get(name)
        if row and row.get("converged"):
            lines.append(f"{label} & {int(row['kpoint_count'])} & {row['electron_count']:.8f} & "
                         f"{row['minus_TS_Ha']:.10f} & {row['free_energy_Ha']:.11f}" + r"\\")
    lines += [r"\bottomrule\end{tabular}"]
    (target / "validation-symmetry-table.tex").write_text("\n".join(lines) + "\n")
    lines = [r"\begin{tabular}{llrrrr}\toprule",
             r"System & Solver & Orbitals & AO rank & Steps & $|\Delta\Acal|$ / Ha\\\midrule"]
    for element in ("al", "cu", "ni"):
        for method in ("cg", "lbfgs", "diag"):
            name = "al-auto" if (element, method) == ("al", "cg") else f"{element}-reduced-{method}"
            row = rows.get(name)
            if not row or not row.get("converged"):
                continue
            difference = 0.0 if method == "diag" else pairs.get(name, {}).get("delta_free_energy_Ha")
            orbitals = row.get("mo_count")
            rank = row.get("ao_count")
            label = "Diagonalization" if method == "diag" else row["method"]
            lines.append(f"{element.title()} & {label} & {orbitals} & {int(rank) if rank else '---'} & "
                         f"{row['steps'][0][0]} & " + sci(abs(difference) if difference is not None else None) + r"\\")
    lines += [r"\bottomrule\end{tabular}"]
    (target / "validation-subspace-table.tex").write_text("\n".join(lines) + "\n")
    lines = [r"\begin{tabular}{llrrr}\toprule",
             r"Model & Solver & Steps & $\Acal$ / Ha & $|\Delta\Acal|$ / Ha\\\midrule"]
    for model in ("gfn1", "gfn2"):
        for method in ("ot", "diag"):
            name = f"al-{model}-{method}"
            row = rows.get(name)
            if not row or not row.get("converged"):
                continue
            difference = 0.0 if method == "diag" else pairs.get(name, {}).get("delta_free_energy_Ha")
            label = ("Direct OT" if model == "gfn1" else "Inner OT") if method == "ot" else "Diagonalization"
            lines.append(f"{model.upper()} & {label} & {row['steps'][0][0]} & "
                         f"{row['free_energy_Ha']:.12f} & {sci(abs(difference) if difference is not None else None)}" + r"\\")
    lines += [r"\bottomrule\end{tabular}"]
    (target / "validation-tblite-table.tex").write_text("\n".join(lines) + "\n")
    lines = [r"\begin{longtable}{p{0.53\linewidth}rrr}",
             r"\caption{Electronic-structure cases and the first converged endpoint when available. A dash denotes an incomplete or failed case. An asterisk marks a converged electronic solve that violates the requested spin constraint. Step counts sum converged electronic solves for motion. Separate attempts, stopping statuses, residuals, and timing samples accompany the archive.}\label{tab:allcases}\\",
             r"\toprule Case & Steps & $\Acal$ / Ha & Correction / Ha\\\midrule\endfirsthead",
             r"\toprule Case & Steps & $\Acal$ / Ha & Correction / Ha\\\midrule\endhead"]
    for name, row in rows.items():
        if (name.startswith("ni-") and not name.endswith("-full-spin-space")
                and "fixed-moment" not in name and row["group"] != "variational-subspace"):
            continue
        if row.get("converged"):
            correction = f"{row['objective_correction_Ha']:.6f}" if row['objective_correction_Ha'] is not None else "---"
            values = (str(sum(row["steps"][0])), f"{row['free_energy_Ha']:.10f}", correction)
            if row.get("spin_constraint_satisfied") is False:
                values = ("$" + values[0] + "^{*}$", values[1], values[2])
        else:
            values = ("---", "---", "---")
        lines.append(rf"\nolinkurl{{{name}}} & " + " & ".join(values) + r"\\")
    lines += [r"\bottomrule\end{longtable}"]
    (target / "validation-case-table.tex").write_text("\n".join(lines) + "\n")
    lines = [r"\begin{tabular}{lrrr}\toprule",
             r"$T$ / K & Displacement / \AA & Analytical / Ha bohr$^{-1}$ & Absolute error / Ha bohr$^{-1}$\\\midrule"]
    for check in analysis["force_checks"]:
        temperature = 3000 if check["case"].endswith("thermal") else 600
        lines.append(f"{temperature} & {check['step_A']} & {check['analytical_Ha_per_bohr']:.9f} & "
                     + sci(check["absolute_error_Ha_per_bohr"]) + r"\\")
    lines += [r"\bottomrule\end{tabular}"]
    (target / "validation-force-table.tex").write_text("\n".join(lines) + "\n")
    lines = [r"\begin{tabular}{lllrrrr}\toprule",
             r"$T$ / K & Method & Target & Space & $\Delta t$ / fs & Range / Ha & Drift / Ha fs$^{-1}$\\\midrule"]
    for check in analysis["dynamics"]:
        temperature = check["temperature_K"]
        timestep = 0.125 if "0.125" in check["case"] else 0.25
        space = "Tail" if check["added_mos"] == "AUTO" else "Full"
        exponent = f"{check['eps_scf']:.0e}".split("e")[1]
        label = "L-BFGS" if check["method"] == "LBFGS" else check["method"]
        lines.append(f"{temperature} & {label} & $10^{{{int(exponent)}}}$ & {space} & {timestep} & "
                     + sci(check["conserved_energy_range_Ha"]) + " & "
                     + sci(check["least_squares_drift_Ha_per_fs"]) + r"\\")
    lines += [r"\bottomrule\end{tabular}"]
    (target / "validation-md-table.tex").write_text("\n".join(lines) + "\n")
    lines = [r"\begin{tabular}{lllrrlr}\toprule",
             r"$T$ / K & Method & Space & $\Delta t$ / fs & Completed / fs & Stop & Last residual\\\midrule"]
    for check in analysis["interrupted_dynamics"]:
        space = "Tail" if check["added_mos"] == "AUTO" else "Full"
        label = "L-BFGS" if check["method"] == "LBFGS" else check["method"]
        lines.append(f"{check['temperature_K']} & {label} & {space} & {check['timestep_fs']} & "
                     f"{check['completed_time_fs']:.3f} & {check['stopping_status']} & "
                     + sci(check["last_scf_residual"]) + r"\\")
    lines += [r"\bottomrule\end{tabular}"]
    (target / "validation-motion-limits-table.tex").write_text("\n".join(lines) + "\n")
    lines = [r"\begin{tabular}{lrrrl}\toprule",
             r"Optimization & $T$ / K & Nuclear steps & SCF solves & Nuclear status\\\midrule"]
    for check in analysis["optimization"]:
        label = "Geometry" if check["run_type"] == "GEO_OPT" else "Cell"
        status = ("Converged" if check["converged"] else "Step limit" if check["step_limit_reached"]
                  else "Time limit" if check["returncode"] == 124 else "SCF incomplete")
        steps = int(check["nuclear_steps"]) if check["nuclear_steps"] is not None else "---"
        lines.append(f"{label} & {check['temperature_K']} & {steps} & {check['scf_solves']} & {status}" + r"\\")
    lines += [r"\bottomrule\end{tabular}"]
    (target / "validation-optimization-table.tex").write_text("\n".join(lines) + "\n")
    lines = [r"\begin{tabular}{lcrrr}\toprule",
             r"$T$ / K & Component & Analytical & Central difference & Absolute error\\\midrule"]
    for check in analysis["stress_checks"]:
        temperature = 3000 if check["case"].endswith("thermal") else 600
        i, j = check["component"]
        component = "xyz"[i] + "xyz"[j]
        lines.append(f"{temperature} & {component} & {sci(check['analytical_Ha_per_bohr3'])} & "
                     + sci(check["numerical_Ha_per_bohr3"]) + " & "
                     + sci(check["absolute_error_Ha_per_bohr3"]) + r"\\")
    lines += [r"\bottomrule\end{tabular}"]
    (target / "validation-stress-table.tex").write_text("\n".join(lines) + "\n")
    lines = [r"\begin{tabular}{llrrrr}\toprule",
             r"Constraint & Solver & Steps & Target $N_\alpha-N_\beta$ & Actual & $|\Delta\Acal|$ / Ha\\\midrule"]
    for name, row in rows.items():
        if row["group"] != "spin-probes" or not row.get("converged"):
            continue
        constraint = row.get("spin_constraint", "free")
        if name.startswith("ni-"):
            constraint = "Ni fixed"
        spin_target = row.get("requested_spin_difference")
        spin_label = f"{spin_target:g}" if spin_target is not None else "Free"
        difference = 0.0 if row["method"] == "DIAG" else pairs.get(name, {}).get("delta_free_energy_Ha")
        lines.append(f"{constraint} & {row['method']} & {row['steps'][0][0]} & {spin_label} & {row['integrated_spin']:.7f} & "
                     + sci(abs(difference) if difference is not None else None) + r"\\")
    lines += [r"\bottomrule\end{tabular}"]
    (target / "validation-spin-table.tex").write_text("\n".join(lines) + "\n")
    plot = [r"\begin{tikzpicture}",
            r"\begin{groupplot}[group style={group size=1 by 2,vertical sep=1.5cm},",
            r"width=0.85\linewidth,height=5cm,ybar,/pgf/bar width=9pt,",
            r"symbolic x coords={Al,Cu,Ni},xtick={Al,Cu,Ni},enlarge x limits=0.22,",
            r"ymajorgrids,grid style={black!12},tick label style={font=\small},",
            r"legend image code/.code={\path[#1] (0cm,-0.08cm) rectangle (0.18cm,0.08cm);},",
            r"legend style={draw=none,font=\small,at={(0.5,1.03)},anchor=south,legend columns=3,column sep=5pt}]",
            r"\nextgroupplot[ylabel={Electronic iterations},ymin=0]"]
    for field in ("steps", "median_cp2k_time_s"):
        if field != "steps":
            plot.append(r"\nextgroupplot[ylabel={CP2K elapsed time / s},ymode=log]")
        for method, label, color in (("cg", "CG", "blue!60!black"), ("lbfgs", "L-BFGS", "green!40!black"),
                                     ("diag", "Diagonalization", "black!45")):
            coordinates = []
            for element in ("al", "cu", "ni"):
                name = f"{element}-base-{method}" + ("-full-spin-space" if element == "ni" else "")
                row = rows.get(name)
                if row and row.get("converged"):
                    value = row["steps"][0][0] if field == "steps" else row[field]
                    coordinates.append(f"({element.title()},{value:.8g})")
            plot.append(rf"\addplot[fill={color},draw=none] coordinates {{" + " ".join(coordinates) + "};")
            if field == "steps":
                plot.append(rf"\addlegendentry{{{label}}}")
    plot += [r"\end{groupplot}", r"\end{tikzpicture}"]
    (target / "convergence-plot.tex").write_text("\n".join(plot) + "\n")
    (target / "validation-results.json").write_text(json.dumps(analysis, indent=2) + "\n")
    print(f"Wrote tables for {len(rows)} archived cases and {len(base_names)} base endpoints.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=ROOT / "publication")
    write(parser.parse_args().output)
