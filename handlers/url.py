from dispatcher import dp, bot
from math import ceil
from pydub import AudioSegment
from implshazam import ImplShazam
from aiogram import types
from handlers.common import cmd_start, Form
from aiogram.dispatcher import FSMContext
from requests.exceptions import ConnectionError
from config import FRAGMENT_DURATION
import wave
import os
import youtube_dl

ydl_opts = {'format': 'bestaudio/best',
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


@dp.message_handler(state=Form.url)
async def process_url(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['url'] = message.text
        ydl = youtube_dl.YoutubeDL(ydl_opts).__enter__()
        result = False
        try:
            result = ydl.extract_info(message.text, download=False)
            if int(result['duration']) > 7200:
                result = False
                await bot.send_message(message.chat.id, "Слишком длинный видеоролик")
        except:
            await bot.send_message(message.chat.id, "Неправильная ссылка, нажмите кнопку ещё раз")

        if result:
            ydl.download([message.text])
            ydl.__exit__()
            percentage_message = await bot.send_message(message.chat.id, "Скачиваю видео...")
            file_name = ydl.prepare_filename({'id': result['id'], 'ext': 'wav', 'title': result['title']})
            wave_file = wave.open(file_name, 'r')
            frames = wave_file.getframerate() * FRAGMENT_DURATION
            length = frames * wave_file.getsampwidth() * wave_file.getnchannels()
            tracks = []

            await percentage_message.edit_text(percentage_format(0, 0))
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
                await percentage_message.edit_text(percentage_format(pretty_percentage, len(tracks)))
                if len(fragment) != length:
                    break

            if len(tracks) > 0:
                await bot.send_message(message.chat.id, "В этом видео были обнаружены треки: \n" + '\n'.join(tracks))
            else:
                await bot.send_message(message.chat.id, "В этом видео не было обнаружено ни одного трека")
            os.remove(file_name)

    await cmd_start(message)
    await state.finish()
