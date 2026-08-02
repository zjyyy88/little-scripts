import tempfile
import unittest
from pathlib import Path

from monty.serialization import dumpfn
from pymatgen.core import Composition
from pymatgen.entries.computed_entries import ComputedEntry

from mp_hull import (
    analyze_against_reference,
    find_entries_file,
    normalize_chemsys,
)


class MpHullTests(unittest.TestCase):
    def test_normalize_chemsys(self):
        self.assertEqual(normalize_chemsys("Li-P-S-Cl-I"), ["Li", "P", "S", "Cl", "I"])
        self.assertEqual(normalize_chemsys("Li, O, Li"), ["Li", "O"])

    def test_binary_hull_energy(self):
        references = [
            ComputedEntry(Composition("Li"), 0.0, entry_id="Li"),
            ComputedEntry(Composition("O2"), 0.0, entry_id="O2"),
            ComputedEntry(Composition("Li2O"), -6.0, entry_id="Li2O"),
        ]
        target = ComputedEntry(Composition("LiO"), -2.0, entry_id="target")

        result = analyze_against_reference(references, target)

        self.assertAlmostEqual(result["e_above_hull_eV_per_atom"], 0.5, places=10)
        self.assertAlmostEqual(
            result["signed_distance_to_reference_hull_eV_per_atom"],
            0.5,
            places=10,
        )

    def test_dataset_directory_resolution(self):
        entries = [
            ComputedEntry(Composition("Li"), 0.0, entry_id="Li"),
            ComputedEntry(Composition("O2"), 0.0, entry_id="O2"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_dir = Path(temp_dir)
            dumpfn(entries, dataset_dir / "entries.json.gz")
            entries_path, metadata_path = find_entries_file(dataset_dir)

            self.assertEqual(entries_path.name, "entries.json.gz")
            self.assertEqual(metadata_path.name, "metadata.json")


if __name__ == "__main__":
    unittest.main()
