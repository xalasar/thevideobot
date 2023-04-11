import os
import openai
import requests
import re
import shutil
from moviepy.editor import *

# Set your API keys
OPENAI_API_KEY = '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'
PEXELS_API_KEY = 'ehyGJkwi8gUUjseQb1Hf5KpcugxylcoAp9L2eyR3gTRjtzxSL2e6KzPl'

# Configure the OpenAI API client
openai.api_key = OPENAI_API_KEY

# Cache for video scripts
video_script_cache = {}

def get_stock_video(keyword):
    pexels_url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": keyword, "per_page": 1}

    response = requests.get(pexels_url, headers=headers, params=params)
    data = response.json()

    if data and "videos" in data and data["videos"]:
        video_url = data["videos"][0]["video_files"][0]["link"]
        return video_url

    return None

def test_pexels_search(keywords):
    for keyword in keywords:
        video_url = get_stock_video(keyword)
        if video_url:
            print(f"Keyword '{keyword}' found video: {video_url}")
        else:
            print(f"Keyword '{keyword}' did not find any video.")

def generate_video_script(prompt):
    if prompt in video_script_cache:
        return video_script_cache[prompt]

    modified_prompt = (
        f"Please generate a concise video script (60 seconds or less) about '{prompt}'. "
        f"Then, provide a list of 5 relevant nouns that will be easily searchable in a stock video API search. "
        f"Separate the script and the keywords with a line break.\n\n"
        f"Script:\n"
    )
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=modified_prompt,
        max_tokens=800,
        n=1,
        stop=None,
        temperature=0.4,
    )

    response_text = response.choices[0].text.strip()

    # Find the index of the "Keywords:" heading
    keywords_index = response_text.find("Keywords:")

    if keywords_index != -1:
        # Extract the script and keywords after the "Keywords:" heading
        video_script = response_text[:keywords_index].strip()
        keywords = response_text[keywords_index + len("Keywords:"):].strip().split(", ")
    else:
        video_script = response_text
        keywords = []

    video_script_cache[prompt] = (video_script, keywords)
    return video_script, keywords

def create_video(prompt):
    script, keywords = generate_video_script(prompt)
    print(f"Generated script:\n{script}")
    print(f"Generated keywords:\n{', '.join(keywords)}")

    test_pexels_search(keywords)
    video_folder = "generated_videos"
    if os.path.exists(video_folder):
        shutil.rmtree(video_folder)
    os.makedirs(video_folder)

    sentences = re.split(r'(?<=\.)\s+', script)

    video_clips = []
    used_video_urls = set()

    for idx, sentence in enumerate(sentences):
        sentence_text = sentence.strip()

        video_url = None
        while keywords:
            keyword = keywords.pop(0)
            attempts = 0
            while attempts < 5:
                candidate_video_url = get_stock_video(keyword)
                if candidate_video_url and candidate_video_url not in used_video_urls:
                    video_url = candidate_video_url
                    used_video_urls.add(video_url)
                    break
                attempts += 1

            if video_url:
                break

        if video_url:
            video_name = f"scene_{idx + 1}.mp4"
            save_path = os.path.join(video_folder, video_name)
            download_video_file(video_url, save_path)

            clip = VideoFileClip(save_path)
            clip = clip.resize(height=720)
            video_clips.append(clip)

    if video_clips:
        final_video = concatenate_videoclips(video_clips, method="compose")
        final_video = final_video.subclip(0, min(15, final_video.duration))

        words = script.split()
        short_phrases = [word.rstrip() for word in words]

        captions = []
        total_duration = 0
        for i, phrase in enumerate(short_phrases):
            caption_duration = 1
            start_time = total_duration
            end_time = start_time + caption_duration

            caption = TextClip(phrase, fontsize=60, color='white', align='center')
            caption = caption.set_position(('center', 'bottom')).set_duration(caption_duration).set_start(start_time)
            caption = caption.on_color(size=(caption.w + 20, caption.h + 20), color=(0, 0, 0), col_opacity=0.4).set_position(('center', 'bottom'))
            captions.append(caption)

            total_duration += caption_duration

        final_video_with_captions = CompositeVideoClip([final_video] + captions, size=final_video.size).set_duration(total_duration)
        final_video_with_captions.write_videofile("final_video.mp4", codec="libx264", audio_codec="aac")

        print("Video creation complete! Check the final_video.mp4 file.")
    else:
        print("No valid video URLs found for any of the script sentences.")

def download_video_file(url, save_path):
    response = requests.get(url, stream=True)

    with open(save_path, "wb") as f:
        response.raw.decode_content = True
        shutil.copyfileobj(response.raw, f)

project_prompt = input("Enter your video prompt: ")
create_video(project_prompt)