# Changelog

## v1.0.0 - 2026-04-27

- 新增 `/角色扮演` 指令，接收首轮对话并在末尾追加空行与 `INNER_OS_MARKER` 后发送给 LLM。
- 新增 `/思维模式` 指令，接收首轮对话并在末尾追加空行与 `NO_INNER_OS_MARKER` 后发送给 LLM。
- 新增 `_conf_schema.json`，支持在 AstrBot 面板中可视化配置 `roleplay_prompt` 与 `thinking_prompt`。
- 更新 `metadata.yaml`，将插件元信息从模板内容改为当前项目配置。
- 更新 `README.md`，补充指令用法、配置项说明和首轮拼接行为说明。
