---
name: gaussian-molecule-workflow
description: Generate, validate, run, resume, and analyze finite-molecule Gaussian calculations from Chinese or English requests and XYZ, MOL V2000, SDF V2000, PDB, or PubChem molecule queries. Use for database structure retrieval with mandatory human structure confirmation, charge and multiplicity resolution, Gaussian/formchk execution, ESP surface extrema, HOMO/LUMO energies and cubes, ELF 2D/3D maps, molecular-box dimensions, thermochemistry, and optimized-structure export. The workflow requires preflight for Gaussian, formchk, Multiwfn, VMD, Python, PyYAML, NumPy, Pillow, and Matplotlib. Do not use for periodic CIF, CASTEP, VASP, or molecular dynamics.
---

# Gaussian molecule workflow v1.6.2

Use this standalone Windows skill for finite-molecule Gaussian 16 jobs. Treat the four bundled analysis skills as one post-Gaussian pipeline: ESP, HOMO/LUMO, ELF, and molecular box.

## Mandatory preflight and setup

Run this before preparing, running, or visualizing a molecule:

```powershell
python scripts/gaussian_workflow.py preflight --scope full --json
```

The gate checks:

- Gaussian console executable (`g16.exe`) and `formchk.exe`;
- Multiwfn (`Multiwfn.exe`, the WFN/wavefunction analyzer) plus its `settings.ini`;
- VMD (`vmd.exe`);
- the active Python interpreter and PyYAML, NumPy, Pillow, and Matplotlib.

If Python packages are missing and installation is authorized, rerun with:

```powershell
python scripts/gaussian_workflow.py preflight --scope full --install-python --write-config
```

Gaussian, Multiwfn, and VMD are external/proprietary applications and are not bundled or silently downloaded. If one is missing, report the exact component, request an installer or executable path, set `GAUSSIAN_EXE`, `FORMCHK_EXE`, `MULTIWFN_BIN`, `MULTIWFNPATH`, or `VMD_BIN` as appropriate, and rerun preflight. `--write-config` writes a local `config/gaussian.local.json`; never share that machine-specific file.

Do not start Gaussian or visualization while preflight is `BLOCKED`. Do not claim that discovering an executable automatically changes the parent process environment. The bundled `analyze` command propagates discovered paths to every substage; when running a substage manually, set the reported environment variables first.

## Initial structures from PubChem

When the user gives a molecule name, formula, SMILES, InChI, or CID but no usable coordinates, retrieve the starting structure before Gaussian preparation:

```powershell
python scripts/gaussian_workflow.py fetch `
  --query "TTE" --name TTE --output-dir molecule_sources --json
```

`fetch` resolves the PubChem CID through PUG REST, tries the 3-D SDF first, saves the structure, and writes `<name>.pubchem.json` with the CID, identity properties, source URL, record type, warnings, electron count, charge, multiplicity, and an unconfirmed structure gate. It uses the standard-library HTTP client; if the network or PubChem is unavailable, report the exact error and do not invent coordinates.

Ambiguous battery abbreviations are pinned in `references/pubchem_aliases.json` (including TTE, LiFSI, and FSI-); use `--cid` when a query has multiple legitimate identities.

For a compound without a PubChem 3-D conformer, the default is an explicitly flagged 2-D fallback. Use `--strict-3d` when a planar starting geometry is unacceptable. For a dot-separated salt such as LiFSI, use:

```powershell
python scripts/gaussian_workflow.py fetch `
  --query "LiFSI" --name LiFSI --output-dir molecule_sources `
  --assemble-disconnected --charge 0 --multiplicity 1 --json
```

The salt option fetches separately available component geometries and writes a non-overlapping XYZ ion-pair starting guess. It is not a crystal or solvent structure; optimize it and, when the result is final, run a frequency calculation to check for imaginary modes. The manifest must remain alongside the XYZ.

### Mandatory structure confirmation gate

Never generate a GJF or launch Gaussian from a PubChem-derived structure until the user has inspected and approved the actual structure. Show the user the resolved name/formula/CID, record type (3-D, 2-D fallback, or assembled ion pair), charge/multiplicity, and a view of the coordinates in VMD/Multiwfn. Ask explicitly whether the structure is correct. Do not issue `--yes` on the user's behalf.

Inspect the sidecar first:

```powershell
python scripts/gaussian_workflow.py confirm-structure --input molecule_sources/TTE.sdf --json
```

After the user explicitly confirms the structure, record the approval:

```powershell
python scripts/gaussian_workflow.py confirm-structure `
  --input molecule_sources/TTE.sdf --yes `
  --note "User confirmed the PubChem structure after visual inspection."
