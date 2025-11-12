#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr  5 17:35:52 2021

@author: nlourie
"""


import json
import logging
import os

# needed for email
import smtplib
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# needed for slack
import requests
import slack_sdk
import slack_sdk.errors
import yaml

# add the wsp directory to the PATH
code_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
wsp_path = code_path + "/wsp"
sys.path.insert(1, wsp_path)
print(f"wsp_path = {wsp_path}")


class SlackDispatcher(object):
    def __init__(self, auth_config, logger=None):
        self.auth_config = auth_config
        self.logger = logger
        self.client = slack_sdk.WebClient(
            token=self.auth_config.get("slackbot_token", "")
        )

    def log(self, msg, level=logging.INFO, verbose=False):
        if self.logger is None:
            if verbose:
                print(msg)
            else:
                pass
        else:
            self.logger.log(level=level, msg=msg)

    def post(self, channel_list, msg, verbose=False):

        # allow just a single address, in addition to a list
        if type(channel_list) is str:
            channel_list = [channel_list]

        for channel in channel_list:

            try:
                slack_data = dict({"text": msg})
                webhook_url = self.auth_config["slackbot_webhooks"][channel]

                response = requests.post(
                    webhook_url,
                    data=json.dumps(slack_data),
                    headers={"Content-Type": "application/json"},
                )

                status_code = response.status_code
                reply_text = response.text

                # log the post
                self.log(
                    f"SlackDispatcher: posted slack message to {channel}. Got status code {status_code}: {reply_text}",
                    verbose=verbose,
                )

            except Exception as e:
                status_code = -999
                reply_text = e

                # log the post failure
                self.log(
                    f"SlackDispatcher: failed to post slack message to {channel}. Got status code {status_code}: {reply_text}",
                    verbose=verbose,
                )
        # return status_code, reply_text

    def postImage(self, channel_list, filepath, msg="", verbose=False):
        """
        Post an image to the channel using the new Slack file upload API.
        Uses files.getUploadURLExternal and files.completeUploadExternal instead
        of the deprecated files.upload method.

        Note: channel can be either a channel name (e.g., 'winter_observatory')
        or a channel ID (e.g., 'C1234567890')
        """
        # allow just a single address, in addition to a list
        if type(channel_list) is str:
            channel_list = [channel_list]

        for channel in channel_list:
            if verbose:
                self.log(f"posting image to channel {channel}", verbose=verbose)

            try:
                # Get file info
                filename = os.path.basename(filepath)
                filesize = os.path.getsize(filepath)

                # Map channel name to ID using auth config
                # Channel IDs start with 'C', 'D', or 'G'
                if not channel.startswith(("C", "D", "G")):
                    # This is a channel name, look it up in the config
                    channel_id = self.auth_config.get("slackbot_channel_id", {}).get(
                        channel
                    )
                    if channel_id is None:
                        raise Exception(
                            f"Could not find channel ID for channel '{channel}' in auth_config['slackbot_channel_id']"
                        )

                    if verbose:
                        self.log(
                            f"Mapped channel '{channel}' to ID {channel_id}",
                            verbose=verbose,
                        )
                else:
                    # Already a channel ID
                    channel_id = channel

                # Step 1: Get upload URL
                upload_url_response = self.client.files_getUploadURLExternal(
                    filename=filename, length=filesize
                )

                upload_url = upload_url_response["upload_url"]
                file_id = upload_url_response["file_id"]

                if verbose:
                    self.log(f"Got upload URL and file_id: {file_id}", verbose=verbose)

                # Step 2: Upload the file to the URL
                with open(filepath, "rb") as file_content:
                    upload_response = requests.post(
                        upload_url,
                        data=file_content.read(),
                        headers={"Content-Type": "application/octet-stream"},
                    )

                if upload_response.status_code != 200:
                    raise Exception(
                        f"File upload failed with status code {upload_response.status_code}"
                    )

                if verbose:
                    self.log(f"File uploaded successfully", verbose=verbose)

                # Step 3: Complete the upload
                complete_response = self.client.files_completeUploadExternal(
                    files=[{"id": file_id, "title": filename}],
                    channel_id=channel_id,
                    initial_comment=msg,
                )

                self.log(f"Successfully uploaded file to {channel}", verbose=verbose)
                if verbose:
                    self.log(complete_response, verbose=verbose)

            except slack_sdk.errors.SlackApiError as e:
                self.log(
                    f"Error uploading file: {e.response['error']}", verbose=verbose
                )
            except Exception as e:
                self.log(f"Error uploading file: {str(e)}", verbose=verbose)


class EmailDispatcher(object):
    def __init__(self, auth_config, logger=None):

        self.auth_config = auth_config
        self.logger = logger

        # set up the sending account
        try:
            self.setupSender(
                sender_email=self.auth_config["email"]["USERNAME"],
                password=self.auth_config["email"]["PASSWORD"],
            )
        except:
            pass

    def log(self, msg, level=logging.INFO):
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    def setupSender(self, sender_email, password):
        self.sender_email = sender_email
        self.__password__ = password

    def send(self, recipient_list, subject, message):
        # allow just a single address, in addition to a list
        if type(recipient_list) is str:
            recipient_list = [recipient_list]
        # print(f'Recipient list = {recipient_list}')
        for receiver_email in recipient_list:
            try:
                # set up the email
                email = MIMEMultipart("alternative")
                email["Subject"] = subject
                email["From"] = self.sender_email
                email["To"] = receiver_email
                # add the body of the email
                email.attach(MIMEText(message, "plain"))

                # Create secure connection with server and send email
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                    server.login(self.sender_email, self.__password__)
                    server.sendmail(
                        self.sender_email, receiver_email, email.as_string()
                    )
                # Make a note that the email was sent
                self.log(f"EmailDispatcher: sent alert email to {receiver_email}")

            except Exception as e:
                self.log(f"Could not send alert email to user {receiver_email}: {e}")


class AlertHandler(object):

    def __init__(self, user_config, alert_config, auth_config):

        self.alert_config = alert_config
        self.auth_config = auth_config
        self.user_config = user_config

        # set up the dispatchers
        self.slacker = SlackDispatcher(self.auth_config)
        self.emailer = EmailDispatcher(self.auth_config)

    def email_group(self, group, subject, message):
        recipient_list = []
        for user in self.user_config["users"]:
            try:
                user_groups = self.user_config["users"][user]["groups"]
                if (
                    (group in user_groups)
                    or ("sudo" in user_groups)
                    or ("all" in group)
                ):
                    email_addresses = self.user_config["users"][user]["email"]
                    for email_address in email_addresses:
                        recipient_list.append(email_address)
            except:
                pass
        # now send the email
        self.emailer.send(recipient_list, subject, message)

    def text_group(self, group, subject, message):
        recipient_list = []
        for user in self.user_config["users"]:
            try:
                user_groups = self.user_config["users"][user]["groups"]
                if (
                    (group in user_groups)
                    or ("sudo" in user_groups)
                    or ("all" in group)
                ):
                    number = str(self.user_config["users"][user]["phone"]["number"])
                    carrier = self.user_config["users"][user]["phone"]["carrier"]
                    domain = self.alert_config["carrier_emails"][carrier]["domain"]
                    email_address = number + "@" + domain
                    recipient_list.append(email_address)
            except:
                pass
        # now send the email
        self.emailer.send(recipient_list, subject, message)

    def slack_message_group(self, group, message):
        recipient_list = []
        for user in self.user_config["users"]:
            try:
                user_groups = self.user_config["users"][user]["groups"]
                if (
                    (group in user_groups)
                    or ("sudo" in user_groups)
                    or ("all" in group)
                ):
                    slack_username = self.user_config["users"][user]["slack"]
                    recipient_list.append(slack_username)
            except:
                pass
        # now send the email
        self.slacker.post(recipient_list, message)

    def slack_log(self, message, group=None, verbose=False):
        # just post a message to the #winter_observatory channel
        # if a group is specified users from that group will be mentioned, eg @username
        mentions = ""

        if not group is None:
            # if is a specified group to tag, try to tag everybody in the group
            for user in self.user_config["users"]:
                try:
                    user_groups = self.user_config["users"][user]["groups"]
                    if (
                        (group in user_groups)
                        or ("sudo" in user_groups)
                        or ("all" in group)
                    ):
                        slack_username = self.user_config["users"][user]["slack"]
                        mentions += " <@" + slack_username + "> "
                except:
                    pass

        full_message = message + mentions
        # now post the message
        self.slacker.post("winter_observatory", full_message, verbose=verbose)

    def slack_postImage(self, filepath, message="", group=None, verbose=False):
        #    def postImage(self, filepath, msg = '', verbose = False):
        # if a group is specified users from that group will be mentioned, eg @username
        mentions = ""

        if not group is None:
            # if is a specified group to tag, try to tag everybody in the group
            for user in self.user_config["users"]:
                try:
                    user_groups = self.user_config["users"][user]["groups"]
                    if (
                        (group in user_groups)
                        or ("sudo" in user_groups)
                        or ("all" in group)
                    ):
                        slack_username = self.user_config["users"][user]["slack"]
                        mentions += " <@" + slack_username + "> "
                except:
                    pass

        full_message = message + mentions
        # now post the message
        channel = "winter_observatory"
        self.slacker.postImage(channel, filepath, full_message, verbose=verbose)


if __name__ == "__main__":

    auth_config_file = wsp_path + "/credentials/authentication.yaml"
    user_config_file = wsp_path + "/credentials/alert_list.yaml"
    alert_config_file = wsp_path + "/config/alert_config.yaml"

    auth_config = yaml.load(open(auth_config_file), Loader=yaml.FullLoader)
    user_config = yaml.load(open(user_config_file), Loader=yaml.FullLoader)
    alert_config = yaml.load(open(alert_config_file), Loader=yaml.FullLoader)

    alertHandler = AlertHandler(user_config, alert_config, auth_config)

    subject = "Test Alert: "
    group = "operator"
    message = (
        ":redsiren: This is a test of the WINTER emergency alert system :banana-dance:"
    )
    message += f' you have been tagged due to membership in the group: "{group}"'
    # alertHandler.email_group(group, subject, message)
    # alertHandler.text_group(group,subject, message)
    alertHandler.slack_message_group(group, message)
    # alertHandler.slack_log('just logging a normal old message', group = None)
    # alertHandler.slack_log(message, group = group)

    """
    group = 'announcements'
    message = 'This is a test of the WINTER emergency alert system'
    alertHandler.email_group(group, subject, message)
    """
    # %%
    # lastimagejpg = os.path.join(os.getenv("HOME"), 'data','last_image.jpg')

    # alertHandler.slack_postImage(lastimagejpg, message = 'here is the last image taken by the observatory')
