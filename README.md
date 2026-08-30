# CP2K Materials Workflow

Agent-neutral, version-aware automation guidance and helper scripts for
CP2K-based density functional theory calculations.

Suggested GitHub short description:

> Agent-neutral CP2K workflows that generate, validate, run, and audit version-matched density functional theory calculations.

## English

### What this repository actually does

This repository is a reusable Skill package for Codex, Claude Code, and other
agents that can read Markdown and execute local commands. It is not CP2K
itself, and it does not contain a hidden density functional theory engine.

The important execution model is:

1. The agent reads SKILL.md and the relevant reference files.
2. The agent calls the bundled Python helpers to inspect the request,
   structure, environment, and calculation choices.
3. The agent renders a native CP2K input file from a version-specific
   template.
4. The helper script launches the external CP2K executable.
5. CP2K performs the actual density functional theory calculation.
6. The helper scripts parse CP2K output, validate expected artifacts, run
   property-specific bookkeeping, and write provenance.

The Skill therefore orchestrates and audits CP2K. It does not replace CP2K,
choose a universally correct physical model, install a cluster, or guarantee
that a syntactically valid input is scientifically valid.

### The complete call chain

The following diagram shows the normal path from a user request to a CP2K
calculation. A real task may stop at any gate when information or approval is
missing.

~~~mermaid
flowchart TD
    A["User request and structure"] --> B["task_router.py"]
    B --> C["environment_audit.py"]
    C --> D["cp2k_version_detect.py"]
    D --> E["manual_resolver.py or manual_cache.py"]
    E --> F["structure_audit.py"]
    F --> G["calculation_init.py"]
    G --> H["Scientific choices and parameter gate"]
    H --> I["template_registry.json"]
    I --> J["render_versioned_template.py"]
    J --> K["input_lint.py"]
    K --> L{"Run target"}
    L -->|LOCAL| M["run_cp2k.py"]
    L -->|REMOTE_SERVER| N["remote_ssh.py preflight"]
    N --> O["scheduler_remote.py"]
    M --> P["External CP2K executable"]
    O --> P
    P --> Q["CP2K output, restart, and property files"]
    Q --> R["cp2k_output_parser.py"]
    R --> S["Property postprocessing"]
    S --> T["provenance.py and final report"]
~~~

There is no generic call such as run_dft() in the package. The concrete local
call made by run_cp2k.py is equivalent to:

~~~text
[cp2k_executable, "-i", "/absolute/path/to/input.inp", "-o", "/absolute/path/to/output.out"]
~~~

The CP2K executable reads the input file and writes its output file. The
Python runner performs the version probe, starts that process, captures the
process streams, and evaluates the result after CP2K exits.

### What happens at every stage

| Stage | Helper or artifact | What the agent checks | Blocking examples |
| --- | --- | --- | --- |
| Request routing | scripts/task_router.py | Maps natural language to a finite workflow such as geo_opt, band, dos, elf_density, charge_population, or single_point. | Unsupported or ambiguous task |
| Environment | scripts/environment_audit.py and scripts/scheduler_detect.py | Finds Python, CPU, memory, GPU, MPI, CP2K candidates, and scheduler commands without submitting anything. | CP2K executable not found |
| Version | scripts/cp2k_version_detect.py | Probes the selected executable and records the exact CP2K version. | Version cannot be parsed or does not match the requested branch |
| Manual | scripts/manual_resolver.py and scripts/manual_cache.py | Resolves the exact official CP2K manual branch and hashes downloaded evidence. | MANUAL_REQUIRED |
| Structure | scripts/structure_audit.py and scripts/structure_audit_full.py | Checks file readability, formula, cell, periodicity, short contacts, disorder, occupancy, and symmetry when optional libraries are available. | Invalid structure or unresolved disorder |
| Scientific model | calculation manifest, literature profile, parameter gate, convergence plan | Records charge, spin, functional, dispersion, basis, potential, cutoff, k points, cell, slab, and convergence decisions with sources. | SCIENTIFIC_DECISION_REQUIRED |
| Input generation | assets/template_registry.json and scripts/render_versioned_template.py | Selects a version-matched template and fills every explicit slot. | Missing value, unknown workflow, or wrong version family |
| Input validation | scripts/input_lint.py | Checks unresolved tokens, required CP2K sections, known version-specific layout rules, and forbidden unsafe settings. | Unresolved token or invalid version-specific structure |
| Execution approval | scripts/run_cp2k.py or scripts/scheduler_remote.py | Requires an explicit local run flag or remote submission approval. | USER_CONFIRMATION_REQUIRED |
| CP2K run | external CP2K binary | Performs the actual electronic-structure calculation. | Nonzero exit, timeout, missing output |
| Output validation | scripts/cp2k_output_parser.py | Looks for normal termination, SCF convergence, finite energy, geometry evidence, errors, and warnings. | FAIL even when an output file exists |
| Property checks | adsorption, cube, charge, and convergence helpers | Computes only the requested derived quantity after comparable inputs and grids are proven. | Incompatible reference settings or cube grids |
| Provenance | scripts/provenance.py | Records hashes, environment, executable information, commands, and calculation metadata. | Missing evidence or incomplete record |

### A complete local calculation

