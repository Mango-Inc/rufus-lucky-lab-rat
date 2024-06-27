import os
import random
import subprocess
import uuid

import replicate
import requests
from PIL import Image

from firebase_helper import upload_filestream_to_firebase


class StableVideoDiffusionWrapper:

    def __init__(self):
        self.client = replicate.Client(api_token='YOUR_API_TOKEN')

    def run_img2vid(self, image_url) -> Image:

        print("Running img2vid...")

        output = self.client.run(
            "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
            input={
                "cond_aug": 0.02,
                "decoding_t": 14,
                "input_image": image_url,
                "video_length": "25_frames_with_svd_xt",
                "sizing_strategy": "maintain_aspect_ratio",
                "motion_bucket_id": 127,
                "frames_per_second": 15
            }
        )

        os.makedirs("/tmp/stable_diffusion_files", exist_ok=True)
        tmp_path = f"/tmp/stable_diffusion_files/{uuid.uuid4()}.mp4"
        with open(tmp_path, "wb") as f:
            f.write(requests.get(output).content)
        return tmp_path

    @staticmethod
    def _convert_mp4_to_gif_ffmpeg(input_file, output_file):
        # Choose random FPS between 10 and 14. This prevents gifs from syncing up with each other.
        fps = random.uniform(10, 14)

        subprocess.run([
            'ffmpeg',
            '-i', input_file,
            '-vf', f'fps={fps},scale=512:-1:flags=lanczos',
            '-c:v', 'gif',
            output_file
        ], check=True)
        print(f"Conversion successful: {output_file}")

    def run_img2gif(self, image_url, storage_dir="lunch_gifs") -> Image:
        mp4_path = self.run_img2vid(image_url)

        print("Running converting gif to mp4...")
        try:
            gif_path = mp4_path.replace(".mp4", ".gif")
            self._convert_mp4_to_gif_ffmpeg(mp4_path, gif_path)
        finally:
            os.remove(mp4_path)

        # Upload gif to firebase
        try:
            with open(gif_path, "rb") as f:
                return upload_filestream_to_firebase(f, f"{storage_dir}/{uuid.uuid4()}.gif", "image/gif")
        finally:
            os.remove(gif_path)

