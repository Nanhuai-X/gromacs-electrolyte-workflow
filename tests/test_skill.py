#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from mdp_builder import DEFAULT, write_mdp
import common
from common import sha256


class SkillTests(unittest.TestCase):
    def test_mean_falls_back_without_statistics_fmean(self):
        with patch.object(common.statistics, "fmean", None, create=True):
            self.assertEqual(common.mean([1, 2, 3]), 2.0)

    def test_default_step_and_output_contract(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            write_mdp(out / "anneal.mdp", DEFAULT, "anneal")
            write_mdp(out / "npt.mdp", DEFAULT, "npt")
            write_mdp(out / "nvt_transition.mdp", DEFAULT, "nvt_transition")
            write_mdp(out / "production.mdp", DEFAULT, "production")
            self.assertIn("nsteps = 300000", (out / "anneal.mdp").read_text())
            self.assertIn("nsteps = 2500000", (out / "npt.mdp").read_text())
            self.assertIn("nsteps = 500000", (out / "nvt_transition.mdp").read_text())
            self.assertIn("nsteps = 10000000", (out / "production.mdp").read_text())
            self.assertIn("nstxout-compressed = 1000", (out / "production.mdp").read_text())
            self.assertEqual(
                DEFAULT["production_steps"] // DEFAULT["nstxout_compressed"] + 1,
                10001,
            )

    def test_composition_counts_and_missing_base(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            cfg = {
                "system": {"base_component_count": 50},
                "components": [
                    {"name": "LiFSI", "ratio": "1"},
                    {"name": "DME", "ratio": "1.2"},
                    {"name": "TTE", "ratio": "3"},
                ],
            }
            (td / "cfg.json").write_text(json.dumps(cfg))
            out = td / "composition.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "composition_builder.py"),
                    "--config",
                    str(td / "cfg.json"),
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0)
            data = json.loads(out.read_text())
            self.assertEqual([c["count"] for c in data["components"]], [50, 60, 150])
            cfg["system"]["base_component_count"] = None
            (td / "cfg.json").write_text(json.dumps(cfg))
            self.assertNotEqual(
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "composition_builder.py"),
                        "--config",
                        str(td / "cfg.json"),
                        "--out",
                        str(out),
                    ]
                ).returncode,
                0,
            )

    def test_runner_guards(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            top = td / "topol.top"
            top.write_text("")
            mdp = td / "production.mdp"
            mdp.write_text("")
            cpt = td / "state.cpt"
            cpt.write_bytes(b"checkpoint")
            out = td / "plan.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "gromacs_runner.py"),
                    "--stage",
                    "production",
                    "--run-dir",
                    str(td / "run"),
                    "--topology",
                    str(top),
                    "--input",
                    str(mdp),
                    "--checkpoint",
                    str(cpt),
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(json.loads(out.read_text())["status"], "PLAN_ONLY")
            bad = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "gromacs_runner.py"),
                    "--stage",
                    "em",
                    "--run-dir",
                    str(td / "run"),
                    "--topology",
                    str(top),
                    "--input",
                    str(td / "maxwarn.mdp"),
                    "--out",
                    str(out),
                ]
            )
            self.assertNotEqual(bad.returncode, 0)

    def test_rdf_no_shell_and_msd(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            rdf = td / "rdf.xvg"
            rdf.write_text(
                "# test\n0.1 0.2\n0.2 1.0\n0.3 1.2\n0.4 1.1\n0.5 0.9\n"
            )
            out = td / "rdf.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "rdf_cn.py"),
                    "--rdf",
                    str(rdf),
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(
                json.loads(out.read_text())["status"], "NO_PHYSICAL_FIRST_SHELL"
            )
            msd = td / "msd.xvg"
            msd.write_text("\n".join(f"{t} {6*t}" for t in range(1, 21)) + "\n")
            mout = td / "msd.json"
            self.assertEqual(
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "msd_diffusion.py"),
                        "--msd",
                        str(msd),
                        "--windows",
                        "5:20",
                        "--out",
                        str(mout),
                    ]
                ).returncode,
                0,
            )
            self.assertAlmostEqual(
                json.loads(mout.read_text())["fits"][0]["D_in_msd_units"], 1.0
            )

    def test_environment_preflight_requires_configured_root(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "preflight.json"
            env = os.environ.copy()
            env.pop("GROMACS_PROJECT_ROOT", None)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "environment_preflight.py"),
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(proc.returncode, 2)
            data = json.loads(out.read_text())
            self.assertEqual(data["status"], "PROJECT_ROOT_REQUIRED")
            self.assertIn("GROMACS_PROJECT_ROOT", data["configuration_policy"])

    def test_wsl_preflight_gate_when_project_exists(self):
        project_value = os.environ.get("GROMACS_PROJECT_ROOT")
        if not project_value:
            self.skipTest("GROMACS_PROJECT_ROOT is not configured in this environment")
        project = Path(project_value)
        if not project.is_dir():
            self.skipTest("configured GROMACS project root is not mounted in this environment")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "preflight.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "environment_preflight.py"),
                    "--project-root",
                    str(project),
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertIn(proc.returncode, (0, 2))
            data = json.loads(out.read_text())
            self.assertIn("is_wsl", data)
            self.assertIn("filesystem_type", data)
            self.assertIn("missing_core", data)
            self.assertIn("setup_plan", data)
            self.assertIn("make", data["tools"])
            setup = Path(td) / "setup.json"
            setup_proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "environment_setup.py"),
                    "--preflight",
                    str(out),
                    "--out",
                    str(setup),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(setup_proc.returncode, 0)
            self.assertEqual(json.loads(setup.read_text())["status"], "NO_ACTION_REQUIRED")
            fake_preflight = Path(td) / "fake_preflight.json"
            fake_preflight.write_text(json.dumps({
                "missing_core": ["cmake", "gromacs_cpu_or_cuda_prefix"],
                "setup_plan": {},
            }))
            blocked = Path(td) / "blocked_setup.json"
            blocked_proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "environment_setup.py"),
                    "--preflight",
                    str(fake_preflight),
                    "--out",
                    str(blocked),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(blocked_proc.returncode, 0)
            blocked_data = json.loads(blocked.read_text())
            self.assertEqual(blocked_data["status"], "ENVIRONMENT_BLOCKED")
            self.assertIn("cmake", blocked_data["missing_core_plan"])

    def test_literature_protocol_and_charge_choice(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            cfg = {
                "protocol": {"mode": "reference_guided"},
                "literature_protocol": {
                    "source": "test paper",
                    "temperature_K": 310.0,
                    "thermostat": {"name": "v-rescale", "tau_t_ps": 0.5},
                    "barostat": {
                        "name": "Berendsen",
                        "type": "isotropic",
                        "tau_p_ps": 2.0,
                    },
                    "electrostatics": {"coulombtype": "Ewald"},
                    "stages": {"production": {"duration_ns": 5}},
                },
            }
            config = td / "protocol.json"
            config.write_text(json.dumps(cfg))
            resolved = td / "resolved.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "protocol_resolver.py"),
                    "--input",
                    str(config),
                    "--out",
                    str(resolved),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0)
            data = json.loads(resolved.read_text())
            self.assertEqual(data["resolved"]["temperature_K"], 310.0)
            self.assertEqual(data["resolved"]["thermostat"]["name"], "v-rescale")
            self.assertEqual(data["resolved"]["barostat"]["name"], "Berendsen")
            self.assertEqual(data["resolved"]["electrostatics"]["coulombtype"], "Ewald")
            self.assertIn("stages.npt.minimum_ns", data["DEFAULT_FILLED"])
            selected = td / "resp1.json"
            self.assertEqual(
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "charge_method_selector.py"),
                        "--method",
                        "RESP1",
                        "--out",
                        str(selected),
                    ]
                ).returncode,
                0,
            )
            self.assertEqual(
                json.loads(selected.read_text())["selected_method"], "RESP1"
            )
            undecided = td / "undecided.json"
            self.assertNotEqual(
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "charge_method_selector.py"),
                        "--out",
                        str(undecided),
                    ]
                ).returncode,
                0,
            )

    def test_literature_mdp_and_gaussian_qm_mapping(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            cfg = {
                "protocol": {"mode": "reference_guided"},
                "literature_protocol": {
                    "source": "qm test",
                    "temperature_K": 310.0,
                    "pressure_bar": 1.2,
                    "qm": {
                        "method": "B3LYP",
                        "basis": "6-31G(d)",
                        "functional": "B3LYP",
                        "dispersion": "none",
                        "solvent_model": "gas",
                        "route_options": ["SCF=Tight"],
                    },
                    "stages": {
                        "em": {"emtol": 10, "max_steps": 123},
                        "nvt_anneal": {"duration_ps": 10},
                        "production": {"duration_ns": 5},
                    },
                },
                "geometry": "H 0 0 0\nH 0 0 0.74",
                "charge": 0,
                "multiplicity": 1,
            }
            config = td / "protocol_qm.json"
            config.write_text(json.dumps(cfg))
            resolved = td / "resolved_qm.json"
            self.assertEqual(
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "protocol_resolver.py"),
                        "--input",
                        str(config),
                        "--out",
                        str(resolved),
                    ]
                ).returncode,
                0,
            )
            mdp_dir = td / "mdp"
            self.assertEqual(
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "mdp_builder.py"),
                        "--resolved-protocol",
                        str(resolved),
                        "--out-dir",
                        str(mdp_dir),
                    ]
                ).returncode,
                0,
            )
            self.assertIn("emtol = 10", (mdp_dir / "em.mdp").read_text())
            self.assertIn("nsteps = 123", (mdp_dir / "em.mdp").read_text())
            self.assertIn("ref-t = 310.0", (mdp_dir / "production.mdp").read_text())
            self.assertIn("ref-p = 1.2", (mdp_dir / "npt.mdp").read_text())
            self.assertIn("nsteps = 2500000", (mdp_dir / "production.mdp").read_text())
            resolved_mdp = json.loads((mdp_dir / "resolved_protocol.json").read_text())
            self.assertEqual(resolved_mdp["field_sources"]["em_emtol"], "literature_or_user")
            self.assertEqual(resolved_mdp["field_sources"]["production_steps"], "literature_or_user")
            gaussian_dir = td / "gaussian"
            self.assertEqual(
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "gaussian_builder.py"),
                        "--config",
                        str(config),
                        "--resolved-protocol",
                        str(resolved),
                        "--out-dir",
                        str(gaussian_dir),
                    ]
                ).returncode,
                0,
            )
            plan = json.loads((gaussian_dir / "gaussian_plan.json").read_text())
            self.assertEqual(plan["status"], "PASS")
            self.assertIn("B3LYP/6-31G(d)", plan["route"])
            self.assertIn("SCF=Tight", plan["route"])
            self.assertIn("B3LYP/6-31G(d)", (gaussian_dir / "job.gjf").read_text())

    def test_backend_selection_and_structure_formats(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            cfg = {
                "execution": {
                    "backend": "hybrid_gaussian_local_gromacs_remote",
                    "gromacs_target": "ssh_remote",
                    "gaussian_target": "local_windows",
                    "remote": {
                        "host": "example.invalid",
                        "username": "tester",
                        "private_key_path": str(td / "missing_key"),
                        "remote_project_root": "/srv/gromacs-electrolyte-workflow",
                    },
                }
            }
            config = td / "backend.json"
            config.write_text(json.dumps(cfg))
            backend_out = td / "backend.json.out"
            backend_proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "backend_preflight.py"),
                    "--config",
                    str(config),
                    "--out",
                    str(backend_out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(backend_proc.returncode, 0)
            backend = json.loads(backend_out.read_text())
            self.assertEqual(backend["status"], "REMOTE_CONFIG_INCOMPLETE")
            self.assertFalse(backend["private_key_contents_read"])
            undecided = td / "undecided_backend.json"
            self.assertEqual(
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "backend_preflight.py"),
                        "--out",
                        str(undecided),
                    ],
                    capture_output=True,
                    text=True,
                ).returncode,
                0,
            )
            self.assertEqual(
                json.loads(undecided.read_text())["status"], "USER_DECISION_REQUIRED"
            )

            mol_atom = lambda symbol, x: (
                f"{x:10.4f}{0.0:10.4f}{0.0:10.4f} {symbol:<2}   0  0  0  0  0  0  0  0  0  0  0  0"
            )
            nl = chr(10)
            structures = {
                "water.xyz": nl.join(["2", "manual", "H 0 0 0", "H 0 0 0.74", ""]),
                "water.mol": nl.join(
                    [
                        "water",
                        "manual",
                        "",
                        "  2  1  0  0  0  0  0  0  0  0999 V2000",
                        mol_atom("H", 0.0),
                        mol_atom("H", 0.74),
                        "  1  2  1  0  0  0  0  0  0  0  0  0",
                        "M  END",
                        "",
                    ]
                ),
                "water.sdf": nl.join(
                    [
                        "water",
                        "manual",
                        "",
                        "  2  1  0  0  0  0  0  0  0  0999 V2000",
                        mol_atom("H", 0.0),
                        mol_atom("H", 0.74),
                        "  1  2  1  0  0  0  0  0  0  0  0  0",
                        "M  END",
                        "$$$$",
                        "",
                    ]
                ),
                "water.pdb": nl.join(
                    [
                        "ATOM      1  H   WAT A   1       0.000   0.000   0.000  1.00  0.00           H",
                        "ATOM      2  H   WAT A   1       0.740   0.000   0.000  1.00  0.00           H",
                        "END",
                        "",
                    ]
                ),
            }
            for name, text in structures.items():
                path = td / name
                path.write_text(text)
                out = td / (name + ".json")
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "structure_adapter.py"),
                        "--input",
                        str(path),
                        "--out",
                        str(out),
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(proc.returncode, 0, name)
                record = json.loads(out.read_text())
                self.assertEqual(record["status"], "PASS", name)
                self.assertEqual(record["atom_count"], 2, name)

            xyz = td / "water.xyz"
            adapter_out = td / "water_confirm.json"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "structure_adapter.py"),
                    "--input",
                    str(xyz),
                    "--out",
                    str(adapter_out),
                ],
                check=True,
            )
            adapter = json.loads(adapter_out.read_text())
            confirm = td / "confirmation.json"
            confirm.write_text(
                json.dumps(
                    {
                        "status": "CONFIRMED",
                        "source_sha256": adapter["source_sha256"],
                    }
                )
            )
            gaussian_cfg = td / "gaussian.json"
            gaussian_cfg.write_text(
                json.dumps(
                    {
                        "method": "B3LYP",
                        "basis": "6-31G(d)",
                        "charge": 0,
                        "multiplicity": 1,
                    }
                )
            )
            gaussian_out = td / "gaussian"
            self.assertEqual(
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "gaussian_builder.py"),
                        "--config",
                        str(gaussian_cfg),
                        "--structure",
                        str(xyz),
                        "--structure-confirmation",
                        str(confirm),
                        "--connectivity-approved",
                        "--out-dir",
                        str(gaussian_out),
                    ],
                    capture_output=True,
                    text=True,
                ).returncode,
                0,
            )
            self.assertEqual(
                json.loads((gaussian_out / "gaussian_plan.json").read_text())["status"],
                "PASS",
            )

    def test_checkpoint_and_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            cpt = td / "state.cpt"
            cpt.write_bytes(b"checkpoint")
            out = td / "cpt.json"
            self.assertEqual(
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "checkpoint_manager.py"),
                        "--checkpoint",
                        str(cpt),
                        "--out",
                        str(out),
                    ]
                ).returncode,
                0,
            )
            prov = td / "prov.json"
            self.assertEqual(
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "provenance.py"),
                        "--hash",
                        str(cpt),
                        "--out",
                        str(prov),
                    ]
                ).returncode,
                0,
            )
            self.assertEqual(json.loads(prov.read_text())[-1]["files"][str(cpt)], sha256(cpt))


if __name__ == "__main__":
    unittest.main()
