from pathlib import Path
from typing import Any

from jinja2 import Template
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel

from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.services.llm import get_llm
from minitap.mobile_use.utils.conversations import get_screenshot_message_for_llm
from minitap.mobile_use.utils.logger import get_logger

logger = get_logger(__name__)


class UpdateField(BaseModel):
    """Single field update with field name as key and value as the content"""

    field_name: str
    field_value: Any


class Patch(BaseModel):
    resource_id: str | None = None
    updates: list[UpdateField]


class SpectronOutput(BaseModel):
    patches: list[Patch]


async def spectron(
    ctx: MobileUseContext, screen_hierarchy: list, screenshot_base64: str
) -> SpectronOutput:
    logger.info("Starting Spectron Agent")
    system_message = Template(
        Path(__file__).parent.joinpath("spectron.md").read_text(encoding="utf-8")
    ).render(
        device_dimensions=f"{ctx.device.device_width}x{ctx.device.device_height} (width x height)",
        screen_hierarchy=str(screen_hierarchy),
    )
    human_message = get_screenshot_message_for_llm(screenshot_base64=screenshot_base64)

    messages: list[BaseMessage] = [
        SystemMessage(content=system_message),
        human_message,
    ]

    llm = get_llm(ctx=ctx, name="spectron", is_utils=True, temperature=1)
    structured_llm = llm.with_structured_output(SpectronOutput, method="function_calling")
    response: SpectronOutput = await structured_llm.ainvoke(messages)  # type: ignore
    # print the response
    print("Spectron response: ", response)
    return response
