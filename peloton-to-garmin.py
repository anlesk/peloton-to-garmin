#
# Author: Bailey Belvis (https://github.com/philosowaffle)
#
# Tool to generate a valid TCX file from a Peloton activity for Garmin.
#
import os
import sys
import json
import logging
import re

from pathlib import Path
from google.cloud import storage
from google.oauth2 import service_account
from datetime import datetime, timezone

from lib import pelotonApi
from lib import config_helper as config
from lib import tcx_builder

##############################
# Debugging Setup
##############################
if config.ConfigSectionMap("DEBUG")['pauseonfinish'] is None:
    pause_on_finish = "false"
else:
    pause_on_finish = config.ConfigSectionMap("DEBUG")['pauseonfinish']

##############################
# Logging Setup
##############################
logger = logging.getLogger('peloton-to-garmin')
# logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)

if len(sys.argv) > 3:
    file_handler = logging.FileHandler(sys.argv[3])
else:
    if config.ConfigSectionMap("LOGGER")['logfile'] is None:
        logger.error("Please specify a path for the logfile.")
        sys.exit(1)
    file_handler = logging.FileHandler(config.ConfigSectionMap("LOGGER")['logfile'])

# Formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s: %(message)s')

# File Handler
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.debug("Peloton to Garmin Magic :)")

##############################
# Environment Variables Setup
##############################
pathToToken = os.getenv("GCS_TOKEN_PATH") or config.ConfigSectionMap("OUTPUT").get('gcptokenpath');
numActivities = os.getenv("NUM_ACTIVITIES") or 5;
output_directory = os.getenv("OUTPUT_DIRECTORY") or config.ConfigSectionMap("OUTPUT")['directory'];

if pathToToken is not None:
    credentials = service_account.Credentials.from_service_account_file(pathToToken)

    client = storage.Client(
        credentials=credentials,
        project="peloton-to-garmin"
    )
    bucket = client.get_bucket("peloton-output")

def getWorkouts(email = None, password = None):
    userOutputDir = output_directory + os.path.sep + email;
    outputDir = userOutputDir.replace("\"", "")

    api = pelotonApi.PelotonApi(email, password)

    ##############################
    # Main
    ##############################
    numA = numActivities;
    if numActivities is None:
        numA = int(input("How many past activities do you want to grab?  "));

    logger.info("Get latest " + str(numA) + " workouts.")
    workouts = api.getXWorkouts(numA)

    for w in workouts:
        workoutId = w["id"]
        logger.info("Get workout: " + str(workoutId))

        workout = api.getWorkoutById(workoutId)

        logger.info("Get workout samples")
        workoutSamples = api.getWorkoutSamplesById(workoutId)

        logger.info("Get workout summary")
        workoutSummary = api.getWorkoutSummaryById(workoutId)

        logger.info("Writing TCX file")
        try:
            tcxXMLString = tcx_builder.workoutSamplesToTCX(workout, workoutSummary, workoutSamples)

            startTimeInSeconds = workout['start_time']
            ride = workout["ride"] if not workout["peloton"] else workout["peloton"]["ride"]
            
            instructor = ""
            if not ride['instructor']:
                instructor = " with " + ride["instructor"]["first_name"] + " " + ride["instructor"]["last_name"]
            
            cleanedTitle = ride["title"].replace("/","-").replace(":","-")
            filename = "{0}-{1}{2}-{3}.tcx".format(startTimeInSeconds, cleanedTitle, instructor, workout['id'])

            if pathToToken is not None:
                blob=bucket.blob("{0}/{1}".format(email,filename))
                blob.upload_from_string(tcxXMLString, content_type='text/xml')
            else:
                Path(outputDir).mkdir(parents=True, exist_ok=True)
                with open("{0}/{1}".format(outputDir,filename), "w") as text_file:
                    text_file.write(tcxXMLString)
            
        except Exception as e:
            logger.error("Failed to write TCX file for workout {} - Exception: {}".format(workoutId, e))
        

    logger.info("Done!")
    logger.info("Your Garmin TCX files can be found in the Output directory: " + outputDir)

    if pause_on_finish == "true":
        input("Press the <ENTER> key to continue...")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        user_email = sys.argv[1]
        user_password = sys.argv[2]
    else:
        if config.ConfigSectionMap("PELOTON")['email'] is None:
            logger.error("Please specify your Peloton login email in the config.ini file.")
            sys.exit(1)

        if config.ConfigSectionMap("PELOTON")['password'] is None:
            logger.error("Please specify your Peloton login password in the config.ini file.")
            sys.exit(1)

    user_email = config.ConfigSectionMap("PELOTON")['email']
    user_password = config.ConfigSectionMap("PELOTON")['password']

    getWorkouts(user_email, user_password);