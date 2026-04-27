# astrbot_plugin_deepseek_v4_cosplay

为 AstrBot 添加两个首轮增强指令：

- `/角色扮演 你的首轮对话`
- `/思维模式 你的首轮对话`

插件会把用户输入的首轮对话原样保留，并在末尾追加一个空行，再拼接对应的 Marker 后发给 LLM。效果等同于只在第一轮执行一次：

- `/角色扮演` -> 追加 `INNER_OS_MARKER`
- `/思维模式` -> 追加 `NO_INNER_OS_MARKER`

## 用法

```text
/角色扮演 你现在是一个嘴硬但心软的女仆，见到主人后先冷淡地打招呼。

/思维模式 你现在是一个高冷剑士，回复时要兼顾克制和压迫感。
```

## 配置

插件遵循 AstrBot Star 插件配置规范，提供两个可视化配置项：

- `roleplay_prompt`
- `thinking_prompt`

可直接在 AstrBot 管理面板中修改追加到首轮消息末尾的 Marker 内容。
