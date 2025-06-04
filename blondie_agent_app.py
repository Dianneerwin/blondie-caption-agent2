
import os
import re
import base64
from PIL import Image
from datetime import datetime
import csv
import streamlit as st
from openai import OpenAI

# CONFIG
COMIC_FOLDER = "./comics"
OUTPUT_FILE = "blondie_social_calendar.csv"
OPENAI_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Replace with your actual key
client = OpenAI(api_key=OPENAI_API_KEY)

# FUNCTION: Extract date from filename
def extract_date(filename):
    match = re.search(r"Blondie(\d{2})(\d{2})", filename)
    if match:
        month, day = match.groups()
        date = datetime(year=2025, month=int(month), day=int(day))
        return date.strftime("%Y-%m-%d"), date.strftime("%A")
    return None, None

# FUNCTION: Use GPT-4-V to read text from comic image
def extract_comic_text_with_openai(filepath):
    try:
        with open(filepath, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("utf-8")
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {"role": "system", "content": "You're a helpful assistant that reads comic strip text."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Read and transcribe all text from this comic."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]
                }
            ],
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[OpenAI Vision error: {e}]"

# FUNCTION: Generate caption prompt
def generate_caption_prompt(date_str, weekday, comic_text):
    style_guide = """Tone Guidelines:
- Instagram: Cheeky, clever, Gen Z-friendly, pop culture-aware. Use emojis, humor, meme-style language.
- Facebook: Warm, nostalgic, conversational. Designed for fans who grew up reading Blondie.
Examples:
- Comic: Dagwood falls asleep on a sandwich
    - IG: "When your midnight snack turns into a pillow. 🥪😴 #SleepChronicles #SandwichSnoozer"
    - FB: "Dagwood fell asleep ON his sandwich. What’s the weirdest place you’ve ever nodded off?"
"""
    return f"""{style_guide}
Date: {date_str} ({weekday})
Comic Dialogue: {comic_text}

Use the tone guidelines and examples above to generate:
1. Instagram Caption
2. Facebook Caption
"""

# FUNCTION: Generate captions
def generate_captions(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a witty social media copywriter for a classic comic strip."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error generating caption: {e}]"

# STREAMLIT APP
def main():
    st.title("Blondie Social Media Caption Generator (Vision Version)")
    st.write("Upload .tif comics named as BlondieMMDD.tif")

    files = os.listdir(COMIC_FOLDER)
    tif_files = [f for f in sorted(files) if f.lower().endswith(".tif") and "Blondie" in f]

    rows = []
    seen_dates = set()

    for filename in tif_files:
        filepath = os.path.join(COMIC_FOLDER, filename)
        date_str, weekday = extract_date(filename)
        if not date_str or date_str in seen_dates:
            continue
        seen_dates.add(date_str)

        with Image.open(filepath) as img:
            st.image(img, caption=f"{filename} - {date_str} ({weekday})", use_column_width=True)

        comic_text = extract_comic_text_with_openai(filepath)
        st.write(f"**Comic Text:** {comic_text}")

        prompt = generate_caption_prompt(date_str, weekday, comic_text)
        caption_output = generate_captions(prompt)
        editable_caption = st.text_area(f"Edit Captions for {date_str}", value=caption_output, height=200)
        st.write("---")

        rows.append([date_str, weekday, filename, comic_text, editable_caption])

    if st.button("Download CSV"):
        with open(OUTPUT_FILE, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Date", "Weekday", "Filename", "ComicText", "Captions"])
            writer.writerows(rows)
        st.success(f"✅ CSV saved as {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
