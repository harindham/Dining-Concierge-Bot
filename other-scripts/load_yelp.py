import os
import time
import requests
import boto3
from datetime import datetime, timezone

YELP_API_KEY = os.environ["YELP_API_KEY"]

URL = "https://api.yelp.com/v3/businesses/search"

HEADERS = {
    "Authorization": f"Bearer {YELP_API_KEY}"
}

CUISINES = [
    "Chinese",
    "Italian",
    "Japanese",
    "Indian",
    "Mexican"
]

dynamodb = boto3.resource(
    "dynamodb",
    region_name="us-east-1"
)

table = dynamodb.Table("yelp-restaurants")

seen = set()


def save_restaurant(business, cuisine):

    restaurant_id = business["id"]

    if restaurant_id in seen:
        return False

    seen.add(restaurant_id)

    location = business.get("location", {})
    coordinates = business.get("coordinates", {})

    item = {
        "RestaurantID": restaurant_id,
        "Cuisine": cuisine,
        "Name": business.get("name", ""),
        "Address": ", ".join(
            location.get("display_address", [])
        ),
        "Coordinates": {
            "latitude": str(
                coordinates.get("latitude", "")
            ),
            "longitude": str(
                coordinates.get("longitude", "")
            )
        },
        "NumberOfReviews": business.get(
            "review_count", 0
        ),
        "Rating": str(
            business.get("rating", 0)
        ),
        "ZipCode": location.get("zip_code", ""),
        "insertedAtTimestamp":
            datetime.now(timezone.utc).isoformat()
    }

    table.put_item(Item=item)

    print(
        f"Stored {cuisine}: {business.get('name')}"
    )

    return True


for cuisine in CUISINES:

    collected = 0
    offset = 0

    while collected < 200:

        params = {
            "term": f"{cuisine} restaurants",
            "location": "Manhattan, NY",
            "limit": 50,
            "offset": offset
        }

        response = requests.get(
            URL,
            headers=HEADERS,
            params=params
        )

        response.raise_for_status()

        businesses = response.json().get(
            "businesses", []
        )

        if not businesses:
            break

        for business in businesses:

            if save_restaurant(
                business,
                cuisine
            ):
                collected += 1

            if collected >= 200:
                break

        offset += 50

        time.sleep(0.5)

    print(
        f"{cuisine}: {collected} restaurants"
    )


print(
    f"Total unique restaurants: {len(seen)}"
)