```

The command stores the confirmation time, note, and structure SHA256 in the sidecar. `gaussian_pipeline.py` refuses to generate the Gaussian input while the gate is unconfirmed or when the structure has changed after approval. Manual/local structures without a PubChem sidecar do not use this particular structure-identity gate, but charge/multiplicity validation still applies.

Never continue to Gaussian if the fetch manifest reports unknown charge/multiplicity or a parity mismatch. For a resolved structure, pass the manifest values explicitly to the GJF pipeline, for example `--charge -1 --multiplicity 1` for FSI-. PubChem identity and formula do not by themselves prove a spin state; use the species rules or ask the user when the state is ambiguous.

## Core Gaussian workflow

Use `prepare` to validate the structure and generate GJF, `run` to execute an explicitly approved GJF, `parse` to parse an existing job, `resume`/`status` to determine the next safe action, and `full` for prepare -> Gaussian -> formchk -> parse. Never launch a real Gaussian calculation without explicit user authorization and a satisfied command-template safety gate.

Default non-monatomic task: single-point plus Opt/Freq. Default theory: B3LYP/6-311+G(d,p), GD3BJ, SCF=(Tight,XQC), Int=UltraFine, Opt=Tight. Resolve charge/multiplicity from the user, species rules, and fragment validation; never silently assume unknown `0 1`. Automatic HOMO/LUMO selection is restricted to closed-shell systems; require explicit spin-channel/index instructions for UHF, ROHF, open-shell, or fractional occupations.

## Complete post-Gaussian analysis

After Gaussian and `formchk` produce `analysis/fch/<M>.fch`, run one command from the skill root or analysis folder:

```powershell
python scripts/gaussian_workflow.py analyze `
  --input analysis/fch --output analysis/output --render
```

`analyze` runs, in order, the bundled ESP, frontier-orbital, ELF, and molecular-box stages. It performs a second full dependency preflight, propagates executable/settings paths, stops on failed required outputs, and writes `analysis_manifest.json`. Use `--install-python` on the first run if Python packages are missing. To generate cubes and TXT files without VMD PNGs, omit `--render`.

## Output contract per molecule `<M>`

The complete rendered run must contain:

- ESP: `<M>_density.cub`, `<M>_ESP.cub`, `<M>_ESP.png`, `<M>_esp_stats.txt`, and `<M>_dimensions.txt`. The statistics and color scale use the actual Multiwfn ESP minimum/maximum on the `rho=0.001` surface. The dimensions file is the electron-density isosurface extent and is distinct from the molecular box.
- HOMO/LUMO: the selected `<M>_orb######.cub` files, `<M>_HOMO<index>.png`, `<M>_LUMO<index>.png`, `<M>_energies.txt`, and root-level `orbital_indices.txt`. The energy TXT contains orbital indices, Hartree, eV, kcal/mol, and the gap.
- ELF: `<M>_ELF.cub`, VMD 3D `<M>_ELF.png`, default 2D XY maps `<M>_ELF_fill_xy.png` and `<M>_ELF_shaded+proj_xy.png`, plus the exported plane TXT/log files. Use `--plane xy|xz|yz|atoms` for another plane.
- Molecular box: `<M>.pdb`, `new.pdb`, `<M>_box_dimensions.txt`, and `<M>_BOX.png`. The TXT and PNG dimensions come from the PDB `CRYST1` record and are reported as X x Y x Z in Angstrom.

Keep per-molecule Multiwfn, VMD, and Matplotlib logs. Do not reuse an old cube, plane file, PDB, TGA, or PNG when the current stage failed.

## Sharing and portability

Share only the clean skill directory containing `SKILL.md`, `requirements.txt`, `config/gaussian.local.example.json`, `references/`, `scripts/` (including `pubchem_structure.py`), and the four bundled `skills/` subdirectories. Exclude `config/gaussian.local.json`, `__pycache__/`, test/visual-test outputs, Gaussian jobs, downloaded structures, sidecars with approvals, and analysis results. The recipient must have network access for PubChem retrieval and install or already possess licensed Gaussian, Multiwfn, and VMD, then run preflight and configure their own executable paths. The skill contains no machine-specific executable paths in its shareable configuration.

## Failure handling

Report the failed stage, executable path, return code, and corresponding log. Preserve valid outputs from earlier completed stages, but do not report the complete pipeline as successful unless all requested required files pass readability and existence checks.
