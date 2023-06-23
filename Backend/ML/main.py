import yt_dlp as youtube_dl
from pytube import YouTube
from src.youtube2text.youtube2text import Youtube2Text
import re
import pandas as pd
from langdetect import detect
import openai

openai.api_key = "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"

# a.ru - автоматически сгенерированные английские
# ru - русский
# en - английский

def get_lang_clean_name(lang_name: str) -> str:
    """
    Получение чистого названия для языка
    """
    if "." in lang_name:
        return lang_name.split(".", 1)[1]
    else:
        return lang_name

def detect_language(text):
    lang = detect(text)
    if lang == "ru":
        return "ru-RU"
    elif lang == "eng":
        return "en-US"
    else:
        return None

def generate_subtitles(lang, yt=None, url=None):
    converter = Youtube2Text()
    df = converter.url2text(urlpath=url, audioformat="flac", yt=yt, lang=lang)
    return df


def detect_lang_for_vid(dict_of_lang_subtitles,title):
    automatic_langs = {"a.ru": "ru-RU", "a.en": "en-US"}
    for lang in automatic_langs.keys():
        if lang in dict_of_lang_subtitles:
            return automatic_langs[lang]
    return detect_language(title)

def get_subtitles_for_yt(link: str):
    """
    Получение субтитров для yt видео
    """

    try:
        yt = YouTube(link)
        dict_of_lang_subtitles = yt.captions
        title = yt.title
        lang_for_vid = detect_lang_for_vid(dict_of_lang_subtitles,title)
        print(f"ЯЗЫК: {lang_for_vid}")
        langs = ["ru", "en"]

        for lang in langs:
            if lang in dict_of_lang_subtitles:
                subtitles = yt.captions[lang].generate_srt_captions()

                # response = openai.ChatCompletion.create(
                #     model="gpt-3.5-turbo",
                #     messages=[
                #         {"role": "user",
                #          "content": f"Based on the subtitles to the video, for each of which there is a number, start time, end time and text. Generate text divided into chapters from subtitles without changing their sequelity and meaning, chapters no more than 10, and specify the start time and the end date for chapters. You cannot change the text too much. Correct the subtitle errors. In the next message I will send the subtitles from which to compose the text. Give me the answer clearly in the format in which you get the subtitles"},
                #         {"role": "user",
                #          "content": f"{subtitles}"}
                #     ]
                # )
                # # print response
                # content_value = response["choices"][0]["message"]["content"]
                # print(content_value)

                df_yt = parse_subtitles(subtitles)
                df_yt.to_csv('yt_sub.csv')
                break

        else:
            if lang_for_vid is not None:
                #df = generate_subtitles(lang=lang_for_vid, yt=yt)
                #df.to_csv('gen_sub.csv')
                print('save to csv')
    except Exception as e:
        print("Произошла ошибка:", e)



def parse_subtitles(subtitles_string):
    lines = subtitles_string.strip().split('\n\n')
    data = []

    for line in lines:
        parts = line.split('\n')
        index = parts[0]

        time_regex = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})')
        time_match = time_regex.search(parts[1])
        start_time = time_match.group(1)
        end_time = time_match.group(2)

        text = ' '.join(parts[2:])

        data.append((text, start_time, end_time))

    df = pd.DataFrame(data, columns=['text', 'start_time', 'end_time'])
    return df


url = "https://www.youtube.com/watch?v=_BD2qY7MYXY&list=PL6Nx1KDcurkCkGiG0hKWtBOQoDqnIBf9E&index=6"

import subprocess

def extract_picture_from_yt_video(url:str,start_time:str = "00:00:00.000", nm_pct_with_ext:str= "output.jpg"):
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",  # Определение формата видео
        "quiet": True,  # Отключение вывода информации от youtube_dl
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        formats = info_dict.get("formats", [])
        mp4_formats = [format for format in formats if format.get("ext") == "mp4"]
        max_quality = max(mp4_formats, key=lambda x: x["quality"])
        video_url = max_quality["url"]
        print(max_quality)

    if video_url:
        ffmpeg_command = f'ffmpeg -ss {start_time} -i "{video_url}" -frames:v 1 -update 1 -y {nm_pct_with_ext}'
        subprocess.run(ffmpeg_command, shell=True)

#extract_picture_from_yt_video(url, start_time = "00:03:00.000")

get_subtitles_for_yt(url)

#openai part




