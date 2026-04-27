from astrbot.api import AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register


DEFAULT_ROLEPLAY_PROMPT = """【角色沉浸要求】在你的思考过程（<think>标签内）中，请遵守以下规则：
1. 请以角色第一人称进行内心独白，用括号包裹内心活动，例如"（心想：……）"或"(内心OS：……)"
2. 用第一人称描写角色的内心感受，例如"我心想""我觉得""我暗自"等
3. 思考内容应沉浸在角色中，通过内心独白分析剧情和规划回复"""

DEFAULT_THINKING_PROMPT = """【思维模式要求】在你的思考过程（<think>标签内）中，请遵守以下规则：
1. 禁止使用圆括号包裹内心独白，例如"（心想：……）"或"(内心OS：……)"，所有分析内容直接陈述即可
2. 禁止以角色第一人称描写内心活动，例如"我心想""我觉得""我暗自"等，请用分析性语言替代
3. 思考内容应聚焦于剧情走向分析和回复内容规划，不要在思考中进行角色扮演式的内心戏表演"""


@register(
    "astrbot_plugin_DS_roleplay_mode_switch",
    "vvx",
    "为首轮对话追加 DeepSeek V4 角色扮演或思维模式提示词。",
    "1.0.0",
)
class DeepSeekV4CosplayPlugin(Star):
    ROLEPLAY_COMMANDS = ("角色扮演", "roleplay", "rp")
    THINKING_COMMANDS = ("思维模式", "thinking", "think")

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    @staticmethod
    def _extract_payload(message: str | None, command_names: tuple[str, ...]) -> str:
        raw_message = (message or "").strip()
        for command_name in sorted(command_names, key=len, reverse=True):
            if raw_message == command_name:
                return ""
            if raw_message.startswith(command_name):
                suffix = raw_message[len(command_name) :]
                if not suffix or suffix[:1].isspace():
                    return suffix.lstrip()
        return ""

    @staticmethod
    def _compose_prompt(user_text: str, suffix_prompt: str) -> str:
        return f"{user_text.rstrip()}\n\n{suffix_prompt.strip()}"

    def _get_prompt(self, config_key: str, default_prompt: str) -> str:
        configured_prompt = str(self.config.get(config_key, "") or "").strip()
        return configured_prompt or default_prompt

    @filter.command("角色扮演", alias={"roleplay", "rp"})
    async def roleplay(self, event: AstrMessageEvent):
        """把首轮对话与 DeepSeek V4 角色沉浸提示词拼接后发送给 LLM。"""
        payload = self._extract_payload(event.message_str, self.ROLEPLAY_COMMANDS)
        if not payload:
            yield event.plain_result("用法：/角色扮演 你的首轮对话")
            return

        event.should_call_llm(True)
        yield event.request_llm(
            prompt=self._compose_prompt(
                payload,
                self._get_prompt("roleplay_prompt", DEFAULT_ROLEPLAY_PROMPT),
            )
        )

    @filter.command("思维模式", alias={"thinking", "think"})
    async def thinking_mode(self, event: AstrMessageEvent):
        """把首轮对话与 DeepSeek V4 思维模式提示词拼接后发送给 LLM。"""
        payload = self._extract_payload(event.message_str, self.THINKING_COMMANDS)
        if not payload:
            yield event.plain_result("用法：/思维模式 你的首轮对话")
            return

        event.should_call_llm(True)
        yield event.request_llm(
            prompt=self._compose_prompt(
                payload,
                self._get_prompt("thinking_prompt", DEFAULT_THINKING_PROMPT),
            )
        )
