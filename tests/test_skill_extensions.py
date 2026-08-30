import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_task_router_maps_combined_chinese_request():
    from task_router import route_task

    result = route_task("\u4f18\u5316\u7ed3\u6784\u540e\u8ba1\u7b97\u80fd\u5e26\u3001DOS\u3001ELF\u548c\u5468\u671f\u7535\u8377")
    assert result["status"] == "ROUTED"
    assert {"geo_opt", "band", "dos", "elf", "periodic_charge"}.issubset(
        set(result["workflows"])
    )
    assert "reference_scf" in result["prerequisites"]


def test_calculation_manifest_preserves_structure_hash(tmp_path):
    from calculation_init import build_manifest

    structure = tmp_path / "x.xyz"
    structure.write_text("1\nH\nH 0 0 0\n", encoding="utf-8")
    manifest = build_manifest(structure, "single point", "LOCAL", {})
    assert manifest["structure"]["sha256"]
    assert manifest["decision_status"] == "READY_FOR_PARAMETER_PLAN"


def test_manual_cache_rejects_non_official_url():
    from manual_cache import safe_section_path, validate_manual_url

    assert validate_manual_url("https://manual.cp2k.org/cp2k-2024_1-branch/CP2K_INPUT.html")
    assert not validate_manual_url("https://example.com/CP2K_INPUT.html")
    assert safe_section_path("CP2K_INPUT/FORCE_EVAL.html") == "CP2K_INPUT/FORCE_EVAL.html"
    with pytest.raises(ValueError):
        safe_section_path("../outside.html")


def test_ssh_command_requires_strict_known_hosts(tmp_path):
    from remote_ssh import build_ssh_command, validate_ssh_inputs

    key = tmp_path / "id_ed25519"
    key.write_text("placeholder", encoding="utf-8")
    with pytest.raises(ValueError, match="known_hosts"):
        validate_ssh_inputs("host", "user", key, 22, None)
    known = tmp_path / "known_hosts"
    known.write_text("host ssh-ed25519 AAAA\n", encoding="utf-8")
    command = build_ssh_command("host", "user", key, 22, known, ["hostname"])
    assert "StrictHostKeyChecking=yes" in command
    assert "BatchMode=yes" in command


def test_literature_profile_extracts_observations_and_requires_choice(tmp_path):
    from literature_profile import build_literature_plan

    reference = tmp_path / "paper.txt"
    reference.write_text("We used a 3x3x3 k-point mesh, cutoff 500 Ry and EPS_SCF 1e-7.", encoding="utf-8")
    plan = build_literature_plan([reference], "band", "accuracy")
    assert plan["observations"]
    assert plan["status"] == "USER_CONFIRMATION_REQUIRED"
    assert plan["candidates"]["HIGH_PRECISION"]["priority"] == "accuracy"


def test_parameter_gate_requires_explicit_confirmation(tmp_path):
    from parameter_gate import approve_plan

    plan = {"status": "USER_CONFIRMATION_REQUIRED", "candidates": {"BALANCED": {"x": 1}}}
    with pytest.raises(ValueError, match="confirmation"):
        approve_plan(plan, "BALANCED", False)
    approved = approve_plan(plan, "BALANCED", True)
    assert approved["approved"] is True

    literature_like = {
        "status": "USER_CONFIRMATION_REQUIRED",
        "candidates": {"BALANCED": {"unresolved_values": ["cutoff"]}},
    }
    approved = approve_plan(literature_like, "BALANCED", True, {"cutoff": 500})
    assert approved["candidate"]["unresolved_values"] == []


def test_output_parser_requires_normal_termination(tmp_path):
    from cp2k_output_parser import parse_output

    output = """CP2K version 2024.1\nSCF run converged\nENERGY| Total FORCE_EVAL ( QS ) energy [a.u.] : -12.5\nGEOMETRY OPTIMIZATION COMPLETED\nPROGRAM STOPPED IN\n"""
    result = parse_output(output, return_code=0)
    assert result["status"] == "PASS"
    assert result["total_energy_au"] == -12.5
    assert result["geometry_completed"] is True