The following is a concrete example for a geometry optimization. Replace the
structure path, executable path, version, and scientific values with values
that apply to the actual system. Unix users can use python3; Windows users
can use python. The commands are intentionally written as one line so that
they can be translated by different agent hosts.

#### 1. Start with a clean calculation directory

~~~text
python scripts/self_check.py
python scripts/task_router.py --task "geometry optimization"
python scripts/environment_audit.py --output calculation/environment.json
python scripts/cp2k_version_detect.py --executable /absolute/path/to/cp2k.psmp
~~~

The environment audit is read-only. Version detection does not install CP2K.
On Windows, an executable might look like
C:/CP2K/bin/cp2k.psmp.exe.

#### 2. Resolve the exact CP2K manual

The Skill keeps syntax branches separate. For CP2K 2024.1:

~~~text
python scripts/manual_resolver.py --version 2024.1 --sections FORCE_EVAL/DFT/SCF --cache-root calculation/manual_cache
~~~

If the required manual evidence is not already in the runtime cache, the
resolver returns MANUAL_REQUIRED. When network access is allowed, retrieve
only the official allowlisted manual:

~~~text
python scripts/manual_cache.py --version 2024.1 --cache-root calculation/manual_cache
python scripts/manual_resolver.py --version 2024.1 --sections FORCE_EVAL/DFT/SCF --cache-root calculation/manual_cache
~~~

The manual cache is runtime evidence and should normally stay outside the
public Skill package. The package does not silently substitute a different
CP2K version when the requested manual is absent.

#### 3. Audit the structure without changing it

~~~text
python scripts/structure_audit.py input_structure/source.cif --output calculation/structure-audit.json
python scripts/structure_audit_full.py input_structure/source.cif --output calculation/structure-audit-full.json
~~~

The full audit uses optional libraries when available. The scripts do not
rewrite coordinates, guess a supercell, remove atoms, or silently repair
short contacts. Any correction must be a separate, reviewable input artifact.

#### 4. Record the calculation and scientific decisions

The agent creates a choices JSON after resolving the scientific questions. A
minimal illustrative file might contain:

~~~json
{
  "charge": 0,
  "charge_source": "USER_SPECIFIED",
  "multiplicity": 1,
  "functional": "EXPLICITLY_CONFIRMED",
  "dispersion": "EXPLICITLY_CONFIRMED",
  "basis_source": "EXPLICITLY_CONFIRMED",
  "potential_source": "EXPLICITLY_CONFIRMED"
}
~~~

The field values above are labels for a decision record, not universal
recommendations. The actual choice must be appropriate for the material.
Create the calculation manifest with:

~~~text
python scripts/calculation_init.py --structure input_structure/source.cif --task "geometry optimization" --run-target LOCAL --choices-json calculation/choices.json --output-dir calculation
~~~

For literature-guided work, the agent may first create an observation record:

~~~text
python scripts/literature_profile.py --reference paper.pdf --workflow geo_opt --output calculation/literature-profile.json
~~~

This extracts reported observations and candidate profiles. It does not
silently copy a paper's parameters into the calculation. The convergence
manager then creates a property-specific plan; thresholds still require
scientific confirmation:

~~~text
python scripts/convergence_manager.py --workflow geo_opt --priority balanced --output calculation/convergence-plan.json
~~~

#### 5. Build the CP2K input from a versioned template

The agent prepares calculation/values.json from the structure and the
approved decisions. It contains concrete values for the template slots, such
as:

- project name and run type;
- cell and coordinate blocks;
- KIND sections;
- basis-set and potential filenames;
- total charge and spin settings;
- plane-wave cutoff and relative cutoff;
- SCF method, convergence target, mixing, and iteration limits;
- geometry-optimization thresholds;
- k-point or band-path blocks;
- property-specific print sections.

Render the input:

~~~text
python scripts/render_versioned_template.py --version 2024.1 --workflow geo_opt --values-json calculation/values.json --output calculation/inputs/geo_opt.inp
~~~

The renderer selects the template path from assets/template_registry.json,
replaces explicit tokens such as {{PROJECT}} and {{COORD_BLOCK}}, refuses
missing values, and lints the result before writing it. The example file
assets/values.example.json is only a placeholder fixture; it is not a
production material model.

The generated file is a native CP2K input. For example, the structure of a
generated input contains blocks like:

~~~text
&GLOBAL
  PROJECT example_geo_opt
  RUN_TYPE GEO_OPT
&END GLOBAL
&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
    POTENTIAL_FILE_NAME GTH_POTENTIALS
    ...
  &END DFT
  &SUBSYS
    ...
  &END SUBSYS
&END FORCE_EVAL
~~~

This fragment is illustrative and is not a runnable scientific input by
itself. The actual input must contain valid coordinates, KIND definitions,
basis/potential mappings, and all model-specific settings.

#### 6. Validate before starting CP2K

~~~text
python scripts/input_lint.py calculation/inputs/geo_opt.inp --version 2024.1
~~~

The internal linter catches structural mistakes that can be checked without
CP2K. If a site provides an external CP2K input validator, the agent may run
it as an additional gate. Static lint is not a substitute for CP2K execution
or scientific review.

#### 7. Launch the actual CP2K process

