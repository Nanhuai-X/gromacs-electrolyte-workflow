# Structure input and Gaussian workflow integration

The electrolyte Skill accepts an initial finite-molecule structure from:

- XYZ;
- MOL V2000;
- SDF V2000;
- PDB;
- a PubChem query/CID when no local coordinates are supplied.

PubChem is an optional identity source, not a mandatory structure source. A manually built MOL, SDF, XYZ, or PDB is allowed when its identity, atom order, connectivity, formal charge, multiplicity, and source/provenance are explicitly reviewed.

## Required structure gates

1. Detect the input format and record the source SHA256.
2. Preserve atom order. Do not silently reorder atoms during format conversion.
3. Validate atom count and coordinates.
4. Validate formula/identity, formal charge, multiplicity, and connectivity.
5. For MOL/SDF V2000, use the bond block as the connectivity source.
6. For XYZ and PDB, connectivity is not complete enough for an automatic force-field decision; require a separate connectivity approval or an audited topology.
7. Require explicit structure confirmation before Gaussian input generation. A confirmation sidecar contains the source SHA256, status CONFIRMED, and a user note.
8. If charge or multiplicity is unknown, stop. Never assume 0 1 from the file name or formula.

scripts/structure_adapter.py performs only format detection, coordinate extraction, atom-count/hash recording, and connectivity status reporting. It does not infer bonds, charges, multiplicity, force-field types, or scientific parameters.

## Gaussian molecule workflow route

If an external compatible finite-molecule/Gaussian workflow Skill is available, use it as the reference for local finite-molecule preparation. Otherwise use the bundled snapshot and stop when a required external capability is unavailable:

- its preflight checks Gaussian/formchk, Multiwfn/settings.ini, VMD, Python, PyYAML, NumPy, Pillow, and Matplotlib;
- prepare validates the structure and creates Gaussian input;
- confirm-structure records explicit human approval and a structure hash;
- run/resume/status manage approved Gaussian execution;
- formchk creates FCHK;
- the RESP/RESP2 route consumes validated geometry, atom mapping, charge, multiplicity, and ESP outputs.

The electrolyte Skill reuses this workflow as a source/adapter; it does not replace its structure confirmation or quantum preflight. The Windows Gaussian project remains separate from the WSL GROMACS control root.

For a local-file route, use the existing Gaussian workflow's prepare/confirm commands on the actual MOL, SDF, XYZ, or PDB file, then pass the approved geometry and manifest to gaussian_builder.py and gaussian_resp_router.py. Do not use an old Gaussian output solely because its filename matches a new molecule.

## Format-specific limitations

- XYZ has coordinates but no reliable bond order. Connectivity must come from an audited source or manual review.
- PDB may have missing element, bond, charge, or multiplicity information. Do not infer a molecular graph from residue names alone.
- MOL/SDF V2000 provides a graph and coordinates, but formal charge and multiplicity still require explicit validation.
- V3000 and periodic CIF are not accepted by the lightweight adapter; use a separately audited converter and preserve an input/output atom mapping.
- A PubChem 3-D structure still requires visual/user confirmation before Gaussian.

After Gaussian/RESP, only derived, hashed charge registries and topology inputs move to the selected GROMACS backend. Raw Gaussian files remain in the Gaussian source project unless the user explicitly approves a transfer.
