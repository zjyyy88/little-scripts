from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from monty.serialization import dumpfn, loadfn
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition
from pymatgen.core.periodic_table import Element
from pymatgen.entries.compatibility import MaterialsProject2020Compatibility
from pymatgen.entries.computed_entries import ComputedEntry
from pymatgen.io.vasp.outputs import Vasprun


SUPPORTED_THERMO_TYPES = (
    "GGA_GGA+U",
    "GGA_GGA+U_R2SCAN",
    "R2SCAN",
)


def normalize_chemsys(raw_chemsys: str) -> list[str]:
    """Validate a chemical system and return unique element symbols."""
    tokens = [token for token in re.split(r"[-,\s]+", raw_chemsys.strip()) if token]
    if not tokens:
        raise ValueError("Chemical system is empty.")

    symbols: list[str] = []
    for token in tokens:
        try:
            symbol = Element(token).symbol
        except ValueError as exc:
            raise ValueError(f"Invalid element symbol: {token}") from exc
        if symbol not in symbols:
            symbols.append(symbol)

    if len(symbols) > 9:
        raise ValueError("Materials Project get_entries_in_chemsys supports at most 9 elements.")
    return symbols


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "_", value)
    return cleaned.strip("._") or "entry"


def find_entries_file(dataset: str | Path) -> tuple[Path, Path]:
    dataset_path = Path(dataset).expanduser().resolve()
    if dataset_path.is_dir():
        entries_path = dataset_path / "entries.json.gz"
        metadata_path = dataset_path / "metadata.json"
    else:
        entries_path = dataset_path
        metadata_path = dataset_path.parent / "metadata.json"

    if not entries_path.is_file():
        raise FileNotFoundError(f"Entry dataset not found: {entries_path}")
    return entries_path, metadata_path


def load_dataset(dataset: str | Path) -> tuple[list[Any], dict[str, Any]]:
    entries_path, metadata_path = find_entries_file(dataset)
    entries = loadfn(entries_path)
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"No entries found in {entries_path}")

    metadata: dict[str, Any] = {}
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return entries, metadata


def entry_summary(entry: Any, structure_file: str = "") -> dict[str, Any]:
    parameters = getattr(entry, "parameters", {}) or {}
    data = getattr(entry, "data", {}) or {}
    uncorrected_energy = getattr(entry, "uncorrected_energy", None)
    correction = getattr(entry, "correction", None)
    return {
        "material_id": str(getattr(entry, "entry_id", "") or ""),
        "formula": entry.composition.reduced_formula,
        "chemsys": "-".join(sorted(element.symbol for element in entry.composition.elements)),
        "num_atoms": float(entry.composition.num_atoms),
        "energy_total_corrected_eV": float(entry.energy),
        "energy_per_atom_corrected_eV": float(entry.energy_per_atom),
        "energy_total_uncorrected_eV": (
            float(uncorrected_energy) if uncorrected_energy is not None else ""
        ),
        "correction_eV": float(correction) if correction is not None else "",
        "run_type": str(parameters.get("run_type", "")),
        "thermo_type": str(data.get("thermo_type", "")),
        "structure_file": structure_file,
    }


def download_dataset(args: argparse.Namespace) -> int:
    elements = normalize_chemsys(args.chemsys)
    api_key = os.environ.get("MP_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "MP_API_KEY is not set. In PowerShell, set it for this session with "
            '$env:MP_API_KEY = "your-new-api-key"'
        )

    output_dir = Path(args.output).expanduser().resolve()
    entries_path = output_dir / "entries.json.gz"
    if entries_path.exists() and not args.force:
        raise FileExistsError(
            f"{entries_path} already exists. Use --force to replace this dataset."
        )

    print(
        f"Downloading {args.thermo_type} entries for {'-'.join(elements)} "
        "and all of its subsystems..."
    )
    with MPRester(api_key, mute_progress_bars=args.quiet) as mpr:
        entries = list(
            mpr.get_entries_in_chemsys(
                elements,
                compatible_only=True,
                inc_structure=True,
                additional_criteria={"thermo_types": [args.thermo_type]},
            )
        )
        database_version = getattr(mpr, "db_version", None)

    if not entries:
        raise RuntimeError("Materials Project returned no compatible entries.")

    output_dir.mkdir(parents=True, exist_ok=True)
    structures_dir = output_dir / "structures"
    if args.save_cifs:
        structures_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    used_filenames: set[str] = set()
    structure_failures = 0

    for index, entry in enumerate(entries, start=1):
        structure_file = ""
        structure = getattr(entry, "structure", None)
        if args.save_cifs and structure is not None:
            entry_id = str(getattr(entry, "entry_id", "") or f"entry-{index}")
            stem = safe_name(f"{entry_id}_{entry.composition.reduced_formula}")
            filename = f"{stem}.cif"
            if filename in used_filenames:
                filename = f"{stem}_{index}.cif"
            used_filenames.add(filename)
            target = structures_dir / filename
            try:
                structure.to(filename=str(target), fmt="cif")
                structure_file = str(Path("structures") / filename)
            except Exception as exc:  # Keep the thermodynamic dataset if one CIF fails.
                structure_failures += 1
                warnings.warn(f"Could not write {entry_id} to CIF: {exc}", stacklevel=2)

        rows.append(entry_summary(entry, structure_file))

    dumpfn(entries, entries_path)

    csv_path = output_dir / "energies.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "schema_version": 1,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "database_version": database_version,
        "chemsys": "-".join(elements),
        "elements": elements,
        "thermo_type": args.thermo_type,
        "compatible_only": True,
        "entry_count": len(entries),
        "cif_count": sum(bool(row["structure_file"]) for row in rows),
        "structure_failures": structure_failures,
        "energy_definition": (
            "ComputedEntry.energy after Materials Project compatibility corrections; "
            "energy_per_atom is corrected energy divided by atom count."
        ),
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Saved {len(entries)} entries to {entries_path}")
    print(f"Energy table: {csv_path}")
    if args.save_cifs:
        print(
            f"Structures: {structures_dir} "
            f"({metadata['cif_count']} CIF files, {structure_failures} failures)"
        )
    return 0


