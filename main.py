import datetime
import json

import holidays
from flask import jsonify
import os

from slack_sdk import WebClient

import gpt_wrapper

from firebase_helper import firestore_db
from get_restaurant import get_random_restaurant
from restaurant_image_generator import generate_gif_url_for_restaurant


slack_token = 'YOUR_SLACK_TOKEN'
slack_client = WebClient(token=slack_token)

bot_user_id = slack_client.auth_test().get('user_id')


displayname_cache = {}


def _get_displayname(user_id):
    if user_id in displayname_cache:
        return displayname_cache[user_id]

    user_info = slack_client.users_info(user=user_id).data
    user_name = user_info['user']['profile']['display_name']
    displayname_cache[user_id] = user_name
    return user_name


def _response_for_slack_messages(slack_messages):
    formatted_messages = []

    for message in slack_messages:

        # Check if message is from the bot itself
        if message.get('user') == bot_user_id or message.get('subtype') == 'bot_message':
            formatted_messages.append({
                'role': 'assistant',
                'content': message['text']
            })
        else:

            # Fetch the user's info
            display_name = _get_displayname(message['user'])

            formatted_messages.append({
                'role': 'user',
                'content': f"{display_name}: {message['text']}"
            })

    print('formatted messages', formatted_messages)

    return gpt_wrapper.get_response_for_messages(formatted_messages)


MESSAGE_LIMIT = 20


def _fetch_recent_messages(channel_id, thread_ts):
    result = slack_client.conversations_replies(channel=channel_id, ts=thread_ts, limit=MESSAGE_LIMIT)

    messages = result.data.get('messages')
    reached_end_of_thread = len(messages) < MESSAGE_LIMIT
    if reached_end_of_thread:
        # Prepend prior channel history (only the ones from before the thread started)
        result = slack_client.conversations_history(channel=channel_id, limit=MESSAGE_LIMIT, latest=thread_ts)
        prior_messages = result.data.get('messages')
        prior_messages.reverse()
        messages = prior_messages + messages

    return messages[-MESSAGE_LIMIT:]


def _reply_to_message(channel_id, thread_ts, debug=False):
    messages = _fetch_recent_messages(channel_id, thread_ts)

    print('messages', messages)

    if not debug and messages[-1]['user'] == bot_user_id:
        raise 'Illegal state: responding to bot message!'

    response = _response_for_slack_messages(messages)

    slack_client.chat_postMessage(channel=channel_id, text=response, thread_ts=thread_ts)


def on_slack_mention(request):
    """
    Invoked via Slack callback when a user messages Rufus.
    """
    print(f"Version: {os.environ.get('K_REVISION')}")
    data = request.get_json()

    # Respond to the URL verification challenge (used for installing the callback in Slack).
    if data['type'] == 'url_verification':
        return jsonify({'challenge': data['challenge']})

    if data['type'] != 'event_callback':
        print('not an event_callback, aborting')
        print(data['type'])
        return jsonify({'status': 'ok'})

    event_type = data['event']['type']
    if not (event_type == 'app_mention' or event_type == 'message'):
        print('not an app_mention or message, aborting')
        print(event_type)
        return jsonify({'status': 'ok'})

    # Ignore message_changed events (these are generated when Rufus edits his own messages)
    if data['event'].get('subtype') == 'message_changed':
        return jsonify({'status': 'ok'})

    # If the message is from the bot itself, ignore it
    if data['event']['user'] == bot_user_id:
        print('bot message, aborting 1')
        return jsonify({'status': 'ok'})

    event_id = data['event_id']

    processed_event = firestore_db.collection('processed_events').document(event_id).get()

    if processed_event.exists:
        print(f"Event {event_id} was already processed, aborting")
        return jsonify({'status': 'ok'})
    else:
        # mark event as processed
        firestore_db.collection('processed_events').document(event_id).set({'processed': True})

    channel_id = data['event']['channel']

    if 'thread_ts' in data['event']:
        # Respond as part of existing thread
        thread_ts = data['event']['thread_ts']
    else:
        # Start a new thread
        thread_ts = data['event']['ts']

    if data['event'].get('channel_type') == 'im' or f'<@{bot_user_id}>' in data['event']['text']:
        print(f"Received data: {data}")
        print(f"Channel ID: {channel_id}, thread_ts: {thread_ts}")
        _reply_to_message(channel_id, thread_ts)

    return jsonify({'status': 'ok'})


def daily_lunch_bell(_):
    """
    Invoked via daily cron job at noon, to send lunch suggestions to #sticky_rice.
    """
    print(f"Version: {os.environ.get('K_REVISION')}")

    us_holidays = holidays.US()
    if datetime.date.today() in us_holidays:
        print(f"Today is a holiday. Skipping lunch suggestions.")
        return json.dumps({'status': 'ok'})

    formatted_messages = []

    formatted_messages.append({
        'role': 'user',
        'content': f"@Rufus: please pretend you will join us for lunch today "
                   f"(we wish you could, if only you had a body!). \n"
                   f"Please introduce the two options for lunch, perhaps as a short poem? \n"
                   f"Format the name of the restaurants in *bold*."
    })

    restaurant_one = get_random_restaurant()
    restaurant_two = get_random_restaurant()

    formatted_messages.append({
        'role': 'system',
        'content': f"Today's options are:\n"
                   f"- *{restaurant_one['name']}*: {restaurant_one['description']}\n"
                   f"- *{restaurant_two['name']}*: {restaurant_two['description']}\n"
    })

    print('formatted messages', formatted_messages)

    response = gpt_wrapper.get_response_for_messages(formatted_messages)

    # Add links to the restaurants
    response = response.replace(
        f"*{restaurant_one['name']}*",
        f"*<{restaurant_one['URL']}|{restaurant_one['name']}>*"
    )
    response = response.replace(
        f"*{restaurant_one['name']}'s*",
        f"*<{restaurant_one['URL']}|{restaurant_one['name']}'s>*"
    )
    response = response.replace(
        f"*{restaurant_two['name']}*",
        f"*<{restaurant_two['URL']}|{restaurant_two['name']}>*"
    )
    response = response.replace(
        f"*{restaurant_two['name']}'s*",
        f"*<{restaurant_two['URL']}|{restaurant_two['name']}'s>*"
    )

    gif_url1 = generate_gif_url_for_restaurant(restaurant_one)
    gif_url2 = generate_gif_url_for_restaurant(restaurant_two)

    if os.environ.get('K_REVISION') is None:
        channel = '#rufus-testing'
    else:
        channel = '#sticky_rice'

    slack_client.chat_postMessage(
        channel=channel,
        text=response,
        unfurl_links=False,
        attachments=[
            {"image_url": gif_url1, "text": restaurant_one['name']},
            {"image_url": gif_url2, "text": restaurant_two['name']}
        ]
    )
    
    return json.dumps({'status': 'ok'})


if __name__ == "__main__":
    daily_lunch_bell(None)

    #_reply_to_message('C05L497EHNG', '1713337397.905189', debug=True)
    """messages = _fetch_recent_messages('D05FYB0F7V0', '1689133447.953969')
    for message in messages:
        print('-----------------')
        print(message['text'])"""

