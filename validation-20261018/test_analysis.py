"""Regression checks for the interpretation of CP2K output, not its physics."""

from pathlib import Path
import tempfile
import unittest

from analyze import trajectory_statistics
from campaign import ROOT, summarize


class OutputAnalysisTests(unittest.TestCase):
    def test_actual_mpi_size_is_required(self):
        with tempfile.TemporaryDirectory(prefix="analysis-check-", dir=ROOT) as directory:
            path = Path(directory)
            (path / "output.out").write_text(
                " GLOBAL| Total number of message passing processes 1\n PROGRAM ENDED AT\n")
            self.assertFalse(summarize(path, dict(ranks=2))["launcher_valid"])
            self.assertTrue(summarize(path, dict(ranks=1))["launcher_valid"])
            (path / "output.out").write_text(" PROGRAM ENDED AT\n")
            self.assertFalse(summarize(path, dict(ranks=2))["launcher_valid"])

    def test_energy_columns(self):
        rows = [[0, 0, 0.1, 100, -0.5, -0.4, 0],
                [1, 1, 0.2, 200, -0.5, -0.3, 99]]
        result = trajectory_statistics(rows)
        self.assertEqual(result["samples"], 2)
        self.assertEqual(result["repeated_identical_samples"], 0)
        self.assertAlmostEqual(result["conserved_energy_range_Ha"], 0.1)
        self.assertAlmostEqual(result["least_squares_drift_Ha_per_fs"], 0.1)

    def test_conflicting_duplicate_rejected(self):
        rows = [[0, 0, 0.1, 100, -0.5, -0.4, 0],
                [1, 1, 0.2, 200, -0.5, -0.3, 99],
                [1, 1, 0.2, 200, -0.5, -0.2, 101]]
        with self.assertRaises(ValueError):
            trajectory_statistics(rows)
        rows[-1][5] = rows[-2][5]
        with self.assertRaises(ValueError):
            trajectory_statistics(rows)

    def test_stress_block_and_generalized_correction(self):
        text = """ SCF run converged in 8 steps
 8 OT CG 0.1 1.2 1.0E-7 -2.0 -1.0E-8
 ENERGY| Total FORCE_EVAL ( QS ) energy [hartree] -2.0
 Smearing free energy correction: -0.001
 *** K-point smearing includes the ***
 *** last band ***
 STRESS| Analytical stress tensor [bar]
 STRESS| x 2.0 0.1 0.2
 STRESS| y 0.1 3.0 0.3
 STRESS| z 0.2 0.3 4.0

 STRESS| Eigenvectors
 STRESS| x 1.0 0.0 0.0
 STRESS| y 0.0 1.0 0.0
 STRESS| z 0.0 0.0 1.0
 PROGRAM ENDED AT
"""
        with tempfile.TemporaryDirectory(prefix="analysis-check-", dir=ROOT) as directory:
            path = Path(directory)
            (path / "output.out").write_text(text)
            result = summarize(path, dict(returncode=0))
        self.assertEqual(result["stress_bar"][0], [2.0, 0.1, 0.2])
        self.assertIsNone(result["minus_TS_Ha"])
        self.assertEqual(result["objective_correction_Ha"], -0.001)
        self.assertFalse(result["finite_entropy"])
        self.assertEqual(result["band_boundary_warnings"], 1)
        self.assertEqual(result["last_scf_residual"], 1e-7)


if __name__ == "__main__":
    unittest.main()
