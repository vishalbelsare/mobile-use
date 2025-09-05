from minitap.mobile_use.agents.executor.utils import is_last_tool_message_take_screenshot
from minitap.mobile_use.agents.spectron.spectron import SpectronOutput, spectron
from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.controllers.mobile_command_controller import get_screen_data
from minitap.mobile_use.controllers.platform_specific_commands_controller import (
    get_device_date,
    get_focused_app_info,
)
from minitap.mobile_use.graph.state import State
from minitap.mobile_use.utils.decorators import wrap_with_callbacks
from minitap.mobile_use.utils.logger import get_logger
from minitap.mobile_use.utils.ui_hierarchy import find_element_by_resource_id

logger = get_logger(__name__)


class ContextorNode:
    def __init__(self, ctx: MobileUseContext):
        self.ctx = ctx

    @wrap_with_callbacks(
        before=lambda: logger.info("Starting Contextor Agent"),
        on_success=lambda _: logger.success("Contextor Agent"),
        on_failure=lambda _: logger.error("Contextor Agent"),
    )
    async def __call__(self, state: State):
        device_data = get_screen_data(self.ctx.screen_api_client)
        focused_app_info = get_focused_app_info(self.ctx)
        device_date = get_device_date(self.ctx)

        should_add_screenshot_context = is_last_tool_message_take_screenshot(list(state.messages))
        screen_hierarchy = device_data.elements
        enriched_screen_hierarchy: list = screen_hierarchy.copy()
        should_enrich_hierarchy = len(device_data.base64) > 0

        if should_enrich_hierarchy:
            try:
                spectron_output: SpectronOutput = await spectron(
                    ctx=self.ctx,
                    screen_hierarchy=screen_hierarchy,
                    screenshot_base64=device_data.base64,
                )
                updates_count = 0
                for patch in spectron_output.patches:
                    if patch.resource_id:
                        element = find_element_by_resource_id(
                            ui_hierarchy=screen_hierarchy, resource_id=patch.resource_id
                        )
                        if element:
                            for update in patch.updates:
                                element[update.field_name] = update.field_value
                        enriched_screen_hierarchy.append(element)
                    else:
                        new_el = {}
                        for update in patch.updates:
                            new_el[update.field_name] = update.field_value
                        enriched_screen_hierarchy.append(new_el)
                    updates_count += 1

                logger.info(f"Enriched screen hierarchy with {updates_count} updates.")

            except Exception as e:
                logger.warning(f"Failed to enrich screen hierarchy: {e}")

        return state.sanitize_update(
            ctx=self.ctx,
            update={
                "latest_screenshot_base64": device_data.base64
                if should_add_screenshot_context
                else None,
                "latest_ui_hierarchy": enriched_screen_hierarchy,
                "focused_app_info": focused_app_info,
                "screen_size": (device_data.width, device_data.height),
                "device_date": device_date,
            },
        )
