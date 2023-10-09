import json
import logging,json
from json import JSONDecodeError
import requests
from core.utils import wrappers

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
BYPASS_EVENT_HISTORY = True


class InitiateHandoff(wrappers.BaseWrapper):
    async def __call__(self, *args, **kwargs):
        slot_rmn = self.slots.get("slot_rmn")
        error_code = "no error"
        event_history_len = 0
        event_history = []
        slot_utter_handoff_content = ""
        self.slots["slot_initiate_handoff_code"] = error_code
        if BYPASS_EVENT_HISTORY:
            try:
                event_history = self.call_api(api_name="event history")
                api_status_code = self.slots.get("api_status_code")
                # self.slots["slot_status_code1"] = event_history.status_code
                if api_status_code == 200:
                    event_history = json.loads(event_history.text)
                    event_history = sorted(event_history, key=lambda x: x["id"])
                    # event_history.reverse()
                    event_history_len = len(event_history)
                    res_status = {
                        "status": "success",
                        "response_text": event_history,
                    }
                else:
                    logger.info("status code... " + str(api_status_code))
                    res_status = {
                        "status": "error",
                        "utter": "utter_handoff_debug",
                        "log_message": "5" + " : " + str(api_status_code),
                    }
                    slot_utter_handoff_content = "Event logger API is failing"
                    # await self.dispatcher.utter_template("utter_handoff_debug")
            except requests.exceptions.ConnectionError:
                logger.exception("VPN Connectivity Lost....")
                res_status = {
                    "status": "error",
                    "utter": "utter_vpn_down",
                    "log_message": 9,
                }
                # await self.dispatcher.utter_template("utter_vpn_down")
            except requests.exceptions.Timeout:
                logger.exception("Request timedout.... ")
                res_status = {
                    "status": "error",
                    "utter": "utter_api_timedout",
                    "log_message": 9,
                }
                # await self.dispatcher.utter_template("utter_api_timedout")
            except JSONDecodeError:
                logger.exception("Event History json decode error... ")
                res_status = {
                    "status": "error",
                    "log_message": "Event History json decode error"
                }
            except Exception as e:
                logger.info("Exception... ", str(e))
                res_status = {
                    "status": "error",
                    "utter": "utter_uncaught_exception",
                    "log_message": "6" + " : " + str(e)[:150],
                }
                # await self.dispatcher.utter_template("utter_uncaught_exception")
        # logger.debug(f"API status--->{res_status}")
        prev_messages = []
        load_message = lambda ev: ev.replace("'", '"') \
            .replace("None", "null") \
            .replace("True", "true") \
            .replace("False", "false")
        update_quick_replies = lambda x: [
            {
                "title": r["title"] if r.get("title") is not None else "",
                "payload": r["payload"] if r.get("payload") is not None else "",
            }
            for r in x
        ]
        # print(event_history)
        event = 0
        while event < event_history_len:
            flag_set = False
            # print(type(event_history[i]),event_history[i])
            if event + 1 <= event_history_len - 1:
                if event_history[event]["source"] == "user" and event_history[event + 1]["source"] == "bot":
                    user_event = event_history[event]
                    bot_event = event_history[event + 1]
                    event += 2
                    try:
                        # print(json.loads(load_message(bot_event.get("message"))))
                        # print(load_message(user_event.get("message")))
                        bot_msg = json.loads(load_message(bot_event.get("message")), strict=False)
                        user_msg = load_message(user_event.get("message"))
                        flag_set = True
                    except JSONDecodeError:
                        logger.debug(
                            f"Non JSON message found, ignoring: {user_event.get('message')},{bot_event.get('message')}"
                        )
                        continue
            if not flag_set:
                if event_history[event]["source"] == "bot":
                    bot_event = event_history[event]
                    user_msg = ""
                    event += 1
                    try:
                        bot_msg = json.loads(load_message(bot_event.get("message")), strict=False)
                    except JSONDecodeError:
                        logger.debug(
                            f"Non JSON message found, ignoring {bot_event.get('message')}"
                        )
                        continue
                else:
                    user_event = event_history[event]
                    user_msg = load_message(user_event.get("message"))
                    bot_response = {
                        "title": "",
                        "subtitle": "",
                        "image_url": "",
                        "quick_replies":
                            [{
                                "title": "",
                                "payload": "",
                            }],
                        "data": [{}],
                    }
                    prev_messages.append(
                        {
                            "text": user_msg,
                            "bot_response": bot_response,
                            "timestamp": user_event.get("timestamp"),
                        }
                    )
                    event += 1
                    continue
            bot_response = {
                "title": bot_msg["data"][0]["title"]
                if bot_msg["data"][0].get("title") is not None
                else "",
                "subtitle": bot_msg["data"][0]["subtitle"]
                if bot_msg["data"][0].get("subtitle") is not None
                else "",
                "image_url": bot_msg["data"][0]["image_url"]
                if bot_msg["data"][0].get("image_url") is not None
                else "",
                "quick_replies": update_quick_replies(bot_msg["quick_replies"]),
                "data": bot_msg["data"],
            }
            prev_messages.append(
                {
                    "text": user_msg,
                    "bot_response": bot_response,
                    "timestamp": bot_event.get("timestamp"),
                }
            )
        slot_handoff_connection_request = {
            "type": "handoff",
            "username": self.slots["slot_user_name"],
            "channel_id": self.slots["channel_id"],  # avalaible by default, always
            "bot_session_id": self.slots["slot_session_id"],
            "channel": self.slots["channel_code"],  # avalaible by default, always
            "skill": self.slots["skill"] if self.slots.get("skill") else "en",
            # "phone_number": slot_rmn,
            "message": "handoff",
            # "customer_id": slot_customer_id,
            "tenant": self.slots["tenant"],
            "prev_messages": prev_messages,
        }
        slot_handoff_connection_request.update({"phone_number": slot_rmn} if slot_rmn else {})
        self.slots["slot_handoff_connection_request"] = slot_handoff_connection_request
        # print(f"Prev messages {prev_messages}")
        logger.debug(f"Prev messages--> {prev_messages}")
        logger.debug(f"event history --> {event_history}")
        if not event_history:
            logger.info("Event history is empty")
        try:
            handoff_call_response = self.call_api(api_name="Initiate handoff")
            handoff_call_response = json.loads(handoff_call_response.text)
            api_status_code = self.slots.get("api_status_code")
            if api_status_code == 201:
                res_status = {
                    "status": "success",
                    "response_text": handoff_call_response,
                }
            elif api_status_code == 400:
                error_code = handoff_call_response["errors"][0]["code"]
                error_detail = handoff_call_response["errors"][0]["detail"]
                res_status = {
                    "status": "400",
                    "error_code": error_code,
                    "response_text": error_detail,
                }
                self.slots["slot_initiate_handoff_code"] = error_code
            else:
                logger.info("status code... " + str(api_status_code))
                res_status = {
                    "status": "error",
                    "utter": "utter_handoff_debug",
                    "log_message": "5" + " : " + str(api_status_code),
                }
                slot_utter_handoff_content = "Agent handoff has failed"
                # await self.dispatcher.utter_template("utter_handoff_debug")
        except requests.exceptions.ConnectionError:
            logger.exception("VPN Connectivity Lost....")
            res_status = {
                "status": "error",
                "utter": "utter_vpn_down",
                "log_message": 9,
            }
            # await self.dispatcher.utter_template("utter_vpn_down")

        except requests.exceptions.Timeout:
            logger.exception("Request timedout.... ")
            res_status = {
                "status": "error",
                "utter": "utter_api_timedout",
                "log_message": 9,
            }
            # await self.dispatcher.utter_template("utter_api_timedout")

        except Exception as e:
            logger.info("Exception... ", str(e))
            res_status = {
                "status": "error",
                "utter": "utter_uncaught_exception",
                "log_message": "6" + " : " + str(e)[:150],
            }
            # await self.dispatcher.utter_template("utter_uncaught_exception")
        logger.debug(f"API status--->{res_status}")
        print(f"res_status----{res_status}")
        self.slots["slot_utter_handoff_content"] = slot_utter_handoff_content
