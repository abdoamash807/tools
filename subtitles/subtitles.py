import os
import time
import random
import chardet
from google import genai
from google.genai import types


async def load_srt_file(file_path):
    # First, detect the encoding
    with open(file_path, "rb") as f:
        raw_data = f.read()
        encoding_result = chardet.detect(raw_data)
        detected_encoding = encoding_result['encoding']
        confidence = encoding_result['confidence']
    
    print(f"🔍 Detected encoding: {detected_encoding} (confidence: {confidence:.2f})")
    
    # Try the detected encoding first
    encodings_to_try = [detected_encoding, 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings_to_try:
        if encoding is None:
            continue
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
                print(f"✅ Successfully loaded file with {encoding} encoding")
                return content
        except (UnicodeDecodeError, LookupError):
            print(f"❌ Failed to decode with {encoding}")
            continue
    
    # If all else fails, use utf-8 with error handling
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            print("⚠️ Loaded with UTF-8 and replaced invalid characters")
            return content
    except Exception as e:
        raise RuntimeError(f"Could not load file {file_path}: {e}")


def split_srt_blocks(srt_text):
    return srt_text.strip().split("\n\n")


def translate_block_batch(blocks, client, model, max_retries=5):
    srt_batch = "\n\n".join(blocks)

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=f"""Translate the following SRT subtitles from English to Arabic. 
Keep the format including numbers, timestamps, and line breaks. 
Only translate the dialogue.\n\n{srt_batch}"""
                )
            ],
        )
    ]

    config = types.GenerateContentConfig(
        temperature=0.7,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        response_mime_type="text/plain",
        system_instruction=[
            types.Part.from_text(
                text="You are a subtitle translator. Translate English SRT subtitles to Arabic while preserving the SRT format (index numbers, timestamps, and line breaks). Only translate the spoken lines, not numbers or timestamps."
            ),
        ],
    )

    for attempt in range(max_retries):
        try:
            output = ""
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config,
            ):
                output += chunk.text
            return output.strip().split("\n\n")

        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait_time = 2 ** attempt + random.uniform(0, 1)
                print(f"⚠️ Model overloaded. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                raise e

    raise RuntimeError("❌ Max retries exceeded: model still unavailable.")


def generate_translation(srt_content, output_path, batch_size=100):
    client = genai.Client(api_key='AIzaSyCH6qbmbIamMm3ePpBD2Hjq1-HY7rojT6Q')
    model = "gemini-2.0-flash"
    blocks = split_srt_blocks(srt_content)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("")  # clear existing content

    for i in range(0, len(blocks), batch_size):
        batch = blocks[i:i + batch_size]
        print(f"🔁 Translating batch {i} to {i + batch_size}...")

        try:
            translated_blocks = translate_block_batch(batch, client, model)
            with open(output_path, "a", encoding="utf-8") as f:
                f.write("\n\n".join(translated_blocks) + "\n\n")
        except Exception as e:
            print(f"❌ Failed to translate batch {i}: {e}")