def entry_elements(entry: Any) -> set[str]:
    return {element.symbol for element in entry.composition.elements}


def build_target_from_vasprun(
    vasprun_path: str | Path,
    entry_id: str | None,
    allow_unconverged: bool,
    skip_potcar_check: bool,
) -> Any:
    path = Path(vasprun_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"vasprun file not found: {path}")

    vasprun = Vasprun(str(path), parse_dos=False, parse_eigen=False)
    if not vasprun.converged and not allow_unconverged:
        raise RuntimeError(
            "The VASP calculation is not electronically and ionically converged. "
            "Use --allow-unconverged only for a deliberate diagnostic calculation."
        )

    raw_entry = vasprun.get_computed_entry(
        inc_structure=True,
        entry_id=entry_id,
    )
    compatibility = MaterialsProject2020Compatibility(
        check_potcar=not skip_potcar_check,
        check_potcar_hash=False,
    )
    processed_entry = compatibility.process_entry(raw_entry, inplace=False)
    if processed_entry is None:
        raise RuntimeError(
            "MaterialsProject2020Compatibility rejected the VASP entry. Check the "
            "functional, Hubbard U values, POTCAR choices, and MP-compatible input settings."
        )
    return processed_entry


def build_target_from_corrected_energy(
    formula: str,
    energy: float,
    energy_unit: str,
    entry_id: str | None,
) -> ComputedEntry:
    composition = Composition(formula)
    total_energy = (
        energy * composition.num_atoms if energy_unit == "per-atom" else energy
    )
    return ComputedEntry(
        composition,
        total_energy,
        entry_id=entry_id or "user-corrected-energy",
    )


def analyze_against_reference(reference_entries: Sequence[Any], target_entry: Any) -> dict[str, Any]:
    reference_pd = PhaseDiagram(reference_entries)
    decomposition, signed_distance = reference_pd.get_decomp_and_e_above_hull(
        target_entry,
        allow_negative=True,
    )
    if decomposition is None or signed_distance is None:
        raise RuntimeError("No valid decomposition was found for the target composition.")

    final_pd = PhaseDiagram([*reference_entries, target_entry])
    final_e_above_hull = float(final_pd.get_e_above_hull(target_entry))

    decomposition_rows = []
    for phase, amount in sorted(
        decomposition.items(),
        key=lambda item: item[0].composition.reduced_formula,
    ):
        decomposition_rows.append(
            {
                "material_id": str(getattr(phase, "entry_id", "") or ""),
                "formula": phase.composition.reduced_formula,
                "amount": float(amount),
                "energy_per_atom_eV": float(phase.energy_per_atom),
            }
        )

    uncorrected_energy = getattr(target_entry, "uncorrected_energy", None)
    correction = getattr(target_entry, "correction", None)
    signed_distance = float(signed_distance)
    return {
        "target": {
            "entry_id": str(getattr(target_entry, "entry_id", "") or ""),
            "formula": target_entry.composition.reduced_formula,
            "composition": target_entry.composition.as_dict(),
            "num_atoms": float(target_entry.composition.num_atoms),
            "energy_total_corrected_eV": float(target_entry.energy),
            "energy_per_atom_corrected_eV": float(target_entry.energy_per_atom),
            "energy_total_uncorrected_eV": (
                float(uncorrected_energy) if uncorrected_energy is not None else None
            ),
            "correction_eV": float(correction) if correction is not None else None,
            "run_type": str((getattr(target_entry, "parameters", {}) or {}).get("run_type", "")),
        },
        "e_above_hull_eV_per_atom": final_e_above_hull,
        "e_above_hull_meV_per_atom": final_e_above_hull * 1000.0,
        "signed_distance_to_reference_hull_eV_per_atom": signed_distance,
        "stabilization_below_reference_hull_eV_per_atom": max(0.0, -signed_distance),
        "decomposition_against_reference_hull": decomposition_rows,
        "interpretation": (
            "e_above_hull is non-negative after adding the target to the phase diagram. "
            "A negative signed distance means the target lies below the downloaded MP "
            "reference hull and becomes a new stable phase."
        ),
    }


