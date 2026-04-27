from astrbot.api import AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
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
    "codex",
    "为会话持续追加 DeepSeek 角色扮演或思维模式提示词。",
    "1.1.0",
)
class DeepSeekV4CosplayPlugin(Star):
    ROLEPLAY_COMMANDS = ("角色扮演", "roleplay", "rp")
    THINKING_COMMANDS = ("思维模式", "thinking", "think")
    MODE_ROLEPLAY = "roleplay"
    MODE_THINKING = "thinking"
    MODE_OFF = "off"

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        # 记录每个会话当前启用的模式，用于后续普通消息自动注入 Marker。
        self._session_modes: dict[str, str] = {}
        # 记录首轮正文；当上游没有回传完整历史时，用它补一个“首轮锚点”。
        self._session_first_messages: dict[str, str] = {}

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
        base_text = (user_text or "").rstrip()
        suffix_text = suffix_prompt.strip()
        if not base_text:
            return suffix_text
        return f"{base_text}\n\n{suffix_text}"

    def _get_prompt(self, config_key: str, default_prompt: str) -> str:
        configured_prompt = str(self.config.get(config_key, "") or "").strip()
        return configured_prompt or default_prompt

    def _normalize_mode(self, mode: str | None) -> str:
        normalized = str(mode or "").strip().lower()
        if normalized in {self.MODE_ROLEPLAY, self.MODE_THINKING, self.MODE_OFF}:
            return normalized
        return self.MODE_OFF

    def _get_default_mode(self) -> str:
        return self._normalize_mode(self.config.get("default_mode", self.MODE_OFF))

    def _get_session_mode(self, session_id: str) -> str:
        return self._session_modes.get(session_id, self._get_default_mode())

    def _set_session_mode(self, session_id: str, mode: str) -> None:
        normalized = self._normalize_mode(mode)
        # 对当前会话显式写入 off，避免 default_mode 重新把模式打开。
        self._session_modes[session_id] = normalized
        if normalized == self.MODE_OFF:
            self._session_first_messages.pop(session_id, None)

    def _set_session_first_message(self, session_id: str, instruction: str) -> None:
        cleaned = (instruction or "").strip()
        if not cleaned:
            return
        self._session_first_messages[session_id] = cleaned

    def _get_session_first_message(self, session_id: str) -> str:
        return self._session_first_messages.get(session_id, "").strip()

    def _get_prompt_for_mode(self, mode: str) -> str:
        if mode == self.MODE_ROLEPLAY:
            return self._get_prompt("roleplay_prompt", DEFAULT_ROLEPLAY_PROMPT)
        if mode == self.MODE_THINKING:
            return self._get_prompt("thinking_prompt", DEFAULT_THINKING_PROMPT)
        return ""

    def _build_seed_prompt(self, session_id: str, marker: str) -> str:
        first_message = self._get_session_first_message(session_id)
        if not first_message:
            return ""
        return self._compose_prompt(first_message, marker)

    async def _clear_current_conversation_context(self, event: AstrMessageEvent) -> bool:
        """清空 AstrBot 当前会话的持久化历史，避免关闭模式后首条消息继续继承旧上下文。"""
        umo = event.unified_msg_origin
        current_cid = await self.context.conversation_manager.get_curr_conversation_id(umo)
        if not current_cid:
            return False

        await self.context.conversation_manager.update_conversation(umo, current_cid, [])
        event.set_extra("_clean_ltm_session", True)
        return True

    @filter.on_llm_request()
    async def inject_mode_prompt(
        self, event: AstrMessageEvent, request: ProviderRequest
    ) -> None:
        session_id = event.get_session_id()
        mode = self._get_session_mode(session_id)
        marker = self._get_prompt_for_mode(mode)
        if not marker or not request.prompt or not request.prompt.strip():
            return

        current_prompt = request.prompt.strip()
        seed_prompt = self._build_seed_prompt(session_id, marker)

        # AstrBot 某些链路不会把完整 messages 历史继续传回模型。
        # 如果当前不是首轮消息，就把“首轮正文 + Marker”补回去，模拟历史仍然存在。
        if seed_prompt and current_prompt != self._get_session_first_message(session_id):
            request.prompt = (
                "以下是当前对话已经建立的首轮设定与用户开场，请视为同一段持续对话历史，不要遗忘。\n\n"
                f"{seed_prompt}\n\n"
                f"【当前用户继续发言】\n{current_prompt}"
            )
            return

        # 首轮或没有首轮缓存时，直接按 DeepSeek 文档建议把 Marker 拼到 user prompt 尾部。
        request.prompt = self._compose_prompt(current_prompt, marker)

    @filter.command("角色扮演", alias={"roleplay", "rp"})
    async def roleplay(self, event: AstrMessageEvent):
        """切换到角色扮演模式，并让后续对话自动追加角色沉浸提示词。"""
        session_id = event.get_session_id()
        self._set_session_mode(session_id, self.MODE_ROLEPLAY)
        payload = self._extract_payload(event.get_message_str(), self.ROLEPLAY_COMMANDS)
        if payload:
            # 把首轮正文单独记住，后续普通消息需要时可拿来补历史。
            self._set_session_first_message(session_id, payload)
        if not payload:
            yield event.plain_result("已切换到角色扮演模式，后续对话会自动追加角色提示词。")
            return

        event.should_call_llm(True)
        yield event.request_llm(prompt=payload)

    @filter.command("思维模式", alias={"thinking", "think"})
    async def thinking_mode(self, event: AstrMessageEvent):
        """切换到思维模式，并让后续对话自动追加分析型提示词。"""
        session_id = event.get_session_id()
        self._set_session_mode(session_id, self.MODE_THINKING)
        payload = self._extract_payload(event.get_message_str(), self.THINKING_COMMANDS)
        if payload:
            self._set_session_first_message(session_id, payload)
        if not payload:
            yield event.plain_result("已切换到思维模式，后续对话会自动追加思维提示词。")
            return

        event.should_call_llm(True)
        yield event.request_llm(prompt=payload)

    @filter.command("关闭模式", alias={"关闭角色模式", "原版模式", "off", "normal"})
    async def disable_mode(self, event: AstrMessageEvent):
        """关闭当前会话的自动提示词注入。"""
        self._set_session_mode(event.get_session_id(), self.MODE_OFF)
        cleared = await self._clear_current_conversation_context(event)
        if cleared:
            yield event.plain_result("已关闭自动模式注入，并清空当前对话上下文。")
            return
        yield event.plain_result("已关闭自动模式注入；当前没有可清空的对话上下文。")
