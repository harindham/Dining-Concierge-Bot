import json
import os
import boto3

sqs = boto3.client("sqs")
QUEUE_URL = os.environ["SQS_QUEUE_URL"]


def get_slot(slots, name):
    slot = slots.get(name)

    if not slot:
        return None

    value = slot.get("value")

    if not value:
        return None

    return value.get("interpretedValue")


def close(intent_name, message):
    return {
        "sessionState": {
            "dialogAction": {
                "type": "Close"
            },
            "intent": {
                "name": intent_name,
                "state": "Fulfilled"
            }
        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": message
            }
        ]
    }


def delegate(intent_name, slots):
    return {
        "sessionState": {
            "dialogAction": {
                "type": "Delegate"
            },
            "intent": {
                "name": intent_name,
                "slots": slots,
                "state": "InProgress"
            }
        }
    }


def lambda_handler(event, context):

    print(json.dumps(event))

    intent = event["sessionState"]["intent"]
    intent_name = intent["name"]
    slots = intent.get("slots", {})

    # -----------------------
    # GreetingIntent
    # -----------------------

    if intent_name == "GreetingIntent":
        return close(
            intent_name,
            "Hi there, how can I help?"
        )

    # -----------------------
    # ThankYouIntent
    # -----------------------

    if intent_name == "ThankYouIntent":
        return close(
            intent_name,
            "You're welcome!"
        )

    # -----------------------
    # DiningSuggestionsIntent
    # -----------------------

    if intent_name == "DiningSuggestionsIntent":

        invocation_source = event.get("invocationSource")

        # Let Lex continue collecting slots
        if invocation_source == "DialogCodeHook":
            return delegate(intent_name, slots)

        location = get_slot(slots, "Location")
        cuisine = get_slot(slots, "Cuisine")
        dining_date = get_slot(slots, "DiningDate")
        dining_time = get_slot(slots, "DiningTime")
        people = get_slot(slots, "NumberOfPeople")
        email = get_slot(slots, "Email")

        message = {
            "location": location,
            "cuisine": cuisine,
            "diningDate": dining_date,
            "diningTime": dining_time,
            "numberOfPeople": people,
            "email": email
        }

        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(message)
        )

        return close(
            intent_name,
            "You're all set. I received your request. "
            "I'll email you restaurant suggestions shortly!"
        )

    return close(
        intent_name,
        "Sorry, I couldn't understand your request."
    )