~~~text
python scripts/run_cp2k.py --executable /absolute/path/to/cp2k.psmp --input calculation/inputs/geo_opt.inp --output calculation/outputs/geo_opt.out --expected-version 2024.1 --workdir calculation --allow-run
~~~

Internally, the runner performs the following actions:

1. It refuses to run unless --allow-run is present.
2. It probes the executable with --version and then -v if needed.
3. It compares the detected version with --expected-version when supplied.
4. It constructs the command
   [executable, "-i", absolute_input, "-o", absolute_output].
5. It starts the process with Python subprocess.run, using the calculation
   directory as the working directory unless another one is supplied.
6. It captures stdout and stderr, does not retry, and never edits the input.
7. It reads the CP2K output and applies the output parser.

The runner returns PASS only when the output parser finds sufficient evidence
of a successful CP2K calculation. A created output file alone is not PASS.
For a separate parse or a previously completed job:

~~~text
python scripts/cp2k_output_parser.py calculation/outputs/geo_opt.out --return-code 0 --json-output calculation/outputs/geo_opt.parse.json
~~~

#### 8. Record provenance and inspect results

~~~text
python scripts/provenance.py --output calculation/provenance/manifest.yaml --structure input_structure/source.cif --input calculation/inputs/geo_opt.inp --cp2k-executable /absolute/path/to/cp2k.psmp --command "cp2k.psmp -i /absolute/path/to/geo_opt.inp -o /absolute/path/to/geo_opt.out"
~~~

The provenance file is JSON formatted but valid YAML 1.2. It records hashes
of the structure and input, the machine, Python version, CP2K version probe,
command text, and a policy stating that credentials are not collected.

### How a request becomes one or more CP2K jobs

Many scientific properties are not one single CP2K invocation. The agent
uses the same render, lint, run, parse, and provenance loop for every job in
the plan.

| User request | Typical CP2K job plan | Final operation |
| --- | --- | --- |
| Single-point energy | One ENERGY or appropriate single-point input | Parse the converged energy |
| Geometry optimization | GEO_OPT input, followed by inspection of the final structure | Parse geometry completion and final energy |
| Band structure | Reference SCF calculation plus a band-path calculation when required by the model | Check the reference state, path, and band artifacts |
| Density of states or projected density of states | Reference electronic state plus a version-correct DOS or PDOS print section, often with virtual states | Check DOS/PDOS files and settings |
| Electron density or electron localization function | CP2K density-print job that writes volumetric files | Validate finite data and grid artifacts |
| Adsorption energy | Separate comparable calculations for complex, host, and adsorbate | Run E_ads = E_complex - E_host - E_adsorbate |
| Charge-density difference | Comparable complex, host, and adsorbate density calculations in one grid frame | Run rho_difference = rho_complex - rho_host - rho_adsorbate |
| Work function | Slab calculation with an explicit vacuum and electrostatic-potential output | Perform a vacuum-referenced planar analysis |
| Periodic charge | A method-specific periodic charge workflow | Keep the chosen charge method separate from molecular charge methods |

The helper scripts perform the deterministic final operations. They do not
claim that two energies are comparable merely because subtraction is
possible. For adsorption energy, the functional, dispersion treatment,
basis, potential, cutoff, relative cutoff, charge, spin, k points, and
geometry policy must be compatible. For density subtraction, the cube parser
checks atom frames, grid dimensions, origins, grid vectors, finite values,
and data counts before subtraction.

### Version selection is part of execution, not documentation

The public package contains exact registry entries for CP2K 2024.1 and
2026.2. An agent must not mix their templates, manuals, or restart files.

| Area | CP2K 2024.1 branch | CP2K 2026.2 branch |
| --- | --- | --- |
| Manual | Official 2024.1 manual evidence | Official 2026.2 manual evidence |
| Template family | assets/templates_2024 | assets/templates_2026 |
| DOS/PDOS layout | Legacy sibling PRINT/DOS and PRINT/PDOS structure | Recorded nested PRINT/DOS/CURVE/PDOS structure |
| Input lint rules | 2024.x-specific section rules | 2026.x-specific section rules |
| Restart policy | Reuse only with the same compatible version/build | Reuse only with the same compatible version/build |

If the installed CP2K version is not one of the versioned branches with
adequate evidence, the safe result is a review request or manual adaptation,
not an automatic fallback to the nearest template.

### Remote server and scheduler execution

The local runner launches CP2K on the machine where the script runs. For a
remote server, run the preflight and scheduler path instead:

~~~text
python scripts/remote_ssh.py --host server.example.org --user your_username --key C:/secure/id_ed25519 --known-hosts C:/secure/known_hosts --remote-dir /data/project/cp2k/job-001 --command hostname
~~~

The remote helper requires a real private-key file and a non-empty verified
known_hosts file. It uses strict host-key checking, does not accept a new
host key automatically, and does not print key contents.

The remote flow is:

1. Render and lint the input locally.
2. Create the scheduler script from assets/slurm/job.slurm.template,
   assets/pbs/job.pbs.template, or assets/local/run.sh.template.
3. Fill the explicit scheduler slots, especially RUN_COMMAND, with the
   site-approved CP2K command. A typical command inside a batch job is
   cp2k.psmp -i geo_opt.inp -o geo_opt.out, possibly wrapped by the site's
   MPI launcher.
