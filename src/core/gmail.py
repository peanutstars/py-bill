# -*- coding: utf-8 -*-

import base64
import httplib2
import os
import sys

from oauth2client.file import Storage
from oauth2client import client, tools
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apiclient import errors, discovery



INFO = print
CLIENT_SECRET_FILE = 'client_secret_846592600740-adtej5v1a4qtvburl8f3jh5r4q0u4kqr.apps.googleusercontent.com.json'


class Gmail:
    @classmethod
    def credentials(cls):
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir, 'gmail-send.json')
        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            SCOPES = 'https://www.googleapis.com/auth/gmail.send'
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            # Added '--noauth_local_webserver' option
            # It prevent to run the web browser for the autherity process.
            sys.argv.append('--noauth_local_webserver')
            credentials = tools.run_flow(flow, store)
        return credentials

    @classmethod
    def to_build_message(cls, to, subject, msghtml, msgtext):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = None
        msg['To'] = to
        if msgtext:
            msg.attach(MIMEText(msgtext, 'plain'))
        msg.attach(MIMEText(msghtml, 'html'))
        raw = base64.urlsafe_b64encode(msg.as_bytes())
        raw = raw.decode()
        body = {'raw': raw}
        return body

    @classmethod
    def send_internal(cls, service, user_id, message):
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        INFO('Message Id: %s' % message['id'])
        return message

    @classmethod
    def send(cls, receiver, subject, msghtml, msgtext=None):
        credentials = cls.credentials()
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('gmail', 'v1', http=http)
        msgchunk = cls.to_build_message(receiver, subject, msghtml, msgtext)
        return cls.send_internal(service, "me", msgchunk)


if __name__ == '__main__':
    def main():
        recipients = ['peanutstars.job@gmail.com']
        to = ', '.join(recipients)
        subject = "Title: Send Mail 5"
        msghtml = "Hi<br/>Html Email<br/><br/>Sent from Gmail"
        msgtext = None
        Gmail.send(to, subject, msghtml, msgtext)
    main()