def test_convergence_plan_is_property_specific():
    from convergence_manager import build_convergence_plan

    plan = build_convergence_plan("charge_density_difference", "cost")
    assert "cube_grid" in plan["metrics"]
    assert "total_energy" not in plan["metrics"]
    assert plan["requires_user_confirmation"] is True


def test_charge_plan_keeps_methods_separate():
    from charge_workflow import build_charge_plan

    plan = build_charge_plan(["hirshfeld", "periodic_resp", "repeat_like"])
    assert plan["methods"] == ["hirshfeld", "periodic_resp", "repeat_like"]
    assert plan["gromacs_status"] == "GROMACS_CHARGE_CANDIDATE_ONLY"
    assert plan["recommended_method"] is None


def test_structured_builder_round_trip_and_conditional_section():
    from input_builder import CP2KInput, Section

    root = CP2KInput()
    global_section = root.add_section("GLOBAL")
    global_section.add_keyword("RUN_TYPE", "ENERGY")
    force = root.add_section("FORCE_EVAL")
    force.add_section("DFT").add_keyword("CHARGE", 0)
    force.add_section("DISABLED", enabled=False)
    text = root.render()
    assert "&GLOBAL" in text and "RUN_TYPE ENERGY" in text
    assert "&DISABLED" not in text
    parsed = CP2KInput.parse(text)
    assert parsed.find("GLOBAL").keywords[0][0] == "RUN_TYPE"


def test_public_template_registry_resolves_packaged_path():
    sys.path.insert(0, str(ROOT / "assets"))
    from library.template_registry import get_template, render_template

    template = get_template("2024.1", "single_point")
    assert template == ROOT / "assets" / "templates_2024" / "single_point.inp.template"
    values = json.loads((ROOT / "assets" / "values.example.json").read_text(encoding="utf-8"))
    rendered = render_template("2024.1", "single_point", values)
    assert "{{" not in rendered


def test_2024_linter_distinguishes_sibling_and_nested_pdos():
    from input_lint import lint_text

    sibling = """&GLOBAL\n&END GLOBAL\n&FORCE_EVAL\n  &DFT\n    &PRINT\n      &DOS\n      &END DOS\n      &PDOS\n        NLUMO 4\n      &END PDOS\n    &END PRINT\n  &END DFT\n  &SUBSYS\n  &END SUBSYS\n&END FORCE_EVAL\n"""
    nested = sibling.replace("      &PDOS", "        &PDOS").replace("      &END PDOS", "        &END PDOS").replace("      &END DOS", "        &END DOS")
    assert lint_text(sibling, "2024.1")["valid"]
    assert any("nested DOS/PDOS" in error for error in lint_text(nested, "2024.1")["errors"])


def test_adsorption_bookkeeping_reports_electron_volts():
    from compute_adsorption_energy import compute_adsorption_energy

    result = compute_adsorption_energy(-10.0, -7.0, -2.0)
    assert result["status"] == "PASS"
    assert result["adsorption_energy_hartree"] == -1.0
    assert result["adsorption_energy_ev"] < 0


def test_cube_subtraction_rejects_mismatched_grid(tmp_path):
    from subtract_cube_density import audit_cubes, read_cube

    def write_cube(path, x_count):
        path.write_text(
            "comment one\ncomment two\n"
            f"1 0.0 0.0 0.0\n{x_count} 1.0 0.0 0.0\n1 0.0 1.0 0.0\n1 0.0 0.0 1.0\n"
            "1 0.0 0.0 0.0\n"
            + " ".join("1.0" for _ in range(x_count))
            + "\n",
            encoding="utf-8",
        )

    first = tmp_path / "first.cube"
    second = tmp_path / "second.cube"
    write_cube(first, 2)
    write_cube(second, 3)
    result = audit_cubes((read_cube(first), read_cube(second)))
    assert result["status"] == "FAIL"
    assert any("grid dimensions" in item for item in result["mismatches"])
