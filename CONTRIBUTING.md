# Contributing

Keep contributions portable, auditable, and useful to more than one project.

## English

- Keep `SKILL.md` agent-neutral; do not add vendor-specific instructions to the
  core workflow.
- Do not commit cluster paths, private keys, credentials, raw personal data,
  downloaded manual caches, or project-specific adapters.
- Keep version-specific CP2K syntax in the matching template family and update
  `assets/template_registry.json` when a template changes.
- Mark capabilities `NOT_VALIDATED` until an exact executable, input, output,
  parser result, and property gate provide evidence.
- Add or update tests for deterministic script behavior. Run
  `python scripts/self_check.py`, `python -m pytest`, and
  `python -m compileall -q scripts assets/library` before a release when the
  relevant tools are available.

## 中文

- 保持 `SKILL.md` 与 Agent 厂商无关，不要把特定平台命令写入核心流程。
- 不要提交集群真实路径、私钥、凭据、手册缓存、个人数据或项目专用适配器。
- 不同 CP2K 版本的语法必须放在对应模板目录；模板变化时同步更新注册表。
- 没有完整的可执行文件、输入、输出、解析结果和性质检查证据时，状态保持
  `NOT_VALIDATED`。
- 为确定性脚本补充测试；发布前尽量运行自检、测试和编译检查。
