from aiogram import executor
from dispatcher import dp
import handlers
import config
import os

print("Your token is " + config.BOT_TOKEN)


def remove_videos():
    for file in os.listdir("."):
        for i in config.AUDIO_FORMATS:
            if file.endswith(i):
                os.remove(file)


if __name__ == "__main__":
    remove_videos()
    executor.start_polling(dp, skip_updates=True)
