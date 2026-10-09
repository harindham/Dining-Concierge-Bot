import json
import boto3
import uuid
from datetime import datetime, timezone

lex = boto3.client("lexv2-runtime")

BOT_ID = "V4FE1RA3SM"
BOT_ALIAS_ID = "TSTALIASID"
LOCALE_ID = "en_US"


def lambda_handler(event, context):
    # Handle CORS preflight requests
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "POST,OPTIONS"
            },
            "body": ""
        }

    try:
        # Parse the incoming request body
        body = event.get("body", event)

        if isinstance(body, str):
            body = json.loads(body)

        messages = body.get("messages", [])

        if not messages:
            raise ValueError("No messages supplied")

        latest_message = messages[-1]
        text = latest_message.get("unstructured", {}).get("text")

        if not text:
            raise ValueError("Latest message has no text")

        # Reuse a stable conversation session ID when supplied.
        # The frontend should send the same sessionId for every turn.
        session_id = body.get("sessionId")

        if not session_id:
            session_id = (
                latest_message.get("unstructured", {}).get("id")
                or str(uuid.uuid4())
            )

        # Send the user's message to Amazon Lex
        lex_response = lex.recognize_text(
            botId=BOT_ID,
            botAliasId=BOT_ALIAS_ID,
            localeId=LOCALE_ID,
            sessionId=session_id,
            text=text
        )

        # Log details to CloudWatch for debugging
        print("Lex response:", json.dumps(lex_response, default=str))

        lex_messages = lex_response.get("messages", [])

        # Convert every Lex message into the frontend response format
        response_messages = []

        for message in lex_messages:
            content = message.get("content")

            if content:
                response_messages.append({
                    "type": "unstructured",
                    "unstructured": {
                        "id": str(uuid.uuid4()),
                        "text": content,
                        "timestamp": datetime.now(
                            timezone.utc
                        ).isoformat()
                    }
                })

        # Provide a fallback if Lex returns no text messages
        if not response_messages:
            response_messages.append({
                "type": "unstructured",
                "unstructured": {
                    "id": str(uuid.uuid4()),
                    "text": "Sorry, I couldn't understand that.",
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat()
                }
            })

        response = {
            "messages": response_messages,
            "sessionId": session_id
        }

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "POST,OPTIONS",
                "Content-Type": "application/json"
            },
            "body": json.dumps(response)
        }

    except Exception as e:
        print("Error:", str(e))

        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "POST,OPTIONS",
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": str(e)
            })
        }