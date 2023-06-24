from typing import Any
import yt_dlp as youtube_dl
from pandas import DataFrame
from pytube import YouTube
from src.youtube2text.youtube2text import Youtube2Text, merge_rows
import re
from langdetect import detect
import openai
import subprocess
from docx import Document
from docx.shared import Inches
from PIL import Image
import pandas as pd
import tiktoken

openai.api_key = "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"
url = "https://www.youtube.com/watch?v=YCvy8OFfyS4"
encoding = tiktoken.get_encoding("cl100k_base")

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


def detect_lang_for_vid(dict_of_lang_subtitles, title):
    automatic_langs = {"a.ru": "ru-RU", "a.en": "en-US"}
    for lang in automatic_langs.keys():
        if lang in dict_of_lang_subtitles:
            return automatic_langs[lang]
    return detect_language(title)


def concatenate_text(df):
    concatenated_text = ""

    # Проходимся по каждой строке датафрейма
    for index, row in df.iterrows():
        text = row["text"]

        # Удаляем все вхождения ".." из текста
        cleaned_text = text.replace("..", "")

        # Объединяем очищенный текст с предыдущими объединенными строками
        concatenated_text += cleaned_text

    # Возвращаем объединенный текст в виде строки
    return concatenated_text


def remove_rows_without_letters_and_numbers(df):
    # Создаем пустой список для хранения индексов строк, которые нужно удалить
    rows_to_remove = []

    # Проходимся по каждой строке датафрейма
    for index, row in df.iterrows():
        text = row["text"]

        # Проверяем, содержит ли поле "text" буквы, цифры или символы кириллицы
        if not re.search('[a-zA-Zа-яА-Я0-9]', text):
            rows_to_remove.append(index)

    # Удаляем строки из датафрейма по полученным индексам
    df = df.drop(rows_to_remove)

    return df


def create_annotation(str, limit_word):
    # encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    # tokens = encoding.encode(str)[:2000]
    # comp_str = encoding.decode(tokens)
    # print(comp_str)

    # 2.8 - среднее увеличение количества токенов по сравнение с количеством слов
    limit_tokens = round(limit_word * 2.8)
    if limit_tokens > 2600:
        limit_tokens = 2600
    message = f"Напиши аннотацию по данному тексту: {str}. В ответе верни только аннотацию."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0,
        max_tokens=limit_tokens,
        messages=[
                 {"role": "user",
                  "content": f"{message}"}]
    )
    # print response
    content_value = response["choices"][0]["message"]["content"]
    return content_value


def get_subtitles_for_yt(link: str) -> tuple[DataFrame, str] | tuple[Any, str]:
    """
    Получение субтитров для yt видео
    """

    try:
        yt = YouTube(link)
        dict_of_lang_subtitles = yt.captions
        title = yt.title
        lang_for_vid = detect_lang_for_vid(dict_of_lang_subtitles, title)
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

                df = parse_subtitles(subtitles)
                break

        else:
            if lang_for_vid is not None:
                df = generate_subtitles(lang=lang_for_vid, yt=yt)

        df = remove_rows_without_letters_and_numbers(df)

        return df, title

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


def extract_picture_from_yt_video(url: str, start_time: str = "00:00:00.000", nm_pct_with_ext: str = "output.jpg"):
    ydl_opts = {
        "quiet": True,  # Отключение вывода информации от youtube_dl
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        formats = info_dict.get("formats", [])
        print(formats)
        mp4_formats = [format for format in formats if format.get("ext") == "mp4"]
        max_quality = max(mp4_formats, key=lambda x: x["quality"])
        video_url = max_quality["url"]

    if video_url:
        ffmpeg_command = f'ffmpeg -ss {start_time} -i "{video_url}" -frames:v 1 -update 1 -y {nm_pct_with_ext}'
        subprocess.run(ffmpeg_command, shell=True)


def create_doc(df, name_of_doc, title, url):
    # Создание нового документа
    doc = Document()
    # Добавление текстового содержимого из датафрейма в документ
    doc.add_heading(f"{title}", level=1)
    for index, row in df.iterrows():
        doc.add_heading(f"Параграф {index + 1}", level=2)
        doc.add_paragraph(row['text'])
        # Добавление изображений в документ
        extract_picture_from_yt_video(url, start_time=row["start_time"])

        image_path = "output.jpg"
        img = Image.open(image_path)

        # Определение размеров изображения в дюймах (пропорционально)
        img_width, img_height = img.size
        aspect_ratio = img_width / img_height
        desired_width = Inches(6)
        desired_height = desired_width / aspect_ratio

        # Масштабирование изображения с сохранением пропорций
        img.thumbnail((desired_width, desired_height))

        # Сохранение временной копии масштабированного изображения в формате JPEG
        temp_image_path = 'temp.jpg'
        img.save(temp_image_path, 'JPEG')

        # Добавление изображения в документ
        doc.add_picture(temp_image_path, width=desired_width, height=desired_height)

        # Разделитель между разделами документа
        doc.add_page_break()

    # Сохранение документа
    doc.save(name_of_doc)


# extract_picture_from_yt_video(url, start_time = "00:01:00.000")

# df, title = get_subtitles_for_yt(url)
# df.to_csv('gen_sub.csv')
# name_of_doc = 'output_doc.docx'
# create_doc(df, name_of_doc, title, url)

# openai part

df = pd.read_csv('gen_sub.csv')
print(create_annotation(concatenate_text(df), 500))

