from dispatcher import dp
from aiogram import types
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

inline_btn_1 = InlineKeyboardButton('Ввести видео', callback_data='button1')
inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1)


class Form(StatesGroup):
    url = State()


@dp.message_handler(commands='start', state="*")
async def cmd_start(message: types.Message, state: FSMContext = False):
    if state:
        await state.finish()
    await message.reply("Здравствуйте! Нажмите на кнопку ниже, чтобы начать находить треки с видео",
                        reply_markup=inline_kb1)


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
