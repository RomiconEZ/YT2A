from pytube import YouTube
from src.youtube2text.youtube2text import Youtube2Text


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


def generate_subtitles(lang, yt=None, url=None):
    converter = Youtube2Text()
    df = converter.url2text(urlpath=url, audioformat="flac", yt=yt, lang=lang)
    return df


def detect_lang_for_vid(dict_of_lang_subtitles):
    automatic_langs = {"a.ru": "ru-RU", "a.en": "en-US"}
    for lang in automatic_langs.keys():
        if lang in dict_of_lang_subtitles:
            return automatic_langs[lang]


def get_subtitles_for_yt(link: str):
    """
    Получение субтитров для yt видео
    """

    try:
        yt = YouTube(link)
        dict_of_lang_subtitles = yt.captions

        lang_for_vid = detect_lang_for_vid(dict_of_lang_subtitles)

        langs = ["ru", "en", "a.ru", "a.en"]

        for lang in langs:
            if lang in dict_of_lang_subtitles:
                subtitles = yt.captions[lang].generate_srt_captions()
                print(subtitles)
                break
        else:
            print('f')
            # df = generate_subtitles(lang=lang_for_vid, yt=yt)
            # df.to_csv('gen_sub.csv')
            # print('save to csv')
        df = generate_subtitles(lang=lang_for_vid, yt=yt)
        df.to_csv('gen_sub.csv')
        print('save to csv')

    except Exception as e:
        print("Произошла ошибка:", e)


get_subtitles_for_yt("https://youtu.be/Y9Zw6xOGly0")
