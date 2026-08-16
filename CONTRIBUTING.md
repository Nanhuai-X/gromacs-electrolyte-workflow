# Contributing

本仓库维护 `gromacs-electrolyte-workflow` Agent Skills 工作流、其可复用脚本、科学参考和测试。提交修改前请运行：

```bash
python -m unittest discover -s tests -v
python -m compileall -q scripts
```

如果修改输入字段、输出字段、门禁状态、默认协议或科学解释，请同步更新 `SKILL.md`、相关 `references/`、`assets/`、测试和 `README.md`。新增的可复用逻辑放入 `scripts/`；新增的领域资料放入 `references/`。

不要提交原始实验/结构数据、生产轨迹、Gaussian checkpoint、GROMACS 输出、缓存、私钥、`known_hosts` 或敏感本地配置。保持输入来源、单位、哈希和用户确认状态可审计。

提交消息建议使用 `feat:`、`fix:`、`docs:`、`test:`、`refactor:` 或 `chore:` 前缀。

## English

This repository maintains the `gromacs-electrolyte-workflow` Agent Skills workflow, reusable scripts, scientific references, and tests. Before submitting a change, run:

```bash
python -m unittest discover -s tests -v
python -m compileall -q scripts
```

When changing input fields, output fields, gate states, default protocols, or scientific interpretation, update `SKILL.md`, the relevant `references/`, `assets/`, tests, and `README.md` together. Put reusable implementation logic in `scripts/` and domain material in `references/`.

Do not commit raw experimental/structure data, production trajectories, Gaussian checkpoints, GROMACS output, caches, private keys, `known_hosts`, or sensitive local configuration. Keep input sources, units, hashes, and user-confirmation state auditable.

Use conventional commit prefixes such as `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, or `chore:`.
