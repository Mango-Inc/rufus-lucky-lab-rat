import os
import uuid
from io import BytesIO
from typing import Optional

import replicate
import requests
from PIL import Image
from replicate.exceptions import ModelError


class StableDiffusionWrapper:

    def __init__(self):
        self.client = replicate.Client(api_token='YOUR_API_TOKEN')

    def run_txt2img_url(self, prompt: str, negative_prompt: Optional[str] = None) -> Image:
        assert prompt is not None

        if negative_prompt is None:
            negative_prompt = ""

        try:
            result = self.client.run(
                "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                input={
                    "width": 1024,
                    "height": 576,
                    "prompt": prompt,
                    "refine": "expert_ensemble_refiner",
                    "scheduler": "K_EULER",
                    "lora_scale": 0.6,
                    "num_outputs": 1,
                    "guidance_scale": 7.5,
                    "apply_watermark": False,
                    "high_noise_frac": 0.8,
                    "negative_prompt": negative_prompt,
                    "prompt_strength": 0.8,
                    "num_inference_steps": 25,
                }
            )
            return result[0]
        except ModelError as e:
            if "NSFW content detected" in str(e):
                return None
            raise e


if __name__ == "__main__":
    wrapper = StableDiffusionWrapper()

    for i in range(1):
        result_url = wrapper.run_txt2img_url(
            "A charming Pixar-style rat delighting in Seoul-style BBQ and teriyaki at an unfussy, walk-up stand, called Gushi. The little scientist rat, wearing a lab coat, should be depicted with big, eager eyes, clearly smitten by the ample portions of food in his plate. The setting should illustrate the informal, yet lively aura of Gushi, with outdoor seating and other customers relishing their meals."
            , negative_prompt="stethoscope, laboratory"
        )

        image = Image.open(BytesIO(requests.get(result_url).content))

        image.show()

        os.makedirs("output", exist_ok=True)
        image.save(f"output/{uuid.uuid4()}.png")
