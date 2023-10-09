from core.utils import validators
import logging,json

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CancelValidator(validators.BaseValidator):
    async def __call__(self, *args, **kwargs):
        user_input = str(self.value)
        current_intent = await self.get_intent(self.value)
        print("user intent================>", current_intent)
        print(f"user input is: {self.value}")
        if current_intent == "cancel" or user_input.lower() in ["cancel"]:
            print("user cancelled...")
            self.slots["slot_txn_log_to_producer"] = self.log_stage(
                "Final Response", "User Aborted", "User Cancelled"
            )
            await self.validation_failure(flow_end_utter="utter_cancel", flow_end=True)