4. Stage the input, values, scheduler script, basis files, potential files,
   and any required restart files into the remote working directory.
5. Build a read-only scheduler status command and run it through the approved
   remote access path.
6. Show the final job script and request approval before submission.
7. Submit only through the explicit approval boundary.
8. Retrieve and parse the output, then write provenance.

This repository does not include a general-purpose file-transfer uploader.
The host or agent must use the site's permitted transfer mechanism and must
not guess remote paths. The remote scheduler helper can produce status and
submission commands:

~~~text
python scripts/scheduler_remote.py --scheduler slurm --action status --job-id 12345
python scripts/scheduler_remote.py --scheduler slurm --action submit --job-script calculation/job.slurm
~~~

The scheduler helper builds commands; it does not silently submit or monitor a
remote job for you. The second command intentionally returns a
confirmation-required state until the explicit submission flag is supplied
after user approval. Do not run a batch job directly on a login node unless
the site policy explicitly allows it.

### Scientific decisions the Skill will not invent

The workflow is designed to stop when a missing choice can change the
meaning of the result. The user or a qualified researcher must resolve, with
an appropriate source:

- total charge, multiplicity, spin treatment, and magnetic ordering;
- exchange-correlation functional and dispersion model;
- basis sets, pseudopotentials, relativistic treatment, and auxiliary data;
- DFT+U element, orbital, U, J, and source;
- partial occupancy and metallic smearing;
- periodic countercharge or charged-cell treatment;
- cell, k-point sampling, cutoff, and convergence targets;
- slab orientation, termination, thickness, vacuum, and dipole correction;
- adsorption reference state, geometry policy, and adsorbate charge;
- NEB endpoint atom mapping and intermediate definition;
- the intended charge analysis method.

The agent can prepare alternatives, show their assumptions, and create a
convergence plan. It must not choose a value merely because it makes CP2K
start successfully.

### Status meanings

Important statuses are evidence states, not marketing labels:

- MANUAL_REQUIRED: the exact manual branch has not been resolved.
- SCIENTIFIC_DECISION_REQUIRED: a physical model choice is missing.
- USER_CONFIRMATION_REQUIRED: an external execution or submission needs
  approval.
- VERSION_UNRESOLVED: the executable could not be identified.
- VERSION_MISMATCH: the executable version differs from the requested branch.
- CONFIGURATION_ERROR: a path, input, credential, or command boundary is
  invalid.
- PASS: CP2K output passed the implemented parser and artifact checks.
- FAIL: the process or parsed scientific artifact did not pass.
- NOT_VALIDATED: the public package has no evidence for a specific cluster or
  capability.

The registry's public capability entries intentionally start as
NOT_VALIDATED. A template existing in the repository is not evidence that a
calculation has been executed successfully on every cluster.

### Dependencies and installation

The core orchestration scripts use the Python standard library. CP2K,
MPI, scheduler commands, basis files, and potential files are external
dependencies and are not installed by this repository.

Optional structure, environment, and literature support:

~~~text
python -m pip install -r requirements-optional.txt
~~~

Development tests:

~~~text
python -m pip install -r requirements-dev.txt
python -m pytest
~~~

An agent should not install packages or download a CP2K binary without the
user's permission and a suitable environment. The bundled example values and
templates are safe fixtures for linting and contract tests, not production
settings.

### Using the Skill with different agents

The portable contract is SKILL.md. For Codex, Claude Code, or another agent:

1. Make the complete cp2k-materials-workflow folder available to the agent.
2. Tell the agent to read SKILL.md before acting.
3. Give it the absolute path to the input structure and the desired
   calculation.
4. Tell it whether the target is LOCAL or REMOTE_SERVER.
5. Require it to show the rendered input, detected CP2K version, planned
   command, and unresolved scientific decisions before execution.

An agent with a native Skill directory may copy the complete folder into that
directory. An agent without a Skill loader can read SKILL.md directly and
invoke the scripts by absolute path. No hook, plugin, slash command, or
vendor-specific API is required. agents/openai.yaml is optional host
metadata; it is not a runtime dependency.

Example instruction:

~~~text
Use the CP2K Materials Workflow at /absolute/path/to/cp2k-materials-workflow.
Read SKILL.md first. Audit my structure and CP2K environment, identify the
exact version, resolve the matching manual, record all scientific choices,
render and lint the CP2K input, and stop before local execution or remote
submission until I approve the displayed command and input. After execution,
parse the output and write provenance.
~~~

### Repository layout

