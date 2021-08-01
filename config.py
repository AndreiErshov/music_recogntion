import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# prerequisites
if 'TOKEN' not in os.environ:
    exit("No token provided")

BOT_TOKEN = os.environ['TOKEN']
AUDIO_FORMATS = ['.wav', '.mp3', '.webm', '.opus', '.ogg', '.m4a', '.wma', '.mkv']
FRAGMENT_DURATION = 20
MAX_TASKS = 10