def analyze_target(args: argparse.Namespace) -> int:
    reference_entries, metadata = load_dataset(args.dataset)
    thermo_type = metadata.get("thermo_type")

    if args.vasprun:
        if thermo_type and thermo_type != "GGA_GGA+U":
            raise ValueError(
                "The vasprun workflow in this tool uses MaterialsProject2020Compatibility "
                "and therefore requires a GGA_GGA+U reference dataset. Download that "
                "thermo type, or use --formula with an already corrected compatible energy."
            )
        target_entry = build_target_from_vasprun(
            args.vasprun,
            args.entry_id,
            args.allow_unconverged,
            args.skip_potcar_check,
        )
        target_source = str(Path(args.vasprun).expanduser().resolve())
    else:
        if args.corrected_energy is None:
            raise ValueError("--corrected-energy is required when --formula is used.")
        target_entry = build_target_from_corrected_energy(
            args.formula,
            args.corrected_energy,
            args.energy_unit,
            args.entry_id,
        )
        target_source = "user-supplied already-corrected energy"

    reference_elements = set().union(*(entry_elements(entry) for entry in reference_entries))
    missing_elements = entry_elements(target_entry) - reference_elements
    if missing_elements:
        raise ValueError(
            "The dataset does not contain elemental references for: "
            + ", ".join(sorted(missing_elements))
        )

    result = analyze_against_reference(reference_entries, target_entry)
    result["reference_dataset"] = {
        "path": str(find_entries_file(args.dataset)[0]),
        "entry_count": len(reference_entries),
        "chemsys": metadata.get("chemsys"),
        "thermo_type": thermo_type,
        "database_version": metadata.get("database_version"),
    }
    result["target_source"] = target_source

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    target = result["target"]
    print(f"Target: {target['formula']} ({target['entry_id']})")
    print(
        "E above hull: "
        f"{result['e_above_hull_eV_per_atom']:.6f} eV/atom "
        f"({result['e_above_hull_meV_per_atom']:.2f} meV/atom)"
    )
    print(
        "Signed distance to downloaded MP hull: "
        f"{result['signed_distance_to_reference_hull_eV_per_atom']:.6f} eV/atom"
    )
    print("Reference-hull decomposition:")
    for phase in result["decomposition_against_reference_hull"]:
        label = phase["material_id"] or "no-id"
        print(f"  {phase['amount']:.6f}  {phase['formula']}  [{label}]")
    print(f"Full result: {output_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download Materials Project competing phases and calculate the convex-hull "
            "energy of a new material."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser(
        "download",
        help="Download compatible entries, corrected energies, and structures.",
    )
    download.add_argument(
        "--chemsys",
        required=True,
        help='Elements separated by "-", comma, or spaces, for example Li-P-S-Cl-I.',
    )
    download.add_argument("--output", required=True, help="Dataset output directory.")
    download.add_argument(
        "--thermo-type",
        choices=SUPPORTED_THERMO_TYPES,
        default="GGA_GGA+U",
        help="MP thermodynamic energy scheme. Default: GGA_GGA+U.",
    )
    download.add_argument(
        "--save-cifs",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Save one CIF structure per entry. Default: enabled.",
    )
    download.add_argument("--force", action="store_true", help="Replace an existing dataset.")
    download.add_argument("--quiet", action="store_true", help="Hide MP download progress bars.")
    download.set_defaults(func=download_dataset)

    analyze = subparsers.add_parser(
        "analyze",
        help="Calculate target stability against a downloaded reference dataset.",
    )
    analyze.add_argument(
        "--dataset",
        required=True,
        help="Dataset directory or entries.json.gz path.",
    )
    source = analyze.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--vasprun",
        help="Path to a converged MP-compatible vasprun.xml or vasprun.xml.gz.",
    )
    source.add_argument(
        "--formula",
        help="Formula for an energy that is already corrected to the dataset reference.",
    )
    analyze.add_argument(
        "--corrected-energy",
        type=float,
        help="Already corrected energy used with --formula.",
    )
    analyze.add_argument(
        "--energy-unit",
        choices=("total", "per-atom"),
        default="total",
        help="Unit basis for --corrected-energy. Default: total.",
    )
    analyze.add_argument("--entry-id", help="Optional identifier for the target entry.")
    analyze.add_argument(
        "--output",
        default="hull_result.json",
        help="Result JSON path. Default: ./hull_result.json.",
    )
    analyze.add_argument(
        "--allow-unconverged",
        action="store_true",
        help="Allow an unconverged vasprun only for diagnostics.",
    )
    analyze.add_argument(
        "--skip-potcar-check",
        action="store_true",
        help="Skip MP POTCAR symbol checking. This weakens compatibility validation.",
    )
    analyze.set_defaults(func=analyze_target)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
