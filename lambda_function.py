#import json
import logging
import os
#from pprint import pprint
import sys
import traceback
import time

from bs4 import BeautifulSoup

from email import encoders
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS region detail
REGION_NAME = os.environ['REGION_NAME']
BUCKET_NAME = os.environ['BUCKET_NAME']
MAIL_PASS_PATH = os.environ['MAIL_PASS_PATH']
MAIL_FAIL_PATH = os.environ['MAIL_FAIL_PATH']
MAIL_QUEUE_PATH = os.environ['MAIL_QUEUE_PATH']
HTML_FILE_EXT = os.environ['HTML_FILE_EXT']

# Create S3 and ses clients
s3 = boto3.client('s3', region_name=REGION_NAME)
ses = boto3.client('ses', region_name=REGION_NAME)


def lambda_handler(event, context):
    logger.debug("Start")

    # Loop through files in the S3 bucket
    try:
        objects = s3.list_objects(Bucket=BUCKET_NAME)['Contents']
    except:
        traceback.print_exc(file=sys.stdout)
        raise Exception("Could retrieve object list.")

    for file in objects:

        # Check if file extention is html
        logger.debug("Checking S3 object: " + file['Key'])
        if ((file['Key'].endswith(HTML_FILE_EXT)) and (file['Key'].startswith(MAIL_QUEUE_PATH))):
            logger.info("Getting S3 object: " + file['Key'])
            # retrieve html file
            try:
                htmlfile = s3.get_object(Bucket=BUCKET_NAME, Key=file['Key'])
            except:
                traceback.print_exc(file=sys.stdout)
                raise Exception("Could not fetch the S3 object.")

            logger.debug("Reading body.")
            htmlbody = htmlfile['Body'].read().decode()
            logger.debug(htmlbody)

            try:
                soup = BeautifulSoup(htmlbody, "lxml")

                # Extract meta data
                fromAddress = soup.find(
                    "meta", property="og:fromAddress")["content"]
                toAddress = soup.find("meta", property="og:toAddress")[
                    "content"]
                subject = soup.find("meta", property="og:subject")["content"]
                attachmentname = soup.find(
                    "meta", property="og:attachmentName")["content"]
                attachmentfile = soup.find(
                    "meta", property="og:attachmentFile")["content"]
            except:
                moveObjects([file["Key"], MAIL_QUEUE_PATH +
                            attachmentfile["content"]], MAIL_QUEUE_PATH, MAIL_FAIL_PATH)

                traceback.print_exc(file=sys.stdout)
                raise Exception("Could not read the meta info from the HTML.")

            if not fromAddress:
                moveObjects([file["Key"], MAIL_QUEUE_PATH +
                            attachmentfile], MAIL_QUEUE_PATH, MAIL_FAIL_PATH)
                raise Exception("og:fromAddress not set in the meta data.")

            if not toAddress:
                moveObjects([file["Key"], MAIL_QUEUE_PATH +
                            attachmentfile], MAIL_QUEUE_PATH, MAIL_FAIL_PATH)
                raise Exception("og:toAddress not set in the meta data.")

            if not subject:
                moveObjects([file["Key"], MAIL_QUEUE_PATH +
                            attachmentfile], MAIL_QUEUE_PATH, MAIL_FAIL_PATH)
                raise Exception("og:subject not set in the meta data.")

            # The character encoding for the email.
            CHARSET = "UTF-8"

            msg = MIMEMultipart()
            try:
                msg["Subject"] = subject
                msg["From"] = fromAddress
                msg["To"] = toAddress

                # Set message body
                body = MIMEText(htmlbody, "html")
                msg.attach(body)
            except:
                traceback.print_exc(file=sys.stdout)
                moveObjects([file["Key"], MAIL_QUEUE_PATH +
                            attachmentfile], MAIL_QUEUE_PATH, MAIL_FAIL_PATH)
                raise Exception("Could not add body to email.")

            # Create the attachment
            try:
                if attachmentname and (len(attachmentname) > 0):
                    logger.debug("Attempt attachment.")
                    if not attachmentfile:
                        moveObjects([file["Key"], MAIL_QUEUE_PATH +
                                     attachmentfile], MAIL_QUEUE_PATH, MAIL_FAIL_PATH)
                        raise Exception(
                            "og:attachmentName meta is set and requires missing og:attachmentFile meta.")

                    # Attach the file to the mime
                    # In same directory as script
                    filename = attachmentname
                    foundAttach = False
                    for x in range(5):
                        try:
                            logger.info("Try to read attachment.")
                            attachment = getAttachment(attachmentfile)
                            foundAttach = True
                            break
                        except:
                            time.sleep(3)

                    if foundAttach:
                        part = MIMEApplication(attachment['Body'].read())
                        part.add_header("Content-Disposition",
                                        "attachment", filename=filename)
                        msg.attach(part)
                    else:
                        raise Exception(
                            "og:attachmentName could not be found after several attempts")

                if not attachmentname and (len(attachmentname) == 0):
                    logger.debug("No attachment to attach.")

            except:
                traceback.print_exc(file=sys.stdout)
                moveObjects([file["Key"], MAIL_QUEUE_PATH +
                            attachmentfile], MAIL_QUEUE_PATH, MAIL_FAIL_PATH)
                raise Exception("Could not add attachment to email.")

            # Convert message to string and send
            try:
                response = ses.send_raw_email(
                    Source=msg["From"],
                    Destinations=[msg["To"]],
                    RawMessage={"Data": msg.as_string()}
                )
                logger.debug(response)
            except:
                traceback.print_exc(file=sys.stdout)
                moveObjects([file["Key"], MAIL_QUEUE_PATH +
                             attachmentfile], MAIL_QUEUE_PATH, MAIL_FAIL_PATH)
                raise Exception("Could not send SES message.")

            moveObjects([file["Key"], MAIL_QUEUE_PATH +
                         attachmentfile], MAIL_QUEUE_PATH, MAIL_PASS_PATH)
    logger.debug("End")

    return {
        "state": "Success",
    }

# Move the object from the bucket
# The key must contain the path


def moveObjects(keys, oldPath, newPath):
    try:
        for key in keys:
            logger.debug("move key from: "+key)

            # Move the html file
            newKey = key.replace(oldPath, newPath)
            logger.debug("move key to: "+newKey)

            s3r = boto3.resource('s3')
            copy_source = {
                'Bucket': BUCKET_NAME,
                'Key': key
            }
            s3r.meta.client.copy(copy_source, BUCKET_NAME, newKey)

            s3.delete_object(
                Bucket=BUCKET_NAME,
                Key=key
            )

    except:
        logger.debug("Cloud not find, move or delete key:" + newKey)


def getAttachment(attachmentfile):
    return s3.get_object(Bucket=BUCKET_NAME, Key=MAIL_QUEUE_PATH + attachmentfile)
