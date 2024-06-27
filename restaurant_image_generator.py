import sentry_sdk
from firebase_admin import firestore

import gpt_wrapper
from firebase_helper import firestore_db
from get_restaurant import get_random_restaurant
from stable_diffusion_wrapper import StableDiffusionWrapper
from stable_video_diffusion_wrapper import StableVideoDiffusionWrapper


def _get_prompt_for_restaurant(restaurant):
    prompt = \
        f"@Rufus: please help create a prompt for generating a photo using Stable Diffusion.\n" \
        f"We'd like to see a cute photo of you dining at {restaurant['name']}, " \
        f"with an emphasis on the food and the environment.\n"
    if restaurant['description']:
       prompt += f"{restaurant['name']} is described as '{restaurant['description']}'\n"
    return prompt


def generate_image_url_for_restaurant(restaurant):
    formatted_messages = []

    # Examples
    formatted_messages.append({
        'role': 'user',
        'content': _get_prompt_for_restaurant({
            "name": "Dim Sum House",
            "description": "A modern spin on traditional Chinese with bbq buns, dumplings & noodles in a strip-mall storefront.",
        })
    })
    formatted_messages.append({
        'role': 'assistant',
        'content': "A cinematic photo of a cute Pixar-style rat enjoying hbbq buns, dumplings and noodles at a strip-mall dimsum restaurant. The rat is wearing a lab coat. Dynamic action shot."
    })

    formatted_messages.append({
        'role': 'user',
        'content': _get_prompt_for_restaurant({
            "name": "Wolfsglen",
            "description": "An innovative, thoughtfully sourced fine dining menu & wine list in a polished restaurant.",
        })
    })
    formatted_messages.append({
        'role': 'assistant',
        'content': "A cinematic photo of a cute Pixar-style rat dining at an upscale, modern restaurant. The rat, wearing a lab coat, is engrossed in tasting a gourmet meal made of innovative and thoughtfully sourced ingredients. The background should focus on the polished and elegant environment of the restaurant, including the wine list visible on a nearby table. Dynamic action shot."
    })

    formatted_messages.append({
        'role': 'user',
        'content': _get_prompt_for_restaurant({
            "name": "Sweetgreen",
            "description": "Locavore-friendly counter-serve chain specializing in organic salads & bowls.",
        })
    })
    formatted_messages.append({
        'role': 'assistant',
        'content': "A cinematic photo of a sweet Pixar-style rat enjoying a wholesome meal at a counter-serve chain restaurant, Sweetgreen. The rat is seen wearing a lab coat and is relishing an organic salad bowl. The environment should emphasize the friendly and vibrant atmosphere of Sweetgreen, with a preference for locally sourced, organic ingredients being visible in the image. Dynamic action shot."
    })

    # The real prompt.
    formatted_messages.append({
        'role': 'user',
        'content': _get_prompt_for_restaurant(restaurant)
    })

    response = gpt_wrapper.get_response_for_messages(formatted_messages)

    print('Restaurant image prompt:', response)

    wrapper = StableDiffusionWrapper()
    result = wrapper.run_txt2img_url(response, negative_prompt="stethoscope, laboratory")

    return result


def generate_gif_url_for_restaurant(restaurant):
    image_url = generate_image_url_for_restaurant(restaurant)

    try:
        stable_diffusion_video = StableVideoDiffusionWrapper()
        gif_url = stable_diffusion_video.run_img2gif(image_url)
    except Exception as e:
        gif_url = None
        print("Error generating gif:", e)
        sentry_sdk.capture_exception(e)

    firestore_db.collection("lunch_gifs").add({
        'timestamp': firestore.SERVER_TIMESTAMP,
        "restaurant_name": restaurant["name"],
        'image_url': image_url,
        "gif_url": gif_url,
    })

    if gif_url is None:
        return image_url

    return gif_url


if __name__ == "__main__":
    restaurant = get_random_restaurant()
    image = generate_gif_url_for_restaurant(restaurant)
    print(image)

    #os.makedirs("output", exist_ok=True)
    #image.save(f"output/{uuid.uuid4()}.png")
