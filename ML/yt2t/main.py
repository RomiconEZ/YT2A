import itertools
import logging
import os
import re
import sys
import time
from datetime import datetime

import dotenv
import ffmpeg
import numpy as np
import openai
import pandas as pd
import speech_recognition as sr
import whisper
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from pytube import YouTube

dotenv.load_dotenv(".env")
openai.api_key = os.environ.get("API_KEY")
model_whisper = whisper.load_model("medium")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=os.environ.get("LOGLEVEL", "INFO").upper(),
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


def merge_rows(df):
    # Функция для проверки наличия двух точек в конце строки
    def has_two_or_more_dots(text):
        return re.search(r"\.{2,}$", text) is not None

    # Объединение строк и обновление времени
    new_rows = []
    current_row = None

    for index, row in df.iterrows():
        if current_row is None:
            current_row = row
        else:
            if has_two_or_more_dots(current_row["text"]):
                current_row["text"] += " " + row["text"]
            else:
                new_rows.append(current_row)
                current_row = row

    # Добавление последней строки
    new_rows.append(current_row)

    # Создание нового датафрейма с обновленными данными
    new_df = pd.DataFrame(new_rows)
    new_df.reset_index(drop=True, inplace=True)

    return new_df


def format_times(milliseconds_array):
    hours = milliseconds_array // (1000 * 60 * 60)
    minutes = (milliseconds_array // (1000 * 60)) % 60
    seconds = (milliseconds_array // 1000) % 60
    milliseconds = milliseconds_array % 1000

    formatted_times = []
    for h, m, s, ms in zip(hours, minutes, seconds, milliseconds):
        formatted_times.append(f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}")

    return np.array(formatted_times)


def split_on_silence(
    audio_segment,
    min_silence_len=1000,
    silence_thresh=-16,
    keep_silence=100,
    seek_step=1,
):
    """
    Returns list of audio segments from splitting audio_segment on silent sections

    audio_segment - original pydub.AudioSegment() object

    min_silence_len - (in ms) minimum length of a silence to be used for
        a split. default: 1000ms

    silence_thresh - (in dBFS) anything quieter than this will be
        considered silence. default: -16dBFS

    keep_silence - (in ms or True/False) leave some silence at the beginning
        and end of the chunks. Keeps the sound from sounding like it
        is abruptly cut off.
        When the length of the silence is less than the keep_silence duration
        it is split evenly between the preceding and following non-silent
        segments.
        If True is specified, all the silence is kept, if False none is kept.
        default: 100ms

    seek_step - step size for interating over the segment in ms
    """

    # from the itertools documentation
    def pairwise(iterable):
        "s -> (s0,s1), (s1,s2), (s2, s3), ..."
        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)

    if isinstance(keep_silence, bool):
        keep_silence = len(audio_segment) if keep_silence else 0

    output_ranges = [
        [start - keep_silence, end + keep_silence]
        for (start, end) in detect_nonsilent(
            audio_segment, min_silence_len, silence_thresh, seek_step
        )
    ]

    for range_i, range_ii in pairwise(output_ranges):
        last_end = range_i[1]
        next_start = range_ii[0]
        if next_start < last_end:
            range_i[1] = (last_end + next_start) // 2
            range_ii[0] = range_i[1]

    return [
        [
            audio_segment[max(start, 0) : min(end, len(audio_segment))],
            max(start, 0),
            min(end, len(audio_segment)),
        ]
        for start, end in output_ranges
    ]


class YT2T:
    """YT2T Class to translates audio to text file"""

    __audioextension = ["flac", "wav"]
    __textextension = "csv"

    def __init__(self, outputpath=None):
        """
        YT2T constructor

        Parameters:
            outputpath (str): Output directory to save audio and csv files
        """

        if outputpath is None:
            outputpath = os.path.join(os.path.expanduser("~"), "YT2A")

        logger.info(f"YT2T content file saved at path {outputpath}")

        # create a speech recognition object
        self.recognizer = sr.Recognizer()

        self.textpath = os.path.join(outputpath, "text")
        self.audiopath = os.path.join(outputpath, "audio")
        self.audiochunkpath = os.path.join(outputpath, "audio-chunks")

        self.__createdir(self.textpath)
        self.__createdir(self.audiopath)
        self.__createdir(self.audiochunkpath)

    def url2text(
        self,
        urlpath=None,
        yt=None,
        outfile=None,
        audioformat="flac",
        audiosamplingrate=16000,
        lang="en-US",
    ):
        """
        Convert youtube url to text

        Parameters:
            urlpath (str): Youtube url
            outfile (str, optional): File path/name of output file (.csv)
            audioformat (str, optional): Audioformat supported in self.__audioextension
            audiosamplingrate (int, optional): Audio sampling rate
        """

        outfilepath = None
        audiofile = None

        if outfile is not None:
            if outfile.endswith(self.__textextension) is False:
                logger.warning(
                    "Text file poorly defined. outfile have to ends with .csv"
                )

                outfile = None

            elif (outfile.find(os.sep) != -1) and (
                outfile.endswith(self.__textextension)
            ):
                textfile = outfile.split(os.sep)[-1]
                outfilepath = outfile[0 : len(outfile) - len(textfile) - 1]

            else:
                if outfile.endswith(self.__textextension):
                    rawfilename = outfile.split(".")[0]
                    filename = self.__removeinvalidcharacter(rawfilename)
                    textfile = filename + "." + self.__textextension

                else:
                    filename = self.__generatefiletitle()
                    textfile = filename + "." + self.__textextension

                if audioformat not in self.__audioextension:
                    defaultaudioformat = self.__audioextension[0]
                    logger.warning(
                        f"Selected audio format not permitted: {audioformat}. Fall back to default: {defaultaudioformat}"
                    )
                    audioformat = self.__audioextension[0]

                audiofile = filename + "." + audioformat

        else:
            filename = self.__generatefiletitle()
            audiofile = filename + "." + self.__audioextension[0]
            textfile = filename + "." + self.__textextension

        audiofile = self.__configurepath(audiofile, outfilepath, self.audiopath)
        textfile = self.__configurepath(textfile, outfilepath, self.textpath)

        if yt != None:
            self.url2audio(
                audiofile=audiofile, audiosamplingrate=audiosamplingrate, yt=yt
            )
        elif urlpath != None:
            self.url2audio(
                urlpath=urlpath,
                audiofile=audiofile,
                audiosamplingrate=audiosamplingrate,
            )
        # Изменить на определение языка
        df = self.audio2text(audiofile=audiofile, textfile=textfile, lang=lang)
        return df

    def url2audio(self, urlpath=None, audiofile=None, audiosamplingrate=16000, yt=None):
        """
        Convert youtube url to audiofile

        Parameters:
            urlpath (str): Youtube url
            audiofile (str, optional): File path/name to save audio file
            audiosamplingrate (int, optional): Audio sampling rate
        """

        audioformat = self.__audioextension[0]
        outfilepath = None

        if (audiofile is not None) and (audiofile.find(".") != -1):
            audioformat = audiofile.split(".")[-1]
            if audioformat in self.__audioextension:
                if audiofile.find(os.sep) != -1:
                    buffer = audiofile.split(os.sep)[-1]
                    outfilepath = audiofile[: len(audiofile) - len(buffer) - 1]
                    audiofile = buffer

            else:
                audiofile = self.__generatefiletitle() + "." + self.audiofilename[0]

        else:
            audiofile = self.__generatefiletitle() + "." + self.__audioextension[0]

        audiofile = self.__configurepath(audiofile, outfilepath, self.audiopath)

        if os.path.exists(audiofile):
            logger.info(f"Audio file exist at {audiofile}. Download skipped")

        else:
            audio = None

            done = False
            while not done:
                try:
                    if urlpath != None and yt == None:
                        yt = YouTube(urlpath)

                    stream_url = yt.streams[0].url

                    video = self.get_yt_video(yt)

                    acodec = "pcm_s16le" if audioformat == "wav" else audioformat

                    logger.info(f"Audio at sample rate {audiosamplingrate}")
                    audio, err = (
                        ffmpeg.input(stream_url)
                        .output(
                            "pipe:",
                            format=audioformat,
                            **{"ar": str(audiosamplingrate), "acodec": acodec},
                        )
                        .run(capture_stdout=True)
                    )
                    done = True
                except Exception as e:
                    print("Ошибка при скачивании.", flush=True)
                    done = False
                    time.sleep(10)

            with open(audiofile, "wb") as f:
                f.write(audio)

            logger.info(f"Download completed at {audiofile}")

    def get_yt_video(self, yt):
        video = yt.streams.get_highest_resolution()
        # get the video with the extension and
        # resolution passed in the get() function
        return video

    def audio2text(self, audiofile, textfile=None, lang="en-US"):
        """
        Convert audio to csv file

        Parameters:
            audiofile (str): File path/name of audio file
            textfile (str, optional): File path/name of text file (*.csv)
        """

        ext = audiofile.split(".")[-1]
        audiochunkpath = None
        audiochunkfolder = None

        if ext not in self.__audioextension:
            logger.error(
                f"Audio file has to end with extension in {self.__audioextension}. Operation abort."
            )

            return

        if os.path.exists(audiofile) is False:
            logger.error(f"Audio file not exist: {audiofile}. Execution abort.")

            return

        if (textfile is not None) and (os.path.exists(textfile)):
            logger.info(f"{textfile} exists. Conversion of speech -> text skipped")
            return

        elif textfile is not None and textfile.find(os.sep) != -1:
            textfilewithext = textfile.split(os.sep)[-1]
            textfilepath = textfile[: len(textfile) - len(textfilewithext) - 1]

            if not os.path.exists(textfilepath):
                logger.warning(
                    f"Text file path {textfilepath} do not exist. Fall back to default"
                )
                textfile = None
            else:
                audiochunkfolder = textfilewithext.split(".")[0]

                if textfile.find(self.textpath) != -1:
                    audiochunkfolder = textfilewithext.split(".")[0]
                    audiochunkpath = self.audiochunkpath
                else:
                    audiochunkpath = textfile[: len(textfile) - len(textfilewithext)]

        if textfile is None:
            textfilename = self.__generatefiletitle()
            audiochunkfolder = (
                textfilename  # both audio chunk folder and csv possess the same name
            )
            textfile = self.__configurepath(
                audiochunkfolder + "." + self.__textextension, None, self.textpath
            )

        df = self._get_large_audio_transcription(
            audiofile,
            audiochunkfolder=audiochunkfolder,
            audiochunkpath=audiochunkpath,
            lang=lang,
        )

        return df
        # df.to_csv(textfile, index=False)
        # logger.info(f"Output text file saved at {textfile}")

    def _get_large_audio_transcription(
        self, audiofullpath, audiochunkfolder, audiochunkpath=None, lang="en-US"
    ):
        """
        Splitting the large audio file into chunks
        and apply speech recognition on each of these chunks

        1Parameters:
            audiofullpath (str): Absolute/relative path to text file
            audiochunkfolder (str): folder name of audio chunk
            audiochunkpath (str, optional): Absolute/relative path to save snippet of audio file

        Returns:
            DataFrame: df with rows of texts
        """

        audiochunkpath = self.__configurepath(
            audiochunkfolder, audiochunkpath, self.audiochunkpath
        )

        if not os.path.isdir(audiochunkpath):
            os.mkdir(audiochunkpath)

        # open the audio file using pydub
        logger.info(f"Audio -> Text: {audiofullpath}")
        # logger.info(f"Audio chunk path: {audiochunkpath}")

        audioformat = audiofullpath.split(".")[-1]

        sound = None
        if audioformat == "wav":
            sound = AudioSegment.from_wav(audiofullpath)

        elif audioformat == "flac":
            sound = AudioSegment.from_file(audiofullpath, audioformat)

        # split audio sound where silence is 700 miliseconds or more and get chunks
        chunks = split_on_silence(
            sound,
            # experiment with this value for your target audio file
            min_silence_len=1000,
            # adjust this per requirement
            silence_thresh=sound.dBFS - 14,
            # keep the silence for 1 second, adjustable as well
            keep_silence=200,
        )

        whole_text = []
        audio_file = []
        start_time = []
        end_time = []

        # process each chunk
        for i, audio_chunk in enumerate(chunks, start=1):
            # export audio chunk and save it in
            # the `folder_name` directory.
            chunkfilename = f"chunk{i}." + audioformat
            chunkfilepath = os.path.join(audiochunkpath, chunkfilename)
            audio_chunk[0].export(chunkfilepath, format=audioformat)

            # recognize the chunk
            # with sr.AudioFile(chunkfilepath) as source:
            #     audio_listened = self.recognizer.record(source)
            #     # try converting it to text
            #     try:
            #         #text = self.recognizer.recognize_google(audio_listened, language=lang)
            #     except sr.UnknownValueError as e:
            #         whole_text.append("None")
            #         start_time.append(audio_chunk[1])
            #         end_time.append(audio_chunk[2])
            #     else:
            #         text = f"{text.capitalize()}. "
            #         whole_text.append(text)
            #         start_time.append(audio_chunk[1])
            #         end_time.append(audio_chunk[2])

            try:
                result = model_whisper.transcribe(chunkfilepath)
                text = result["text"]

            except sr.UnknownValueError as e:
                whole_text.append("None")
                start_time.append(audio_chunk[1])
                end_time.append(audio_chunk[2])
            else:
                text = f"{text.capitalize()}. "
                whole_text.append(text)
                start_time.append(audio_chunk[1])
                end_time.append(audio_chunk[2])

            audio_file.append(os.path.join(audiochunkfolder, chunkfilename))

        # return as df
        df = pd.DataFrame(
            {
                "text": whole_text,
                "file": audio_file,
                "start_time": start_time,
                "end_time": end_time,
            }
        )
        df["start_time"] = format_times(df["start_time"])
        df["end_time"] = format_times(df["end_time"])
        df = merge_rows(df)
        return df

    def __removeinvalidcharacter(self, strin):
        """
        Removal of invalid character when creating folder/filename

        Parameters:
            strin (str): Input string

        Returns:
            str: Processed valid string
        """

        removal_list = [i for i in r"\/:*?<>|\""]

        strout = strin

        for i in removal_list:
            strout = strout.replace(i, "_")

        return strout

    def __generatefiletitle(self):
        """
        Generate filename according to time stamp if did not provided

        Returns:
            str: timestamp str
        """

        now = datetime.now()

        return now.strftime("%Y%h%d_%H%M%S")

    def __createdir(self, path):
        """
        Create directory resursively if directories do not exist
        """
        if not os.path.exists(path):
            os.makedirs(path)

    def __configurepath(self, filename, designatedpath, fallbackpath):
        """
        Configure path to follows designated path or fallbackpath if former doesnt exist

        Returns:
            str: Absolute path to a file
        """
        if designatedpath is not None:
            if not os.path.exists(designatedpath):
                logger.warning(f'"{designatedpath}" not exist. Execution abort')
            else:
                return os.path.join(designatedpath, filename)
        else:
            return os.path.join(fallbackpath, filename)
