# gromacs-electrolyte-workflow

An Agent Skills-compatible electrolyte molecular dynamics workflow for auditable GROMACS modeling, staged equilibration, production simulation, and structural/diffusion analysis.

[English](#english) · [中文](#中文)

---

## English

### What this is

`gromacs-electrolyte-workflow` is an Agent Skills-compatible, gated, provenance-first bulk liquid electrolyte GROMACS workflow. It covers Li/Na salts, solvent/diluent mixtures, HCE/LHCE systems, additives, and related electrolyte simulations.

This is more than a collection of `.mdp` generators. Each important stage records input provenance, parameter status, file hashes, commands, return codes, and a gate verdict. An unresolved scientific input is a stop condition; the workflow does not guess.

### Capabilities

- WSL/Linux-first environment validation with `wsl_local`, `ssh_remote`, and `hybrid_gaussian_local_gromacs_remote` backends.
- Intake and hashing for molecular identity, structure files, formal charge, multiplicity, ratios, and molecule counts.
- Reproduction, reference-guided, default, and hybrid protocol resolution with `field_sources` and `DEFAULT_FILLED` tracking.
- RESP1/RESP2 selection and routing for Gaussian, implicit-solvent, Multiwfn/RESP, and multi-conformer workflows.
- Force-field audits, atom mapping, topology construction, static `grompp` gates, and Packmol box validation.
- Checkpoint-safe EM → NVT thermal history → NPT convergence → NVT transition → NVT production stages.
- Thermodynamic convergence, RDF/CN, solvation shells, SSIP/CIP/AGG structural proxies, ion-contact/cluster, MSD, and diffusion diagnostics.
- Methods text, stage reports, final verdicts, and provenance/hash manifests.

### Safety and scientific boundaries

- Never invent force-field, charge, Lennard-Jones, bonded, cross, 1–4, composition, box-size, or concentration parameters.
- Never use `grompp -maxwarn`; a warning that requires it is a failed gate.
- Never silently edit charges, topology, molecule counts, box geometry, timestep, coupling, or cutoffs.
- Remote mode stores only connection metadata and a private-key path; it does not read, copy, print, or hash private-key contents.
- Tests and skill installation do not start a new long formal MD calculation. Production execution is dry-run by default and requires an explicit confirmation file.
- RDF/CN, solvation, and SSIP/CIP/AGG results are structural diagnostics or proxies, not direct experimental species fractions. Diffusion requires PBC/COM checks and a data-supported fitting window.

### Install for a compatible agent

Keep the complete directory structure and copy it into a skills directory supported by the target agent. For Claude Code:

```text
<project>/.claude/skills/gromacs-electrolyte-workflow/     # Claude Code project scope
~/.claude/skills/gromacs-electrolyte-workflow/             # Claude Code personal scope
~/.codex/skills/gromacs-electrolyte-workflow/              # Codex or compatible scope
```

Other agents that support the Agent Skills format can use the same complete directory. Claude Code can invoke it as `/gromacs-electrolyte-workflow`; other agents use their native invocation or automatic description-based triggering. Keep `assets/`, `references/`, and `scripts/`; `agents/openai.yaml` is optional OpenAI/Codex UI metadata.

### Python and external dependencies

- Python 3.9 or newer is recommended.
- JSON input and most pure-Python checks use only the standard library.
- YAML configuration requires PyYAML:

```bash
python -m pip install -r requirements.txt
```

- Formal calculations require user-provided and validated WSL/Linux GROMACS, Packmol, and optionally Gaussian, formchk, Multiwfn, or a remote Linux environment. The repository does not silently run `sudo`, `apt`, or `pip` installation, and it does not connect to an unknown SSH host on the user's behalf.

### Repository self-check

These commands validate the repository and generate default MDPs only; they do not start a formal MD run:

```bash
python -m unittest discover -s tests -v
python -m compileall -q scripts
python scripts/mdp_builder.py --out-dir runs/mdp
```

Generated `runs/` content is local runtime output and is ignored by Git.

### Formal workflow entry points

1. Copy `assets/electrolyte.yaml` and fill in the system name, `system.execution_root`, backend, structure paths and SHA256 hashes, ratios/base count, formal charge/multiplicity, force-field/charge sources, and literature protocol. You may provide the control root with `--project-root` or `GROMACS_PROJECT_ROOT`. Do not leave `TODO` values.
2. Run `python scripts/environment_preflight.py --config <config> --out <preflight.json>`; for remote or hybrid mode, run the plan-only `scripts/backend_preflight.py` first.
3. Validate structures, identity, connectivity, and integer molecule counts with `structure_adapter.py`, `structure_validate.py`, and `composition_builder.py`.
4. Parse and resolve the protocol with `literature_protocol_parser.py` and `protocol_resolver.py`. Inspect `resolved_protocol.json`, `field_sources`, `DEFAULT_FILLED`, and `unresolved_required`.
5. After the user chooses RESP1 or RESP2, run the Gaussian/RESP route, force-field audit, topology construction, and atom mapping.
6. Pass the static topology/grompp gate before Packmol, then pass the actual-box grompp gate.
7. Generate MDP files and execute stages only after user confirmation and with complete checkpoint lineage; NPT extensions are decided by the convergence gate.
8. Generate thermodynamic, RDF/CN, solvation, aggregation, and MSD/diffusion diagnostics, then assemble the final verdict with the reporting scripts.

Inspect any script's arguments with:

```bash
python scripts/environment_preflight.py --help
python scripts/protocol_resolver.py --help
python scripts/mdp_builder.py --help
python scripts/gromacs_runner.py --help
python scripts/report_generator.py --help
```

### Default protocol summary

The default protocol is defined by `references/default_protocol.md`, `assets/simulation_protocol.yaml`, and `scripts/mdp_builder.py`; generated script output is authoritative:

| Stage | Default |
| --- | --- |
| Timestep/constraints | 0.002 ps only after validated hydrogen constraints; LINCS order 4, iter 1 |
| Non-bonded settings | PME, Verlet, periodic xyz |
| NVT anneal | 600 ps, 298.15 → 350 → 298.15 K |
| NPT | At least 5 ns; extend by 2 ns per convergence decision, up to 10 ns |
| NVT transition | 1 ns from a representative final NPT checkpoint/box |
| Production | 20 ns NVT; NPT production is not the default for diffusion analysis |
| Output | Compressed trajectory/energy every 2 ps, log every 10 ps, checkpoint every 15 min |

Literature or user-approved protocols may override fields only when they are explicitly reported with units and context. Missing fields are listed in `DEFAULT_FILLED` for reference-guided/hybrid modes and cause `PROTOCOL_UNRESOLVED` in reproduction mode.

### Repository layout

```text
SKILL.md                         # Agent Skills entrypoint metadata and core workflow
agents/openai.yaml               # Optional OpenAI/Codex UI metadata
assets/                          # Input templates, protocol, MDP, and report templates
references/                      # Force-field, RESP, GROMACS, remote, and analysis references
scripts/                         # Executable gates, builders, runners, and analysis tools
tests/test_skill.py              # Standard-library unittest regression suite
README.md                        # This bilingual README
requirements.txt                 # Optional YAML parsing dependency
```

### Data, credentials, and contributions

Do not commit private keys, `known_hosts`, raw experimental/structure data, Gaussian checkpoints, GROMACS trajectories, production outputs, caches, or sensitive local configuration. Read `CONTRIBUTING.md` first; when changing scientific rules, input fields, or output contracts, update `SKILL.md`, the relevant references/assets, and tests together.

This repository uses the MIT License. External papers, Multiwfn documentation, and other cited materials remain subject to their own copyright and usage terms.

---

## 中文

### 这是什么

`gromacs-electrolyte-workflow` 是一个“门禁优先、来源可追溯”的 bulk liquid electrolyte GROMACS 工作流，适用于 Li/Na 盐、电解质溶剂/稀释剂混合物、HCE/LHCE 和相关添加剂体系。

它不是一个只生成几份 `.mdp` 文件的脚本集合。工作流会在每个关键阶段记录输入来源、参数状态、文件哈希、命令、返回码和阶段结论；未解析的科学输入会触发停止，而不是由模型猜测。

### 主要功能

- WSL/Linux-first 环境门禁，以及 `wsl_local`、`ssh_remote`、`hybrid_gaussian_local_gromacs_remote` 后端选择。
- 分子身份、结构文件、形式电荷、多重度、摩尔比和分子数的 intake 与哈希记录。
- 文献复现、reference-guided、default 和 hybrid 协议解析；记录 `field_sources` 与 `DEFAULT_FILLED`。
- RESP1/RESP2 选择、Gaussian/隐式溶剂路线、Multiwfn/RESP 参考协议和多构象扩展的路由信息。
- 力场候选审计、原子映射、拓扑构建、静态 `grompp` 检查和 Packmol 盒子验证。
- EM → NVT 温度历史 → NPT 收敛 → NVT transition → NVT production 的 checkpoint-safe 阶段执行。
- 热力学收敛、RDF/CN、溶剂化壳层、SSIP/CIP/AGG 结构代理、离子接触/cluster、MSD 与扩散诊断。
- 方法部分、阶段报告、最终 verdict 和 provenance/hash 清单生成。

### 重要安全与科学边界

- 不猜测力场、RESP 电荷、Lennard-Jones、键参数、交叉项、1–4 规则、组成、盒子尺寸或浓度。
- 不使用 `grompp -maxwarn`；需要 `maxwarn` 才能继续时，门禁失败。
- 不静默修改电荷、拓扑、分子数、盒子、时间步长、温压耦合或截断参数。
- 远程模式只保存连接元数据和私钥路径，不读取、复制、打印或哈希私钥内容。
- 测试和 skill 安装不会启动新的长时间正式 MD；生产阶段默认 dry-run，并要求用户提供确认文件。
- RDF/CN、溶剂化和 SSIP/CIP/AGG 是结构诊断或代理指标，不等同于实验物种比例。扩散系数必须通过 PBC、COM 和数据支持的拟合窗口检查。

### 安装到兼容 Agent

保留整个目录结构，将本目录复制到目标 Agent 支持的 skills 目录。例如 Claude Code：

```text
<project>/.claude/skills/gromacs-electrolyte-workflow/     # Claude Code 项目级
~/.claude/skills/gromacs-electrolyte-workflow/             # Claude Code 全局
~/.codex/skills/gromacs-electrolyte-workflow/              # Codex 或兼容目录
```

其他 Agent 只要支持 Agent Skills 格式，也应将完整目录放在其 skills 目录中。Claude Code 可使用 `/gromacs-electrolyte-workflow` 调用；其他 Agent 使用各自的调用方式或根据 description 自动触发。不要只复制 `SKILL.md`；`assets/`、`references/` 和 `scripts/` 都是工作流的一部分，`agents/openai.yaml` 只是可选的 OpenAI/Codex UI 元数据。

### Python 与外部依赖

- 推荐 Python 3.9 或更高版本。
- JSON 输入和大部分纯 Python 校验只依赖标准库。
- YAML 配置需要 PyYAML：

```bash
python -m pip install -r requirements.txt
```

- 正式计算还需要用户自行准备并确认 WSL/Linux GROMACS、Packmol，以及可选的 Gaussian、formchk、Multiwfn 或远程 Linux 环境。仓库不会自动执行 `sudo`、`apt`、`pip` 安装，也不会替用户建立未知 SSH 连接。

### 仓库自检

这些命令只验证仓库脚本和默认 MDP 生成，不会启动正式 MD：

```bash
python -m unittest discover -s tests -v
python -m compileall -q scripts
python scripts/mdp_builder.py --out-dir runs/mdp
```

生成的 `runs/` 属于本地运行产物，已在 `.gitignore` 中排除。

### 正式工作流入口

1. 复制 `assets/electrolyte.yaml`，填写体系名称、`system.execution_root`、后端、分子结构路径与 SHA256、组分比例/基准分子数、形式电荷/多重度、力场/电荷来源和文献协议。也可以使用 `--project-root` 或 `GROMACS_PROJECT_ROOT` 提供控制根目录。不要保留 `TODO`。
2. 使用 `python scripts/environment_preflight.py --config <config> --out <preflight.json>` 运行环境门禁；远程或 hybrid 模式先运行 `scripts/backend_preflight.py` 的 plan-only 检查。
3. 用 `structure_adapter.py`、`structure_validate.py`、`composition_builder.py` 验证结构、身份、连通性和整数分子数。
4. 用 `literature_protocol_parser.py` 和 `protocol_resolver.py` 解析协议；检查 `resolved_protocol.json`、`field_sources`、`DEFAULT_FILLED` 和 `unresolved_required`。
5. 在用户确认 RESP1/RESP2 后，运行 Gaussian/RESP 路由、力场审计、拓扑构建和原子映射。
6. 先做静态 topology/grompp 门禁，再做 Packmol 和实际盒子 grompp 门禁。
7. 生成 MDP 后，只在用户确认且 checkpoint lineage 完整时执行阶段模拟；NPT 收敛门禁负责决定是否延长 NPT。
8. 用分析脚本生成热力学、RDF/CN、溶剂化、聚集和 MSD/扩散结果，再由报告脚本汇总最终 verdict。

常用脚本的参数可直接查看：

```bash
python scripts/environment_preflight.py --help
python scripts/protocol_resolver.py --help
python scripts/mdp_builder.py --help
python scripts/gromacs_runner.py --help
python scripts/report_generator.py --help
```

### 默认协议摘要

默认值由 `references/default_protocol.md`、`assets/simulation_protocol.yaml` 和 `scripts/mdp_builder.py` 共同定义，生成结果以脚本输出为准：

| 阶段 | 默认设置 |
| --- | --- |
| 时间步长/约束 | 0.002 ps；仅在氢约束已验证时使用；LINCS order 4、iter 1 |
| 非键相互作用 | PME、Verlet、周期边界 xyz |
| NVT anneal | 600 ps，298.15 → 350 → 298.15 K |
| NPT | 至少 5 ns；按收敛门禁每次延长 2 ns，最多 10 ns |
| NVT transition | 1 ns，来自有代表性的最终 NPT checkpoint/盒子 |
| production | 20 ns NVT；默认不使用 NPT production 做扩散分析 |
| 输出 | 压缩轨迹/能量每 2 ps，日志每 10 ps，checkpoint 每 15 min |

文学协议或用户批准的协议可以覆盖已明确报告、带单位且有上下文的字段；缺失字段在 reference-guided/hybrid 模式中会列入 `DEFAULT_FILLED`，在 reproduction 模式中会导致 `PROTOCOL_UNRESOLVED`。

### 目录结构

```text
SKILL.md                         # Agent Skills 入口元数据和核心工作流
agents/openai.yaml               # 可选的 OpenAI/Codex UI 元数据
assets/                          # 输入模板、默认协议、MDP 和报告模板
references/                      # 力场、RESP、GROMACS、远程和分析参考
scripts/                         # 可执行的门禁、构建、运行和分析脚本
tests/test_skill.py              # 标准库 unittest 回归测试
README.md                        # 本双语说明
requirements.txt                 # YAML 解析的可选运行依赖
```

### 数据、凭据和贡献

不要提交私钥、`known_hosts`、原始实验/结构数据、Gaussian checkpoint、GROMACS 轨迹、生产输出、缓存或含敏感信息的本地配置。请先阅读 `CONTRIBUTING.md`，并在修改科学规则、输入字段或输出契约时同步更新 `SKILL.md`、相关 reference、assets 和 tests。

本仓库采用 MIT License；外部论文、Multiwfn 文档和其他引用资料仍受其各自的版权和使用条款约束。
