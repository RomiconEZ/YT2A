import yt_dlp as youtube_dl
from pytube import YouTube
from src.youtube2text.youtube2text import Youtube2Text
import re
import pandas as pd
from langdetect import detect

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
        langs = ["ru", "en", "a.ru", "a.en"]

        for lang in langs:
            if lang in dict_of_lang_subtitles:
                subtitles = yt.captions[lang].generate_srt_captions()
                df_yt = parse_subtitles(subtitles)
                df_yt.to_csv('yt_sub.csv')
                break
        #else:
        if lang_for_vid is not None:
            df = generate_subtitles(lang=lang_for_vid, yt=yt)
            df.to_csv('gen_sub.csv')
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


url = "https://www.youtube.com/watch?v=wddeVYrg-dk"

import subprocess

start_time = "00:01:30.000"  # Время, на котором нужно извлечь кадр

ydl_opts = {
    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",  # Определение формата видео
    "quiet": True,  # Отключение вывода информации от youtube_dl
}

with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    info_dict = ydl.extract_info(url, download=False)
    formats = info_dict.get("formats", [])
    mp4_formats = [format for format in formats if format.get("ext") == "mp4"]
    video_url = None
    max_quality = max(mp4_formats, key=lambda x: x["quality"])
    video_url = max_quality["url"]
    print(max_quality)

if video_url:
    ffmpeg_command = f'ffmpeg -ss {start_time} -i "{video_url}" -vframes 1 output.jpg'
    subprocess.run(ffmpeg_command, shell=True)

# if video_url:
#     random_name = "output.mp4"  # Случайное имя файла для сохранения видео
#     ffmpeg_command = f'ffmpeg -ss {start_time} -i "{video_url}" -t 1 -c copy "{random_name}"'
#     subprocess.run(ffmpeg_command, shell=True)
#
#     # Извлечение кадра из сохраненного видео
#     ffmpeg_command = f'ffmpeg -i "{random_name}" -ss 00:00:01 -vframes 1 output.jpg'
#     subprocess.run(ffmpeg_command, shell=True)
#
#     # Удаление временного видео
#     subprocess.run(f'rm "{random_name}"', shell=True)
# else:
#     print("Не удалось найти URL-адрес видео в подходящем формате.")


#get_subtitles_for_yt(url)
