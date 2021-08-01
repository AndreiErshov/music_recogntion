from dispatcher import dp, bot
from math import ceil
from pydub import AudioSegment
from implshazam import ImplShazam
from aiogram import types
from handlers.common import cmd_start, Form
from aiogram.dispatcher import FSMContext
from requests.exceptions import ConnectionError
from threading import Thread
from asyncio import run, get_event_loop, run_coroutine_threadsafe, all_tasks
from asyncio.futures import Future
import wave
import os
import config
import youtube_dl

schedule_thread = None
schedule_loop = None
main_loop = get_event_loop()
running_tasks = []
ydl_opts = {'format': 'worstaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'noplaylist': True,
            'extractaudio': True}


@dp.callback_query_handler(lambda c: c.data == 'button1')
async def process_callback_button1(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await Form.url.set()
    await bot.send_message(callback_query.from_user.id, 'Введите ссылку на видео')


def percentage_format(percentage, tracks_length):
    pretty_percentage_format = ceil(percentage * 100)
    return "Начинаю искать треки, " + str(pretty_percentage_format) + "%" + ", было найдено " + str(
        tracks_length) + " треков"


def is_file_exists(file_name: str, path=".") -> str:
    for i in os.listdir(path):
        split_name = file_name.split('.')
        if len(split_name) > 1:
            split_name = '.'.join(split_name[:-1])
        else:
            split_name = file_name
        if split_name in i:
            return i
    return ""


async def url_threading(message: types.Message, state: FSMContext):
    global schedule_loop
    msg_id = message.chat.id
    running_tasks.append(msg_id)
    bot.set_current(bot)
    schedule_loop = get_event_loop()

    def send_message_threadsafe(c_id, msg):
        future: Future = run_coroutine_threadsafe(bot.send_message(c_id, msg), main_loop)
        func_result = future.result()
        return func_result

    def edit_message_threadsafe(inst, msg):
        future: Future = run_coroutine_threadsafe(inst.edit_text(msg), main_loop)
        func_result = future.result()
        return func_result

    ydl = youtube_dl.YoutubeDL(ydl_opts).__enter__()
    result = False
    try:
        result = ydl.extract_info(message.text, download=False)
        if int(result['duration']) > 7200:
            result = False
            send_message_threadsafe(msg_id, "Слишком длинный видеоролик")
    except:
        send_message_threadsafe(msg_id, "Неправильная ссылка, нажмите кнопку ещё раз")

    if result:
        file_name = ydl.prepare_filename({'id': result['id'], 'ext': 'wav', 'title': result['title']})
        file_exists = is_file_exists(file_name)
        percentage_message = send_message_threadsafe(msg_id, "Скачиваю видео...")
        if file_exists == "":
            ydl.download([message.text])
        else:
            if file_name != file_exists:
                while file_name != is_file_exists(file_name):
                    pass
        ydl.__exit__()
        wave_file = wave.open(file_name, 'r')
        frames = wave_file.getframerate() * config.FRAGMENT_DURATION
        length = frames * wave_file.getsampwidth() * wave_file.getnchannels()
        tracks = []

        edit_message_threadsafe(percentage_message, percentage_format(0, 0))
        percentage_max = ceil(wave_file.getnframes() / frames)

        i = 0
        while True:
            i += 1
            fragment = wave_file.readframes(frames)

            audio = AudioSegment(data=fragment, sample_width=wave_file.getsampwidth(),
                                 frame_rate=wave_file.getframerate(), channels=wave_file.getnchannels())
            audio = audio.set_frame_rate(16000).set_sample_width(2).set_channels(1)
            shazam = ImplShazam()
            recognize_generator = shazam.recognizeAudioSegment(audio)
            while True:
                try:
                    try:
                        result = next(recognize_generator)
                    except ConnectionError:
                        continue
                    new_result = False
                    try:
                        new_result = result[1]['track']['share']['subject']
                    except:
                        continue
                    if new_result not in tracks:
                        tracks.append(new_result)
                except StopIteration:
                    break

            pretty_percentage = i / percentage_max
            text = percentage_format(pretty_percentage, len(tracks))
            if percentage_message.text != text:
                percentage_message.text = text
                edit_message_threadsafe(percentage_message, text)
            if len(fragment) != length:
                break

        if len(tracks) > 0:
            send_message_threadsafe(msg_id, "В этом видео были обнаружены треки: \n" + '\n'.join(tracks))
        else:
            send_message_threadsafe(msg_id, "В этом видео не было обнаружено ни одного трека")
        if file_exists == "":
            os.remove(file_name)

    running_tasks.remove(msg_id)
    run_coroutine_threadsafe(cmd_start(message), main_loop).result()


@dp.message_handler(state=Form.url)
async def process_url(message: types.Message, state: FSMContext):
    global schedule_thread
    async with state.proxy() as data:
        data['url'] = message.text
    await state.finish()
    msg_id = message.chat.id
    if msg_id in running_tasks:
        await bot.send_message(msg_id, "Подождите, пока окончится прошлая задача")
        return
    if schedule_loop and schedule_thread and schedule_thread.is_alive():
        if len(all_tasks(schedule_loop)) >= config.MAX_TASKS:
            await bot.send_message(msg_id, "Бот сейчас нагружен. Подождите, пока бот завершит все задачи")
            return
        run_coroutine_threadsafe(url_threading(message, state), schedule_loop)
    schedule_thread = Thread(target=run, args=(url_threading(message, state),))
    schedule_thread.start()
