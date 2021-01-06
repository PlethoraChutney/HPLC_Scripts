import sys
import os
from slack import WebClient
from slack.errors import SlackApiError

def get_client(config):
    chromatography_channel = config['chromatography_channel']
    try:
        token = config['token']
        if config['token'] == '':
            print('Config file has empty Slack token. Skiping slack integration.')
            return None
        client = WebClient(token = token)
        client.auth_test()
        print('Slack authentication succeeded')
    except KeyError as e:
        print('Your config file does not have a bot token. Cannot post to slack')
        return None
    except SlackApiError as e:
        if e.response['error'] == 'invalid_auth':
            print('Slack bot authentication failed.')
        else:
            raise e

    return client

def send_graphs(config, client, files):
    chromatography_channel = config['chromatography_channel']
    client.chat_postMessage(channel = chromatography_channel, text = 'A chromatography run has completed!')
    for file in files:
        client.files_upload(
            channels = chromatography_channel,
            file = file
        )