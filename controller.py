"""
        File Name: controller.py
        Author: Brian Ko (swko2@illinois.edu)
        Maintainer: Brian Ko (swko2@illinois.edu)
        Description:
            This is the main script that controls the initiation, scheduling,
            and the operation of the Cairo crawler.
"""

import os
import logging
import json
import requests
from latlong_generator import generate_latlongs
from pymongo import MongoClient

def logging_init():
    """Initiates the logger

    Initiates the logger, the logger handler (for file handling), and the
    formatter

    """
 
    logger = logging.getLogger("cairo_crawler")
    logger.setLevel(logging.INFO)

    log_handler = logging.FileHandler("cairo_crawler.log", mode="w")

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    log_handler.setFormatter(formatter)
    logger.addHandler(lh)

    return logger, log_handler

def slack_notification(slack_msg):
    """Send slack notification

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

def load_latlongs():
    """Generates and stores the lat/longs in a database

    Calls the generate_latlongs method from latlong_generator.py and stores
    the generated data in a MongoDB database.

    """

    client = MongoClient(os.environ['DB_PORT_27017_TCP_ADDR'], 27017)
    db = client.cairo_trial
    record = db.latlongs

    slack_msg = "Cairo Crawler: Generating Random Latitude/Longitudes"
    slack_notification(slack_msg)

    latlong_list = generate_latlongs()

    #filename = "latlongs{0}.json"

    #for x in range(len(latlong_list)):
    #    coord = latlong_list[x]["coord"]
    #    with open(filename.format(coord), 'w') as f:
    #        json.dump(latlong_list[x], f)

    record.insert_many(latlong_list)

    slack_msg = "Cairo Crawler: Inserted Random Latitude/Longitudes into MongoDB"
    slack_notification(slack_msg)

def main():
   slack_msg = "Cairo Crawler: Initiating Controller"
   slack_notification(slack_msg)

   load_latlongs()


if __name__ == "__main__":
    main()