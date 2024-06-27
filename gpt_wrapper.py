import json
import time
from typing import List

import openai
import tiktoken

openai.organization = "YOUR_ORG_KEY"
openai.api_key = "YOUR_API_KEY"
model_id = "gpt-4o"


with open('rufus_prompt.txt', "r") as f:
    base_rufus_prompt = f.read()


def _get_token_count(messages):
    encoding = tiktoken.encoding_for_model(model_id)
    total_tokens = 0
    for message in messages:
        total_tokens += len(encoding.encode(message['content']))
    return total_tokens


# Note: gpt-4o supports up to 128,000 tokens
MAX_TOKENS = 10_000


def _sanitize_response(response):
    # Replace some emojis that Rufus gets wrong.

    emoji_mapping = {
        'man_scientist': 'male-scientist',
        'woman_scientist': 'female-scientist',
        'monocle': 'face_with_monocle',
        'magnifying_glass_tilted_left': 'mag',
        'magnifying_glass_tilted_right': 'mag_right',
        'cheese': 'cheese_wedge',
        'orange': 'tangerine',
        'hot_dog': 'hotdog',
        'plate_with_cutlery': 'knife_fork_plate',
        'laptop': 'computer',
        'computer_mouse': 'three_button_mouse',
        'graduation_cap': 'mortar_board',
        'paintbrush': 'lower_left_paintbrush',
        'fountain_pen': 'lower_left_fountain_pen',
        'party_popper': 'confetti_ball',
        'star_struck': 'star-struck',
        'salad': 'green_salad',
        'drum': 'drum_with_drumsticks',
        'policeman': 'cop',
        'beaker': 'alembic',
        'disk': 'floppy_disk',
        'soccer': 'soccer_ball',
        'swimming': 'swimmer',
        'biking': 'bicyclist',
        'mountain_biking': 'mountain_bicyclist',
        'map': 'world_map',
        'cloud_with_rain': 'rain_cloud',
        'wind_face': 'wind_blowing_face',
        'light_bulb': 'bulb',
        'bacterium': 'microbe',
        'detective': 'female-detective',
    }
    for key, value in emoji_mapping.items():
        response = response.replace(f':{key}:', f':{value}:')

    return response


def get_response_for_messages(messages: List[dict]):
    messages.insert(
        0, {
            "role": "system",
            "content": base_rufus_prompt,
        },
    )

    print(json.dumps(messages, indent=2))

    while _get_token_count(messages) > MAX_TOKENS:
        print('token count', _get_token_count(messages), 'messages', len(messages))
        messages.pop(1)

    print('token count', _get_token_count(messages))

    max_retries = 3
    retry_delay = 2  # in seconds
    attempt = 0

    while attempt < max_retries:
        try:
            response = openai.ChatCompletion.create(
                model=model_id,
                messages=messages,
            )

            full_response = response['choices'][0]['message']['content']
            full_response = _sanitize_response(full_response)

            if full_response != "":
                print(f'ChatGPT Response: {full_response}')
                return full_response

        except Exception as ex:
            attempt += 1
            print(f'Error encountered: {ex}. Attempting retry {attempt}/{max_retries}')
            time.sleep(retry_delay)

            if attempt == max_retries:
                raise


if __name__ == "__main__":
    response = get_response_for_messages([
        {
            "role": "user",
            "content": "Hi Rufus! What do you like to do in your free time?",
        },
    ])
    print(response)
