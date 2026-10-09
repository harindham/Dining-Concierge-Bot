import os
import boto3
from opensearchpy import (
    OpenSearch,
    RequestsHttpConnection,
    AWSV4SignerAuth
)

REGION = "us-east-1"
HOST = os.environ["OPENSEARCH_HOST"]

credentials = boto3.Session().get_credentials()

auth = AWSV4SignerAuth(
    credentials,
    REGION,
    "es"
)

client = OpenSearch(
    hosts=[
        {
            "host": HOST,
            "port": 443
        }
    ],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

INDEX = "restaurants"

if not client.indices.exists(index=INDEX):

    client.indices.create(
        index=INDEX,
        body={
            "mappings": {
                "properties": {
                    "RestaurantID": {
                        "type": "keyword"
                    },
                    "Cuisine": {
                        "type": "keyword"
                    }
                }
            }
        }
    )


dynamodb = boto3.resource(
    "dynamodb",
    region_name=REGION
)

table = dynamodb.Table(
    "yelp-restaurants"
)

response = table.scan()

restaurants = response["Items"]

while "LastEvaluatedKey" in response:

    response = table.scan(
        ExclusiveStartKey=
        response["LastEvaluatedKey"]
    )

    restaurants.extend(
        response["Items"]
    )


for restaurant in restaurants:

    doc = {
        "RestaurantID":
            restaurant["RestaurantID"],
        "Cuisine":
            restaurant["Cuisine"]
    }

    client.index(
        index=INDEX,
        body=doc
    )

    print(
        restaurant["Name"]
    )


print(
    f"Indexed {len(restaurants)} restaurants."
)