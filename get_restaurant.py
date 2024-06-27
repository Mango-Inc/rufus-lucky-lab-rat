
import csv
import os
import random
from datetime import datetime, timedelta

from google.cloud.firestore_v1 import SERVER_TIMESTAMP, FieldFilter

from firebase_helper import firestore_db

with open('restaurants.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    all_restaurants = list(reader)


def _get_restaurants_that_havent_been_chosen():
    # Get all restaurants that haven't been chosen in the last 30 days
    recent_restaurants = firestore_db.collection(u'recent_restaurants').where(
        filter=FieldFilter(u'date', u'>', datetime.now() - timedelta(days=30))
    ).stream()

    recent_restaurant_names = set()
    for recent_restaurant in recent_restaurants:
        recent_restaurant_names.add(recent_restaurant.to_dict()['name'])

    restaurants_that_havent_been_chosen = []
    for restaurant in all_restaurants:
        if restaurant['Restaurant Name'] not in recent_restaurant_names:
            restaurants_that_havent_been_chosen.append(restaurant)

    return restaurants_that_havent_been_chosen


def get_random_restaurant():
    restaurants_that_havent_been_chosen = _get_restaurants_that_havent_been_chosen()

    random_restaurant = random.choice(restaurants_that_havent_been_chosen)

    if os.environ.get('K_REVISION') is not None:
        # If we're running on GCP, save the restaurant to the database
        firestore_db.collection(u'recent_restaurants').document().set({
            u'name': random_restaurant['Restaurant Name'],
            u'date': SERVER_TIMESTAMP,
        })

    return {
        "name": random_restaurant['Restaurant Name'],
        "URL": random_restaurant['URL'],
        "description": random_restaurant['Description'],
    }


if __name__ == "__main__":
    print(get_random_restaurant())
