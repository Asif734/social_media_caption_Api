#app/api/v1/endpoints/caption.py

import os
import uuid
import re
import asyncio
from typing import List, Optional, Union

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse

from app.models.captions import CaptionInput, EditRequest
from app.services.captions_service import (
    generate_caption,
    build_prompt_for_platform,
    build_edit_prompt,
    describe_image
)

router = APIRouter()
TEMP_DIR = os.path.join(os.getcwd(), "temp_images")
os.makedirs(TEMP_DIR, exist_ok=True)


@router.post(
    "/caption",
    summary="Generate or edit captions with optional images",
    response_description="Generated or edited caption and hashtags"
)
async def merged_caption_endpoint(
    platforms: List[str] = Form(...),
    post_type: Optional[str] = Form(None),
    post_topic: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    edit_type: Optional[str] = Form(None),
    image: Union[UploadFile, str] = File(None)
):
    """
    Handles both caption generation and editing.
    - If edit_type is empty → generate new captions
    - If edit_type is provided → edit the existing caption while keeping hashtags
    """

    # ---------------------------

    TEMP_DIR = os.path.join(os.getcwd(), "temp_images")
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Fixed filename for uploaded image
    IMAGE_FILENAME = "current_post_image.jpg"

    if image:
        image_path = os.path.join(TEMP_DIR, IMAGE_FILENAME)
        with open(image_path, "wb") as f:
            f.write(await image.read())
        
        # Generate description using the overwritten file
        description =await describe_image(image_path)

        # Merge with post_topic
        if post_type and post_topic:
            post_topic = f"{post_type} {post_topic}. Image: {description}"
        elif post_type:
            post_topic = f"{post_type}. Image: {description}"
        elif post_topic:
            post_topic = f"{post_topic}. Image: {description}"
        else:
            post_topic = f"Image: {description}"

    # ---------------------------
    # 2️⃣ Generate new captions
    # ---------------------------
    if not edit_type or edit_type.strip() == "":
        input_data = CaptionInput(
            platforms=platforms,
            post_type=post_type,
            post_topic=post_topic
        )

        tasks = [
            generate_caption(build_prompt_for_platform(input_data, platform))
            for platform in platforms
        ]
        outputs = await asyncio.gather(*tasks, return_exceptions=True)

        results = {}
        for platform, output in zip(platforms, outputs):
            if isinstance(output, Exception):
                results[platform.lower()] = {"caption": "", "hashtags": [], "error": str(output)}
            else:
                # Clean caption text
                raw_caption = output.get("caption", "").strip()
                cleaned_lines = [
                    re.sub(r'\s+', ' ', re.sub(r'#\w+', '', line)).strip()
                    for line in raw_caption.splitlines()
                ]
                cleaned_caption = "\n".join([l for l in cleaned_lines if l])

                hashtags = output.get("hashtags", [])
                results[platform.lower()] = {"caption": cleaned_caption, "hashtags": hashtags}

        return JSONResponse(content=results)

    # ---------------------------
    # 3️⃣ Edit existing caption
    # ---------------------------
    else:
        if not caption:
            raise HTTPException(
                status_code=400,
                detail="Caption is required when edit_type is provided"
            )

        edit_data = EditRequest(
            platform=platforms,
            original_caption=caption,
            edit_type=edit_type
        )

        try:
            prompt = build_edit_prompt(edit_data)
            llm_output = await generate_caption(prompt)

            if not isinstance(llm_output, dict) or "caption" not in llm_output:
                raise ValueError("LLM returned unexpected JSON structure")

            # Clean caption
            raw_caption = llm_output.get("caption", "").strip()
            cleaned_lines = [
                re.sub(r'\s+', ' ', re.sub(r'#\w+', '', line)).strip()
                for line in raw_caption.splitlines()
            ]
            edited_caption = "\n".join([l for l in cleaned_lines if l])

            # Keep original hashtags if available
            hashtags = getattr(edit_data, "hashtags", []) or llm_output.get("hashtags", [])

            return JSONResponse(content={"caption": edited_caption, "hashtags": hashtags})

        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"LLM processing error: {ve}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


