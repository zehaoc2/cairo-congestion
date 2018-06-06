'''
    File Name: crawler.py
    Author: Zehao Chen (zehaoc2@illinois.edu)
    Maintainer: Zehao Chen (zehaoc2@illinois.edu)
    Description:
	This script parses data from the JSON Object to form a URL and then
        requests data from the Google API. The response data is updated in
        the corresponding trip in the database.
'''

# Import libraries.
import os
import json
import requests
import logging
import time
from datetime import datetime, timedelta
from pprint import pprint
from pymongo import MongoClient
from bson.objectid import ObjectId

API_key = "AIzaSyADEXdHuYJDPa2K5oSzBxAUxCGEzzRvzi0"

def slack_notification(slack_msg):
    """
        Send slack notification with custom messages for different purposes

        Args:
            slack_msg: The custom message being sent.
    """

    slack_url = "https://hooks.slack.com/services/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"

    payload = {"text": slack_msg}

    try:
        r = requests.post(slack_url, data=json.dumps(payload))
    except requests.exceptions.RequestionException as e:
        logger.info("Cairo Crawler: Error while sending controller Slack notification")
        logger.info(e)

def request_API(origin, destination, mode):
    """
    Uses Google Distance Matrix AP
    matrix of origins and destinations.

    Args:
        origin: Coordinate of the origin
        destination: Coordinate of the destination
        mode: Mode of the travel (driving, walking, bicycling, transit). Note
              that bicycling and transit modes are not available since API
              responses will always be ZERO_RESULTS.

    Returns:
        distance: distance of this trip
        duration: duration of this trip
        duration_in_traffic: The length of time it takes to travel this route, based on current and historical traffic conditions.
    """

    base_url = "https://maps.googleapis.com/maps/api/distancematrix/json?"
    final_url = base_url+"origins="+origin+"&destinations="+destination+"&departure_time=now&mode="+mode+"&key="+API_key
    print(final_url)

    distance = 0
    duration = 0
    duration_in_traffic = 0

    try:
        r = requests.get(final_url)
        response = json.loads(r.content)

        if response['status'] == 'OK':
            for row in response['rows']:
                for elem in row['elements']:
                    if elem['status'] == 'OK':
                        try:
                            distance = elem['distance']['value']
                            duration = elem['duration']['value']

                            if mode == 'driving':
                                try:
                                    duration_in_traffic = elem['duration_in_traffic']['value']
                                except:
                                    print("duration_in_traffic doesn't exist.")
                        except:
                            print("Error occurred when parsing response.")

                    else:
                        print("Element status is not OK: " + elem['status'])
                        print(mode)

        else:
            print("Request status is not OK: " + response['status'])

    except requests.exceptions.RequestException as e:
        slack_notification("Cairo Crawler: Error when crawling")

    return distance, duration, duration_in_traffic

def crawl_trip(cells):
    client = MongoClient(os.environ['DB_PORT_27017_TCP_ADDR'],27017)
    db = client.cairo_trial

    latlongs = db.latlongs
    cursor = latlongs.find({"$or": cells})

    slack_notification("Cairo Crawler: Start Crawling Trips.")

    trip_list = []

    modes = ['walking', 'driving']
    cairo_datetime = datetime.utcnow() + timedelta(hours=2)
    cairo_date = cairo_datetime.strftime("%Y-%m-%d")
    cairo_time = cairo_datetime.strftime("%H:%M:%S")
    query_datetime = datetime.utcnow() + timedelta(hours=-5)
    query_date = query_datetime.strftime("%Y-%m-%d")
    query_time = query_datetime.strftime("%H:%M:%S")

    for document in cursor:
        num_trips = 5
        coord = document["coord"]
        orig_latlongs = document["latlongs"][:num_trips]
        dest_latlongs = document["latlongs"][num_trips:]

        for orig_latlong, dest_latlong in zip(orig_latlongs, dest_latlongs):
            origin = str(orig_latlong[0]) + ',' + str(orig_latlong[1])
            destination = str(dest_latlong[0]) + ',' + str(dest_latlong[1])
            trip = {"coord_x": coord[0],
                    "coord_y": coord[1],
                    "cairo_date": cairo_date,
                    "cairo_time": cairo_time,
                    "query_date": query_date,
                    "query_time": query_time,
                    "origin_lat": orig_latlong[0],
                    "origin_long": orig_latlong[1],
                    "destination_lat": dest_latlong[0],
                    "destination_long": dest_latlong[1]
                    }

            for mode in modes:
                distance, duration, duration_in_traffic = request_API(origin, destination, mode)
                mode_distance = mode + "_distance"
                mode_duration = mode + "_duration"
                trip[mode_distance] = distance
                trip[mode_duration] = duration
                trip['driving_duration_in_traffic'] = duration_in_traffic

            trip_list.append(trip)

    db.crawled_trips.insert_many(trip_list)

    slack_notification("Cairo Crawler: Crawling Successful.")
