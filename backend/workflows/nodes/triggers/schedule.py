"""
Schedule trigger node processor
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import BaseNodeProcessor
from datetime import datetime

logger = logging.getLogger(__name__)


class TriggerScheduleProcessor(BaseNodeProcessor):
    """
    Processes scheduled trigger events
    This node starts a workflow on a schedule
    """

    async def process(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process scheduled trigger

        Config includes schedule settings like cron expression, timezone, etc.
        """
        schedule_config = config.get('schedule', {})

        # Get current execution time
        execution_time = datetime.now().isoformat()

        logger.info(f"Schedule trigger activated at {execution_time}")

        # Pass schedule information forward
        return {
            'success': True,
            'triggered_at': execution_time,
            'schedule': schedule_config,
            'trigger_type': 'schedule',
            'is_scheduled': True
        }

    def get_display_name(self) -> str:
        return "Schedule Trigger"

    def get_description(self) -> str:
        return "Starts workflow on a schedule"

    def get_category(self) -> str:
        return "Triggers"

    def get_icon(self) -> str:
        return "⏰"