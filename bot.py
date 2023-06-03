from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart, StateFilter, Text
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.fsm.storage.redis import RedisStorage, Redis
from aiogram.types import (CallbackQuery,
                           InlineKeyboardButton,
                           InlineKeyboardMarkup,
                           Message,
                           PhotoSize)

from config import Config, load_config

CONFIG: Config = load_config()
TOKEN = CONFIG.tg_bot.token

# Инициализируем Redis
REDIS: Redis = Redis(host='localhost')
# Инициализируем хранилище (создаем экземпляр класса RedisStorage)
STORAGE: RedisStorage = RedisStorage(redis=REDIS)

BOT: Bot = Bot(token=TOKEN)
DP: Dispatcher = Dispatcher(storage=STORAGE)

# Создаем "базу данных" пользователей
USER_DICT: dict[int, dict[str, str | int | bool]] = {}


# Cоздаем класс, наследуемый от StatesGroup, для группы состояний нашей FSM
class FSMFillForm(StatesGroup):
    """
    Создаем экземпляры класса State, последовательно перечисляя возможные
    состояния, в которых будет находиться бот в разные моменты взаимодействия
    с пользователем
    Args:
        StatesGroup (_type_): _description_
    """
    fill_name = State()  # Состояние ожидания ввода имени
    fill_age = State()  # Состояние ожидания ввода возраста
    fill_gender = State()  # Состояние ожидания выбора пола
    upload_photo = State()  # Состояние ожидания загрузки фото
    fill_education = State()  # Состояние ожидания выбора образования
    getting_news = State()  # Состояние ожидания выбора получать ли новости


@DP.message(CommandStart(), StateFilter(default_state))
async def process_start_cmd(message: Message):
    """
    Хэндлер срабатывает на команду /start вне состояний и предлагает перейти к
    заполнению анкеты, отправив команду /fillform
    Args:
        message (Message): _description_
    """
    await message.answer(text='Этот бот демонстрирует работу FSM\n\n'
                              'Чтобы перейти к заполнению анкеты - '
                              'отправьте команду /fillform')


# Этот хэндлер будет срабатывать на команду "/cancel" в состоянии
# по умолчанию и сообщать, что эта команда работает внутри машины состояний
@DP.message(Command(commands=['cancel']), StateFilter(default_state))
async def process_cancel_cmd_default(message: Message):
    """
    Хэндлер срабатывает на команду "/cancel" в состоянии по умолчанию и
    сообщает, что эта команда работает внутри машины состояний

    Args:
        message (Message): _description_
    """
    await message.answer(text='Отменять нечего. Вы вне машины состояний\n\n'
                              'Чтобы перейти к заполнению анкеты - '
                              'отправьте команду /fillform')


@DP.message(Command(commands=['cancel']), ~StateFilter(default_state))
async def process_cancel_smd_fsm(message: Message, state: FSMContext):
    """
    Хэндлер срабатывает на команду "/cancel" в любых состояниях, кроме
    состояния по умолчанию, и отключать машину состояний

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    await message.answer(text='Вы вышли из машины состояний\n\n'
                              'Чтобы снова перейти к заполнению анкеты - '
                              'отправьте команду /fillform')
    # Сбрасываем состояние и очищаем данные, полученные внутри состояний
    await state.clear()


@DP.message(Command(commands=['fillform']), StateFilter(default_state))
async def process_fillform_cmd(message: Message, state: FSMContext):
    """
    Хэндлер срабатывает на команду /fillform и переводить бота в состояние
    ожидания ввода имени

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    await message.answer(text='Пожалуйста, введите ваше имя')
    await state.set_state(FSMFillForm.fill_name)


@DP.message(StateFilter(FSMFillForm.fill_name), F.text.isalpha())
async def process_correct_name(message: Message, state: FSMContext):
    """
    Хэндлер будет срабатывать, если введено корректное имя и переводить в
    состояние ожидания ввода возраста

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    # Cохраняем введенное имя в хранилище по ключу "name"
    await state.update_data(name=message.text)
    await message.answer(text='Спасибо!\n\nА теперь введите ваш возраст')
    # Устанавливаем состояние ожидания ввода возраста
    await state.set_state(FSMFillForm.fill_age)


@DP.message(StateFilter(FSMFillForm.fill_name))
async def process_incorrect_name(message: Message):
    """
    Хэндлер будет срабатывать, если во время ввода имени будет введено что-то
    некорректное
    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    await message.answer(text='То, что вы отправили не похоже на имя\n\n'
                              'Пожалуйста, введите ваше имя\n\n'
                              'Если вы хотите прервать заполнение анкеты - '
                              'отправьте команду /cancel')


@DP.message(StateFilter(FSMFillForm.fill_age),
            lambda x: x.text.isdigit() and 4 <= int(x.text) <= 120)
