#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr  5 17:06:31 2021

gmail alert system test

The code is shamelessly copied from here:
    https://realpython.com/python-send-email/

Note the texts come in the best if you enable show subject field:
    https://www.idownloadblog.com/2019/08/02/add-text-message-subject-line-messages-app/#:~:text=To%20enable%20this%20feature%20in,line%20field%20in%20the%20text.

@author: nlourie
"""

import os
import yaml
import sys
import logging

# add the wsp directory to the PATH
code_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
wsp_path = code_path + '/wsp'
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailDispatcher(object):
    def __init__(self, auth_config, logger = None):
        
        self.auth_config = auth_config
        self.logger = logger
        
        # set up the sending account
        try:
            self.setupSender(sender_email = self.auth_config['email']['USERNAME'], password = self.auth_config['email']['PASSWORD'])
        except:
            pass
        
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)  
        
    def setupSender(self, sender_email, password): 
        self.sender_email = sender_email
        self.__password__ = password
    
    def send(self,recipient_list, subject, message):
        # allow just a single address, in addition to a list
        if type(recipient_list) is str:
            recipient_list = [recipient_list]
        
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
                self.log(f'EmailDispatcher: sent alert email to {receiver_email}')
                
            except Exception as e:
                self.log(f'Could not send alert email to user {receiver_email}: {e}')
                         
if __name__ == '__main__':

    auth_config_file  = wsp_path + '/credentials/authentication.yaml'
    alert_config_file = wsp_path + '/credentials/alert_list.yaml'
    
    
    auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
    alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)
    
    emailDispatcher = EmailDispatcher(auth_config)
    
    subject = "TEST ALERT"
    receiver_email = "nate.lourie@gmail.com"
    message = "This is a test of the WINTER email alert system. \nNo actions are requested at this time."
    
    emailDispatcher.send(receiver_email, subject, message)
        
