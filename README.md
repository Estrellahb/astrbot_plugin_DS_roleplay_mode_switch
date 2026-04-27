# astrbot_plugin_DS_roleplay_mode_switch
     注意：需选择 deepseek 作为对话模型
为 AstrBot 提供会话级模式切换，在发送给模型的 `user prompt` 尾部自动追加 DeepSeek 风格的 Marker。

支持的命令：

- `/角色扮演`
- `/思维模式`
- `/关闭模式`

## 行为说明

- `/角色扮演`：切换当前会话到角色扮演模式。
- `/思维模式`：切换当前会话到思维模式。
- `/关闭模式`：关闭当前会话的自动注入，并清空当前对话历史，避免下一条消息继续继承旧上下文。

如果你在切换命令后面直接跟正文，例如 `/角色扮演 你是猫娘女仆小月...`，插件会把这条首轮消息记下来。

后续普通消息到来时：

- 如果 AstrBot 正常带回完整历史，模型会直接从历史里继承首轮 Marker。
- 如果 AstrBot 没有带回完整历史，插件会把“首轮正文 + Marker”补回当前请求，模拟首轮历史仍然存在。

## 用法

```text
/角色扮演 [忙完一天的工作，终于下班回家了，拖着疲累的身躯打开房间门，突然看到一个穿着女仆装的猫娘正在打扫家里的卫生] "你是谁？"

/思维模式 你现在是一个高冷剑士，回复时要兼顾克制和压迫感。

```

`/关闭模式` 的响应示例：

```text
已关闭自动模式注入，并清空当前对话上下文。
```

## 注意事项

- 不建议与额外的角色扮演类 `system prompt` 混用。
- 本插件默认以 `user prompt + 对话历史` 方式维持角色状态；混用 `system prompt` 可能导致模型过度服从系统规则，影响剧情连续性。

## 配置

插件遵循 AstrBot Star 插件配置规范，提供以下可视化配置项：

- `roleplay_prompt`
- `thinking_prompt`
- `default_mode`

`default_mode` 支持 `off`、`roleplay`、`thinking`。

- `off`：新会话默认不开启模式
- `roleplay`：新会话默认启用角色扮演模式
- `thinking`：新会话默认启用思维模式

即使配置了 `default_mode=roleplay` 或 `thinking`，单个会话执行 `/关闭模式` 后也会保持关闭，直到你再次手动切换。

## 实现要点

- 注入时机在 `@filter.on_llm_request()`，不是在普通消息阶段直接改聊天记录。
- 首轮命令正文会缓存到会话内存里，用于“缺历史时补首轮锚点”。
- `/关闭模式` 不只清插件自己的状态，也会清 AstrBot 当前对话历史。

## 参考

https://github.com/victorchen96/deepseek_v4_rolepaly_instruct/tree/main

