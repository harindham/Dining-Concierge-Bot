import json
import os
import random
import boto3

from opensearchpy import (
    OpenSearch,
    RequestsHttpConnection,
    AWSV4SignerAuth
)

REGION = os.environ.get(
    "AWS_REGION",
    "us-east-1"
)

QUEUE_URL = os.environ["SQS_QUEUE_URL"]

OPENSEARCH_HOST = os.environ[
    "OPENSEARCH_HOST"
]

SENDER_EMAIL = os.environ[
    "SENDER_EMAIL"
]

sqs = boto3.client("sqs")
ses = boto3.client("ses")

dynamodb = boto3.resource(
    "dynamodb"
)

table = dynamodb.Table(
    "yelp-restaurants"
)


def get_opensearch():

    credentials = (
        boto3.Session()
        .get_credentials()
    )

    auth = AWSV4SignerAuth(
        credentials,
        REGION,
        "es"
    )

    return OpenSearch(
        hosts=[
            {
                "host":
                    OPENSEARCH_HOST,
                "port": 443
            }
        ],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=
            RequestsHttpConnection
    )


def lambda_handler(event, context):

    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=1
    )

    messages = response.get(
        "Messages", []
    )

    if not messages:

        return {
            "statusCode": 200,
            "body": "No requests in queue"
        }

    sqs_message = messages[0]

    request = json.loads(
        sqs_message["Body"]
    )

    cuisine = request["cuisine"]
    email = request["email"]

    client = get_opensearch()

    search_body = {
        "size": 20,
        "query": {
            "term": {
                "Cuisine": cuisine
            }
        }
    }

    result = client.search(
        index="restaurants",
        body=search_body
    )

    hits = result["hits"]["hits"]

    if not hits:

        raise Exception(
            f"No restaurants found "
            f"for {cuisine}"
        )

    number = min(3, len(hits))

    selected = random.sample(
        hits,
        number
    )

    restaurants = []

    for hit in selected:

        restaurant_id = (
            hit["_source"]
            ["RestaurantID"]
        )

        db_response = (
            table.get_item(
                Key={
                    "RestaurantID":
                        restaurant_id
                }
            )
        )

        item = db_response.get("Item")

        if item:
            restaurants.append(item)

    lines = []

    for i, restaurant in enumerate(
        restaurants,
        1
    ):

        lines.append(
            f"{i}. "
            f"{restaurant['Name']}, "
            f"located at "
            f"{restaurant['Address']}"
        )

    restaurant_text = "\n".join(lines)

    email_body = f"""
Hello!

Here are my {cuisine} restaurant
suggestions for {request['numberOfPeople']}
people on {request.get('diningDate')}
at {request.get('diningTime')}:

{restaurant_text}

Enjoy your meal!
"""

    ses.send_email(
        Source=SENDER_EMAIL,
        Destination={
            "ToAddresses": [
                email
            ]
        },
        Message={
            "Subject": {
                "Data":
                    f"{cuisine} Restaurant Suggestions"
            },
            "Body": {
                "Text": {
                    "Data": email_body
                }
            }
        }
    )

    sqs.delete_message(
        QueueUrl=QUEUE_URL,
        ReceiptHandle=
            sqs_message["ReceiptHandle"]
    )

    return {
        "statusCode": 200,
        "body":
            f"Suggestions sent to {email}"
    }