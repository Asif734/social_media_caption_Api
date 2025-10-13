#app/services/captions_service.py

import json
import base64
from openai import AsyncOpenAI
from app.core.config import OPENAI_API_KEY
from app.models.captions import CaptionInput, EditRequest

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ---------------------------
# 1️⃣ General caption generator
# ---------------------------
async def generate_caption(prompt: str, max_tokens: int = 150):
    """
    Generate a social media caption quickly using AsyncOpenAI.
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a social media caption generator. "
                        "Respond only in JSON format: "
                        '{"caption": "your caption here", "hashtags": ["#tag1", "#tag2"]}'
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=max_tokens
        )
        content = response.choices[0].message.content
        print("[LLM RAW OUTPUT]", content)
        return json.loads(content)
    except Exception as e:
        print(f"Error generating caption: {e}")
        return {"caption": "", "hashtags": []}


# ---------------------------
# 2️⃣ Image description generator
# ---------------------------
async def describe_image(image_path: str, max_tokens: int = 100):
    """
    Generate a concise yet descriptive caption from an image using GPT-4o-mini.
    Optimized for speed and clarity in social media use cases.
    """
    try:
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Analyze the image and describe it in 1–2 short sentences, "
                                "as if writing a natural social media caption context. "
                                "Avoid technical terms and keep it warm and human-like."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                    ],
                }
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )

        description = response.choices[0].message.content.strip()

        # ✅ Ensure non-empty description
        if not description:
            description = "A visual scene suitable for generating a caption."

        return description

    except Exception as e:
        print(f"⚠️ Error describing image: {e}")
        return "An image was provided but could not be analyzed."

# ---------------------------
# 3️⃣ Build platform-specific prompt
# ---------------------------
def build_prompt_for_platform(input_data: CaptionInput, platform: str) -> str:
    prompt = f"""
You are an AI social media assistant for small business owners.
Your tasks:

-Understand the content, tone, and business type.
-Write a short, engaging caption (1–3 sentences) that fits the platform{platform}.
-Post type: {input_data.post_type}, Topic: {input_data.post_topic}
-Keep it modern, relatable, and relevant. Add a call-to-action if suitable.
-Include 5–10 trending or niche hashtags in JSON format.
"""
    return prompt


# ---------------------------
# 4️⃣ Edit existing caption
# ---------------------------
def build_edit_prompt(edit_data: EditRequest) -> str:
    edit_map = {
        "rephrase": "Rephrase without changing meaning.",
        "shorten": "Make it concise and engaging.",
        "expand": "Add more enticing details.",
        "more formal": "Make it formal and professional.",
        "more casual": "Make it casual and friendly.",
        "more creative": "Make it creative and eye-catching."
    }
    instruction = edit_map.get(edit_data.edit_type.lower(), "Improve the caption to make it more engaging.")

    return (
        f"Edit the social media caption for {edit_data.platform}.\n"
        f"Original caption: \"{edit_data.original_caption}\"\n"
        f"{instruction}\n"
        "Include 5-10 trending or niche hashtags in JSON format"
        "Output JSON: {'caption': 'edited caption', 'hashtags': ['#tag1', '#tag2',...,...,...]}."
    )