async def process_correct_age(message: Message, state: FSMContext):
    """
    Хэндлер будет срабатывать, если введен корректный возраст и переводить в
    состояние выбора пола
    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    # Cохраняем возраст в хранилище по ключу "age"
    await state.update_data(age=message.text)
    # Отправляем пользователю сообщение с клавиатурой
    female_btn: InlineKeyboardButton = InlineKeyboardButton(
        text='Женский ♀',
        callback_data='female')
    male_btn: InlineKeyboardButton = InlineKeyboardButton(
        text='Мужской ♂',
        callback_data='male')
    undefined_btn: InlineKeyboardButton = InlineKeyboardButton(
        text='🤷 Пока не ясно',
        callback_data='undefined_gender')
    keyboard_gender: list[list[InlineKeyboardButton]] = [
        [female_btn, male_btn],
        [undefined_btn]]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_gender)
    await message.answer(text='Спасибо!\n\nУкажите ваш пол',
                         reply_markup=markup)
    # Устанавливаем состояние ожидания выбора пола
    await state.set_state(FSMFillForm.fill_gender)


@DP.message(StateFilter(FSMFillForm.fill_age))
async def process_incorrect_age(message: Message):
    """
    Хэндлер будет срабатывать, если во время ввода возраста будет введено
    что-то некорректное
    Args:
        message (Message): _description_
    """
    await message.answer(
        text='Возраст должен быть целым числом от 4 до 120\n\n'
        'Попробуйте еще раз\n\nЕсли вы хотите прервать '
        'заполнение анкеты - отправьте команду /cancel')


@DP.callback_query(StateFilter(FSMFillForm.fill_gender),
                   Text(text=['female', 'male', 'undefined_gender']))
async def process_correct_gender(callback: CallbackQuery, state: FSMContext):
    """
    Хэндлер будет срабатывать на нажатие кнопки при выборе пола и переводить в
    состояние отправки фото
    Args:
        callback (CallbackQuery): _description_
        state (FSMContext): _description_
    """
    # Cохраняем пол (callback.data нажатой кнопки) в хранилище,
    # по ключу "gender
    await state.update_data(gender=callback.data)
    # Удаляем сообщение с кнопками, потому что следующий этап - загрузка фото
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.delete()
    await callback.message.answer(text='Спасибо! А теперь загрузите, '
                                       'пожалуйста, ваше фото')
    # Устанавливаем состояние ожидания загрузки фото
    await state.set_state(FSMFillForm.upload_photo)


@DP.message(StateFilter(FSMFillForm.fill_gender))
async def process_incorrect_gender(message: Message):
    """
    Хэндлер будет срабатывать, если во время выбора пола будет введено/
    отправлено что-то некорректное
    Args:
        message (Message): _description_
    """
    await message.answer(text='Пожалуйста, пользуйтесь кнопками '
                              'при выборе пола\n\nЕсли вы хотите прервать '
                              'заполнение анкеты - отправьте команду /cancel')


@DP.message(StateFilter(FSMFillForm.upload_photo),
            F.photo[-1].as_('largest_photo'))
async def proccess_correct_photo(message: Message,
                                 state: FSMContext,
                                 largest_photo: PhotoSize):
    """
    Хэндлер будет срабатывать, если отправлено фото и переводить в состояние
    выбора образования
    Args:
        message (Message): _description_
        state (FSMContext): _description_
        largest_photo (PhotoSize): _description_
    """
    await state.update_data(photo_id=largest_photo.file_id,
                            photo_unique_id=largest_photo.file_unique_id)
    higher_btn: InlineKeyboardButton = InlineKeyboardButton(
        text='Высшее',
        callback_data='high_education')
    secondary_btn: InlineKeyboardButton = InlineKeyboardButton(
        text='Среднее',
        callback_data='secondary_education')
    none_edu_btn: InlineKeyboardButton = InlineKeyboardButton(
        text='Нет',
        callback_data='no_education')
    keyboard_edu: list[list[InlineKeyboardButton]] = [
        [higher_btn, secondary_btn],
        [none_edu_btn]]
    markup: InlineKeyboardMarkup = InlineKeyboardMarkup(
        inline_keyboard=keyboard_edu)
    await message.answer(text='Спасибо!\n\nУкажите ваше образование',
                         reply_markup=markup)
    await state.set_state(FSMFillForm.fill_education)


@DP.message(StateFilter(FSMFillForm.upload_photo))
async def process_incorrect_photo(message: Message):
    """
    Хэндлер будет срабатывать, если во время отправки фото будет введено/
    отправлено что-то некорректное
    Args:
        message (Message): _description_
    """
    await message.answer(text='Пожалуйста, на этом шаге отправьте '
                              'ваше фото\n\nЕсли вы хотите прервать '
                              'заполнение анкеты - отправьте команду /cancel')


@DP.callback_query(StateFilter(FSMFillForm.fill_education),
                   Text(text=['high_education',
                              'secondary_education',
                              'no_education']))
async def process_correct_education(callback: CallbackQuery,
                                    state: FSMContext):
    """
    Хэндлер будет срабатывать, если выбрано образование и переводить в
    состояние согласия получать новости
    Args:
        callback (CallbackQuery): _description_
        state (FSMContext): _description_
    """
    await state.update_data(education=callback.data)
    agreed_btn: InlineKeyboardButton = InlineKeyboardButton(
        text='Да',
        callback_data='agreed')
    declined_btn: InlineKeyboardButton = InlineKeyboardButton(
        text='Нет',
        callback_data='declined')
    keyboard_news: list[list[InlineKeyboardButton]] = [[agreed_btn,
                                                        declined_btn]]
    markup: InlineKeyboardMarkup = InlineKeyboardMarkup(
        inline_keyboard=keyboard_news)
    await callback.message.edit_text(text='Спасибо!\n\n'
                                          'Остался последний шаг.\n'
                                          'Хотели бы вы получать новости?',
                                     reply_markup=markup)
    # Устанавливаем состояние ожидания выбора получать новости или нет
    await state.set_state(FSMFillForm.getting_news)


@DP.message(StateFilter(FSMFillForm.fill_education))
async def process_incorrect_education(message: Message):
    """
    Хэндлер будет срабатывать, если во время выбора образования будет введено/
    отправлено что-то некорректное
    Args:
        message (Message): _description_
    """
    await message.answer(text='Пожалуйста, пользуйтесь кнопками '
                              'при выборе образования\n\nЕсли вы хотите '
                              'прервать заполнение анкеты - отправьте '
                              'команду /cancel')


@DP.callback_query(StateFilter(FSMFillForm.getting_news),
                   Text(text=['agreed', 'declined']))
async def process_correct_news(callback: CallbackQuery, state: FSMContext):
    """
    Хэндлер будет срабатывать на выбор получать или не получать новости и
    выводить из машины состояний
    Args:
        callback (CallbackQuery): _description_
        state (FSMContext): _description_
    """
    # Cохраняем данные о получении новостей по ключу "wish_news"
    await state.update_data(news=callback.data == 'agreed')
    # Добавляем в "базу данных" анкету пользователя
    # по ключу id пользователя
    USER_DICT[callback.from_user.id] = await state.get_data()
    # Завершаем машину состояний
    await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
    await callback.message.edit_text(text='Спасибо! Ваши данные сохранены!\n\n'
                                          'Вы вышли из машины состояний')
    # Отправляем в чат сообщение с предложением посмотреть свою анкету
    await callback.message.answer(text='Чтобы посмотреть данные вашей '
                                       'анкеты - отправьте команду /showdata')


@DP.message(StateFilter(FSMFillForm.getting_news))
async def process_incorrect_news(message: Message):
    """
    Хэндлер будет срабатывать, если во время согласия на получение новостей
    будет введено/отправлено что-то некорректное
    Args:
        message (Message): _description_
    """
    await message.answer(text='Пожалуйста, воспользуйтесь кнопками!\n\n'
                              'Если вы хотите прервать заполнение анкеты - '
                              'отправьте команду /cancel')


@DP.message(Command(commands=['showdata']), StateFilter(default_state))
async def process_showdata_cmd(message: Message):
    """
    Хэндлер будет срабатывать на отправку команды /showdata и отправлять в чат
    данные анкеты, либо сообщение об отсутствии данных
    Args:
        message (Message): _description_
    """
    # Отправляем пользователю анкету, если она есть в "базе данных"
    if message.from_user.id in USER_DICT:
        user = USER_DICT[message.from_user.id]
        await message.answer_photo(
            photo=user['photo_id'],
            caption=f'Имя: {user["name"]}\n'
                    f'Возраст: {user["age"]}\n'
                    f'Пол: {user["gender"]}\n'
                    f'Образование: {user["education"]}\n'
                    f'Получать новости: {user["news"]}')
    else:
        # Если анкеты пользователя в базе нет - предлагаем заполнить
        await message.answer(text='Вы еще не заполняли анкету. '
                                  'Чтобы приступить - отправьте '
                                  'команду /fillform')


@DP.message(StateFilter(default_state))
async def process_other(message: Message):
    """
    Хэндлер будет срабатывать на любые сообщения, кроме тех для которых есть
    отдельные хэндлеры, вне состояний
    Args:
        message (Message): _description_
    """
    await message.reply(text='Я такое не понимаю.')


if __name__ == '__main__':
    DP.run_polling(BOT)