~~~text
SKILL.md                         agent-neutral operating protocol
agents/openai.yaml               optional host metadata
scripts/                         routing, audits, rendering, running, and parsing
references/                      detailed scientific and operational guidance
assets/templates_2024/           CP2K 2024.1 skeletons
assets/templates_2026/           CP2K 2026.2 skeletons
assets/template_registry.json    version and capability registry
assets/*.example.*               safe local, remote, and parameter examples
tests/                            unit and contract tests
~~~

See CONTRIBUTING.md for repository changes and
THIRD_PARTY_ATTRIBUTION.md for bundled-resource attribution.

## 中文

### 这个仓库实际做什么

这是一个可以给 Codex、Claude Code 以及其他 Agent 使用的、与厂商无关的
CP2K 材料计算 Skill。它不是 CP2K 程序，也不包含一个隐藏的密度泛函理论
计算引擎。

它的实际执行模型是：

1. Agent 先读取 SKILL.md 和当前任务需要的参考文档。
2. Agent 调用仓库中的 Python 辅助脚本，检查任务、结构、环境和计算选择。
3. Agent 根据 CP2K 版本模板生成原生 CP2K 输入文件。
4. 辅助脚本启动外部 CP2K 可执行文件。
5. 真正的密度泛函理论计算由 CP2K 完成。
6. 辅助脚本解析 CP2K 输出，检查预期文件，完成性质后处理并保存
   provenance。

所以，这个 Skill 负责编排、检查和记录 CP2K；它不替代 CP2K，不会自动
决定唯一正确的物理模型，不会安装集群，也不会因为输入文件语法正确就
保证结果具有科学意义。

### 从用户请求到 CP2K 计算的完整调用链

~~~mermaid
flowchart TD
    A["用户请求和结构文件"] --> B["task_router.py"]
    B --> C["environment_audit.py"]
    C --> D["cp2k_version_detect.py"]
    D --> E["manual_resolver.py 或 manual_cache.py"]
    E --> F["structure_audit.py"]
    F --> G["calculation_init.py"]
    G --> H["科学选择和参数闸门"]
    H --> I["template_registry.json"]
    I --> J["render_versioned_template.py"]
    J --> K["input_lint.py"]
    K --> L{"运行目标"}
    L -->|LOCAL| M["run_cp2k.py"]
    L -->|REMOTE_SERVER| N["remote_ssh.py 预检查"]
    N --> O["scheduler_remote.py"]
    M --> P["外部 CP2K 可执行文件"]
    O --> P
    P --> Q["CP2K 输出、重启文件和性质文件"]
    Q --> R["cp2k_output_parser.py"]
    R --> S["性质后处理"]
    S --> T["provenance.py 和最终报告"]
~~~

仓库里没有一个通用的 run_dft() 函数。真正的本地调用等价于：

~~~text
[cp2k_executable, "-i", "/绝对路径/input.inp", "-o", "/绝对路径/output.out"]
~~~

CP2K 读取输入文件并写出输出文件；Python runner 负责检测版本、启动这个
进程、收集标准输出和错误输出，并在 CP2K 退出后判断结果。

### 每个阶段具体检查什么

| 阶段 | 脚本或产物 | Agent 做什么 | 什么时候阻断 |
| --- | --- | --- | --- |
| 任务路由 | scripts/task_router.py | 把自然语言映射到有限工作流，例如 geo_opt、band、dos、elf_density、charge_population、single_point。 | 任务不支持或含义不明确 |
| 环境 | scripts/environment_audit.py、scripts/scheduler_detect.py | 只读检查 Python、CPU、内存、GPU、MPI、CP2K 候选程序和调度器。 | 找不到 CP2K 可执行文件 |
| 版本 | scripts/cp2k_version_detect.py | 探测可执行文件并记录精确 CP2K 版本。 | 版本无法解析或与目标分支不一致 |
| 手册 | scripts/manual_resolver.py、scripts/manual_cache.py | 解析并哈希对应版本的官方 CP2K 手册。 | MANUAL_REQUIRED |
| 结构 | scripts/structure_audit.py、scripts/structure_audit_full.py | 检查可读性、化学式、晶胞、周期性、过短接触、无序、占位和对称性。 | 结构无效或无序未解决 |
| 科学模型 | calculation 清单、文献参数、参数闸门、收敛计划 | 记录电荷、自旋、泛函、色散、基组、赝势、截断能、k 点、晶胞、slab 和收敛选择。 | SCIENTIFIC_DECISION_REQUIRED |
| 输入生成 | assets/template_registry.json、scripts/render_versioned_template.py | 选择版本匹配模板并填充每个显式槽位。 | 缺少值、工作流未知或版本分支错误 |
| 输入验证 | scripts/input_lint.py | 检查未替换 token、必要 CP2K 区块、版本相关布局和危险设置。 | 仍有 token 或区块结构不正确 |
| 执行批准 | scripts/run_cp2k.py 或 scripts/scheduler_remote.py | 要求本地运行标志或远程提交批准。 | USER_CONFIRMATION_REQUIRED |
| CP2K 运行 | 外部 CP2K 程序 | 真正执行电子结构计算。 | 非零返回、超时或输出缺失 |
| 输出验证 | scripts/cp2k_output_parser.py | 检查正常结束、SCF 收敛、有限能量、几何优化证据、错误和警告。 | 即使有输出文件也可能 FAIL |
| 性质检查 | 吸附能、cube、电荷和收敛脚本 | 只有输入可比、网格一致时才做确定性的后处理。 | 参考设置或 cube 网格不兼容 |
| provenance | scripts/provenance.py | 保存哈希、环境、可执行文件、命令和计算元数据。 | 证据不完整 |

### 一个完整的本地 CP2K 计算

下面以几何优化为例，展示一条实际可执行的流程。请替换结构路径、
CP2K 路径、版本和科学参数。Unix 可以使用 python3，Windows 可以使用
python。命令写成单行，方便不同 Agent 和操作系统转换。

#### 1. 初始化并检查环境

~~~text
python scripts/self_check.py
python scripts/task_router.py --task "geometry optimization"
python scripts/environment_audit.py --output calculation/environment.json
python scripts/cp2k_version_detect.py --executable /绝对路径/cp2k.psmp
~~~

环境审计是只读的，版本探测不会安装 CP2K。Windows 可执行文件也可能写成
C:/CP2K/bin/cp2k.psmp.exe。

#### 2. 解析精确 CP2K 手册

以 CP2K 2024.1 为例：

~~~text
python scripts/manual_resolver.py --version 2024.1 --sections FORCE_EVAL/DFT/SCF --cache-root calculation/manual_cache
~~~

如果运行时缓存中没有需要的官方手册，脚本会返回 MANUAL_REQUIRED。这是
有意设置的安全状态。允许联网时，再执行：

~~~text
python scripts/manual_cache.py --version 2024.1 --cache-root calculation/manual_cache
python scripts/manual_resolver.py --version 2024.1 --sections FORCE_EVAL/DFT/SCF --cache-root calculation/manual_cache
~~~

手册缓存是运行证据，通常应放在计算目录，不应放入公共 Skill 包。工作流
不会在目标手册缺失时悄悄换成另一个 CP2K 版本。

#### 3. 审计结构，但不修改原始结构

~~~text
python scripts/structure_audit.py input_structure/source.cif --output calculation/structure-audit.json
python scripts/structure_audit_full.py input_structure/source.cif --output calculation/structure-audit-full.json
~~~

完整审计在安装了可选库时会增加晶体学检查。脚本不会重写坐标、猜超胞、
删除原子或自动修复过短接触。任何修正都应该形成单独、可审阅的输入文件。

#### 4. 记录计算和科学选择

Agent 在科学问题得到确认后，创建 choices JSON。下面只是记录格式示例：

~~~json
{
  "charge": 0,
  "charge_source": "USER_SPECIFIED",
  "multiplicity": 1,
  "functional": "EXPLICITLY_CONFIRMED",
  "dispersion": "EXPLICITLY_CONFIRMED",
  "basis_source": "EXPLICITLY_CONFIRMED",
  "potential_source": "EXPLICITLY_CONFIRMED"
}
~~~

这些字段值是决策记录标签，不是通用推荐参数；具体材料必须使用适合它的
选择。然后创建计算清单：

~~~text
python scripts/calculation_init.py --structure input_structure/source.cif --task "geometry optimization" --run-target LOCAL --choices-json calculation/choices.json --output-dir calculation
~~~

如果有参考论文，Agent 可以先提取文献中的参数观察：

~~~text
python scripts/literature_profile.py --reference paper.pdf --workflow geo_opt --output calculation/literature-profile.json
~~~

这个步骤只创建文献观察和候选 profile，不会悄悄把论文参数写进计算。随后
可以生成性质相关的收敛计划；收敛阈值仍然要由用户或研究者确认：

~~~text
python scripts/convergence_manager.py --workflow geo_opt --priority balanced --output calculation/convergence-plan.json
~~~

#### 5. 从版本模板生成 CP2K 输入

Agent 根据结构和已经批准的选择生成 calculation/values.json。它至少需要
为模板提供项目名和运行类型、晶胞和坐标、KIND 区块、基组和赝势文件名、
总电荷和自旋、截断能和相对截断能、SCF 设定、几何优化阈值、k 点或能带
路径，以及目标性质需要的输出区块。

然后渲染输入：

~~~text
python scripts/render_versioned_template.py --version 2024.1 --workflow geo_opt --values-json calculation/values.json --output calculation/inputs/geo_opt.inp
~~~

渲染器从 assets/template_registry.json 选择模板，替换 {{PROJECT}}、
{{COORD_BLOCK}} 等显式 token；如果有槽位没有值就失败，并在写入前运行
输入检查。assets/values.example.json 只是 lint 和契约测试的占位 fixture，
不是生产计算参数。

生成的文件是原生 CP2K 输入，结构大致包括：

~~~text
&GLOBAL
  PROJECT example_geo_opt
  RUN_TYPE GEO_OPT
&END GLOBAL
&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
    POTENTIAL_FILE_NAME GTH_POTENTIALS
    ...
  &END DFT
  &SUBSYS
    ...
  &END SUBSYS
&END FORCE_EVAL
~~~

这只是结构示意，不是可以直接运行的科学输入。真正的文件必须有有效的
坐标、KIND 定义、基组/赝势映射以及与模型相符的全部设置。

#### 6. 启动 CP2K 之前检查输入

~~~text
python scripts/input_lint.py calculation/inputs/geo_opt.inp --version 2024.1
~~~

内部 linter 能检查不需要启动 CP2K 就能判断的结构问题。如果计算平台有
自己的 CP2K 输入验证器，Agent 可以把它作为额外闸门。静态检查不能代替
CP2K 实际运行，也不能代替科学审阅。

#### 7. 由 runner 调用真正的 CP2K

~~~text
python scripts/run_cp2k.py --executable /绝对路径/cp2k.psmp --input calculation/inputs/geo_opt.inp --output calculation/outputs/geo_opt.out --expected-version 2024.1 --workdir calculation --allow-run
~~~

这个命令内部按以下顺序工作：

1. 没有 --allow-run 就拒绝执行。
2. 先用 --version 探测 CP2K，必要时再尝试 -v。
3. 如果给了 --expected-version，就把探测结果与它精确比较。
4. 组装 [executable, "-i", absolute_input, "-o", absolute_output]。
5. 用 Python subprocess.run 启动进程，默认把计算目录作为工作目录。
6. 收集 stdout 和 stderr，不自动重试，也不修改输入文件。
7. CP2K 退出后读取输出并交给输出解析器。

只有输出解析器找到足够的成功证据时，runner 才会返回 PASS。仅仅生成了
一个 output 文件并不等于 PASS。对已完成任务可以单独解析：

~~~text
python scripts/cp2k_output_parser.py calculation/outputs/geo_opt.out --return-code 0 --json-output calculation/outputs/geo_opt.parse.json
~~~

#### 8. 保存 provenance 和结果证据

~~~text
python scripts/provenance.py --output calculation/provenance/manifest.yaml --structure input_structure/source.cif --input calculation/inputs/geo_opt.inp --cp2k-executable /绝对路径/cp2k.psmp --command "cp2k.psmp -i /绝对路径/geo_opt.inp -o /绝对路径/geo_opt.out"
~~~

provenance 文件使用 JSON 格式，但符合 YAML 1.2。它会保存结构和输入哈希、
机器、Python 版本、CP2K 版本探测、命令文本，并记录脚本不收集凭据。

### 一个请求为什么可能对应多个 CP2K 作业

许多科学性质不是一次 CP2K 调用就能得到。Agent 对计划中的每个作业都
重复使用“渲染—检查—运行—解析—记录”的循环。

| 用户请求 | 常见的 CP2K 作业计划 | 最后的操作 |
| --- | --- | --- |
| 单点能 | 一个 ENERGY 或对应的单点输入 | 解析收敛能量 |
| 几何优化 | 一个 GEO_OPT 输入，然后检查最终结构 | 检查几何优化结束和最终能量 |
| 能带 | 参考 SCF 加上需要的能带路径作业 | 检查参考态、路径和能带文件 |
| 总态密度或分波态密度 | 参考电子态加版本正确的 DOS/PDOS 输出，通常还要虚轨道 | 检查 DOS/PDOS 文件和设定 |
| 电子密度或电子局域函数 | CP2K 输出体数据文件的密度作业 | 检查有限数值和网格产物 |
| 吸附能 | 复合物、基底、吸附物分别做可比计算 | 计算 E_ads = E_complex - E_host - E_adsorbate |
| 电荷密度差 | 在相同网格坐标系中分别计算复合物、基底、吸附物密度 | 计算 rho_difference = rho_complex - rho_host - rho_adsorbate |
| 功函数 | 明确有真空层的 slab 和静电势输出 | 做以真空为参考的平面分析 |
| 周期电荷 | 与体系和方法对应的周期电荷流程 | 与分子电荷方法分开记录 |

辅助脚本只做确定性的最终操作。它不会因为三个能量可以相减，就声称它们
具有可比性。吸附能需要兼容的泛函、色散、基组、赝势、截断能、相对截断能、
电荷、自旋、k 点和几何策略。电子密度相减前，cube 脚本会检查原子框架、
网格尺寸、原点、网格向量、有限数值和数据数量。

### 版本选择是执行的一部分

公共包中记录了 CP2K 2024.1 和 2026.2 的版本注册信息。Agent 不能混用它们
的模板、手册或重启文件。

| 方面 | CP2K 2024.1 | CP2K 2026.2 |
| --- | --- | --- |
| 手册 | 2024.1 官方手册证据 | 2026.2 官方手册证据 |
| 模板目录 | assets/templates_2024 | assets/templates_2026 |
| DOS/PDOS 布局 | 旧式并列 PRINT/DOS 和 PRINT/PDOS | 注册表记录的嵌套 PRINT/DOS/CURVE/PDOS |
| 输入检查 | 2024.x 专用区块规则 | 2026.x 专用区块规则 |
| 重启策略 | 只与兼容的同版本/同构建复用 | 只与兼容的同版本/同构建复用 |

如果已安装的 CP2K 不在有充分证据的版本分支内，安全做法是请求人工适配，
而不是自动套用最近的模板。

### 远程服务器和调度器

本地 runner 在脚本所在机器启动 CP2K。远程服务器则使用 SSH 预检查和调度
路径：

~~~text
python scripts/remote_ssh.py --host server.example.org --user your_username --key C:/secure/id_ed25519 --known-hosts C:/secure/known_hosts --remote-dir /data/project/cp2k/job-001 --command hostname
~~~

远程辅助脚本要求真实的私钥文件和非空、已验证的 known_hosts 文件，启用严格
主机密钥检查，不自动接受新主机密钥，也不会打印私钥内容。

远程完整流程是：

1. 本地渲染并检查输入。
2. 从 assets/slurm/job.slurm.template、assets/pbs/job.pbs.template 或
   assets/local/run.sh.template 准备调度脚本。
3. 填充显式槽位，尤其是 RUN_COMMAND，写入平台允许的 CP2K 命令。批处理
   作业中的典型命令是 cp2k.psmp -i geo_opt.inp -o geo_opt.out，必要时
   外面再加该平台的 MPI 启动器。
4. 把输入、values、调度脚本、基组、赝势和必要重启文件放到远程工作目录。
5. 生成只读的调度状态命令，并通过获准的远程访问路径执行它。
6. 展示最终作业脚本，在提交前请求批准。
7. 只有越过明确的批准边界后才提交。
8. 取回并解析输出，写入 provenance。

本仓库没有通用的 scp 或 rsync 上传器。远程文件必须通过平台允许的传输
机制放置，Agent 不能猜测远程路径。调度器辅助脚本可以生成状态和提交命令：

~~~text
python scripts/scheduler_remote.py --scheduler slurm --action status --job-id 12345
python scripts/scheduler_remote.py --scheduler slurm --action submit --job-script calculation/job.slurm
~~~

调度器辅助脚本只负责生成命令，不会悄悄提交或监控远程作业。第二个命令在没
有额外显式提交标志时会停在确认状态。除非平台政策明确允许，不要直接在登录
节点运行批处理计算。

### 工作流不会替用户虚构的科学决定

以下选择如果缺失可能改变结果的物理含义，必须由用户或有资质的研究者根据
适当来源确认：

- 总电荷、多重度、自旋处理和磁性排列；
- 交换关联泛函和色散模型；
- 基组、赝势、相对论处理和辅助数据；
- DFT+U 的元素、轨道、U、J 以及来源；
- 部分占据和金属展宽；
- 周期带电体系的补偿电荷处理；
- 晶胞、k 点、截断能和收敛目标；
- slab 取向、终止面、厚度、真空层和偶极修正；
- 吸附参考态、几何策略和吸附物电荷；
- NEB 两端原子映射和中间态定义；
- 采用哪一种电荷分析方法。

Agent 可以准备多个方案、展示假设并生成收敛计划，但不能仅仅为了让 CP2K
启动成功就替用户选择参数。

### 状态含义

这些状态是证据状态，不是宣传标签：

- MANUAL_REQUIRED：还没有解析精确版本的手册。
- SCIENTIFIC_DECISION_REQUIRED：缺少物理模型选择。
- USER_CONFIRMATION_REQUIRED：外部执行或提交需要批准。
- VERSION_UNRESOLVED：无法识别可执行文件版本。
- VERSION_MISMATCH：实际版本和目标分支不一致。
- CONFIGURATION_ERROR：路径、输入、凭据或命令边界无效。
- PASS：CP2K 输出通过已有解析器和产物检查。
- FAIL：进程或解析得到的科学产物未通过检查。
- NOT_VALIDATED：公共包没有某个集群或能力的执行证据。

公共注册表中的能力状态有意从 NOT_VALIDATED 开始。仓库里存在某个模板，
不代表它已经在所有集群上成功运行。

### 依赖和安装

核心编排脚本只使用 Python 标准库。CP2K、MPI、调度器命令、基组文件和
赝势文件都是外部依赖，不会由本仓库自动安装。

可选的结构、环境和文献支持：

~~~text
python -m pip install -r requirements-optional.txt
~~~

开发测试：

~~~text
python -m pip install -r requirements-dev.txt
python -m pytest
~~~

Agent 不应在没有用户允许和合适环境的情况下安装依赖或下载 CP2K 二进制。
仓库中的 example values 和模板只是 lint/契约测试 fixture，不是生产参数。

### 在不同 Agent 中使用

跨 Agent 的核心入口是 SKILL.md。无论使用 Codex、Claude Code 还是其他
Agent，都可以按下面的方式使用：

1. 让 Agent 能访问完整的 cp2k-materials-workflow 文件夹。
2. 明确要求 Agent 先读取 SKILL.md。
3. 提供结构文件的绝对路径和目标计算。
4. 指明运行目标是 LOCAL 还是 REMOTE_SERVER。
5. 在执行前要求展示渲染后的输入、检测到的 CP2K 版本、计划命令和未解决
   的科学选择。

支持原生 Skill 目录的 Agent 可以把整个文件夹复制进去。不支持 Skill 自动
发现的 Agent 也可以直接读取 SKILL.md，并按绝对路径调用脚本。不依赖 Hook、
插件、斜杠命令或特定厂商 API。agents/openai.yaml 只是可选的宿主元数据，
不是运行依赖。

可以给 Agent 的指令示例：

~~~text
使用 /absolute/path/to/cp2k-materials-workflow。
先读取 SKILL.md。审计我的结构和 CP2K 环境，确认精确版本，解析匹配的官方
手册，记录所有科学选择，生成并检查 CP2K 输入。在我批准展示出来的输入和
命令之前，不要执行本地计算或提交远程作业。完成后解析输出并写 provenance。
~~~

### 仓库目录

~~~text
SKILL.md                         与 Agent 无关的操作协议
agents/openai.yaml               可选宿主元数据
scripts/                         路由、审计、渲染、运行和解析脚本
references/                      科学与运行细节
assets/templates_2024/           CP2K 2024.1 模板骨架
assets/templates_2026/           CP2K 2026.2 模板骨架
assets/template_registry.json    版本和能力注册表
assets/*.example.*               本地、远程和参数示例
tests/                            单元测试和契约测试
~~~

仓库修改请参见 CONTRIBUTING.md；第三方资源归属请参见
THIRD_PARTY_ATTRIBUTION.md。
