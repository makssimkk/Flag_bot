# Импортируем необходимые классы.
import logging
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from config import BOT_TOKEN, LIFE_COUNT
from data import *
from random import choice, sample, shuffle
import pymorphy2


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)


class GeographyBot:
    def __init__(self):
        self.morph = pymorphy2.MorphAnalyzer()
        self.countries = {
            'southAmerica': southAmerica,
            'northAmerica': northAmerica,
            'oceania': oceania,
            'asia': asia,
            'africa': africa,
            'eur': eur
        }

        self.set_default()

    def set_default(self):
        self.modes = {}
        self.continents = {}
        self.current_countries = {}
        self.lifes = {}
        self.points = {}

    def get_user_mode(self, chat_id):
        if chat_id not in self.modes:
            self.modes[chat_id] = None
        return self.modes[chat_id]

    def set_user_mode(self, chat_id, mode):
        self.modes[chat_id] = mode

    def get_user_continent(self, chat_id):
        if chat_id not in self.continents:
            self.continents[chat_id] = None
        return self.continents[chat_id]

    def set_user_continent(self, chat_id, continent):
        self.continents[chat_id] = continent

    def get_user_countries(self, chat_id):
        if chat_id not in self.current_countries:
            self.current_countries[chat_id] = None
        return self.current_countries[chat_id]

    def set_user_countries(self, chat_id, country):
        self.current_countries[chat_id] = country

    def set_user_default(self, chat_id):
        self.set_user_mode(chat_id, None)
        self.set_user_continent(chat_id, None)
        self.set_user_countries(chat_id, None)

    def set_life_default(self, chat_id):
        self.lifes[chat_id] = LIFE_COUNT

    def set_points_default(self, chat_id):
        self.points[chat_id] = 0

    def decr_user_lifes(self, chat_id):
        self.lifes[chat_id] -= 1

    def incr_user_points(self, chat_id):
        self.points[chat_id] += 1

    def get_user_lives(self, chat_id):
        return self.lifes[chat_id]

    def get_user_points(self, chat_id):
        return self.points[chat_id]

    async def start(self, update, context):
        user = update.effective_user
        chat_id = update.message['chat']['id']
        self.set_user_default(chat_id)

        keyboard = [
            [
                InlineKeyboardButton("Обучение", callback_data='1'),
                InlineKeyboardButton("Тест", callback_data='2'),
            ],
            [InlineKeyboardButton("Поиск", callback_data='3')],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_html(
            rf"Привет, {user.mention_html()}! Здесь вы можете найти флаг нужной страны, пройти обучение или проверить свои знания флагов ;3. Выберите режим", reply_markup=reply_markup)

    async def button(self, update, context):
        query = update.callback_query
        variant = query.data
        chat_id = query.message['chat']['id']

        await query.answer()

        mode = self.get_user_mode(chat_id)
        print(mode, chat_id)
        if mode is None:
            if variant == '1':
                self.set_user_mode(chat_id, 'study')
                await self.study(update)
            elif variant == '2':
                self.set_user_mode(chat_id, 'test')
                await self.test(update, context)
            elif variant == '3':
                self.set_user_mode(chat_id, 'search')
                self.set_user_continent(chat_id, None)
                await self.search(update)

        elif mode == 'study':
            current_continent = self.get_user_continent(chat_id)
            if current_continent is None:
                self.set_user_continent(chat_id, variant)
                current_continent = self.get_user_continent(chat_id)
                await query.message.reply_text(self.countries[current_continent]['text'])
                await self.send_flag_study(update, context)
            else:
                current_country = self.get_user_countries(chat_id)
                if variant == current_country:
                    await query.message.reply_text(f"Поздравляю! Абсолютно верно, это {self.countries[current_continent]['countries'][variant]['name']}")
                    await self.send_flag_study(update, context)
                else:
                    variant_for_text = self.morph.parse(self.countries[current_continent]['countries'][variant]['name'])[0]
                    gent_variant = variant_for_text.inflect({'gent'})
                    current_country_for_text = self.morph.parse(self.countries[current_continent]['countries'][current_country]['name'])[0]
                    gent_current_country = current_country_for_text.inflect({'gent'})
                    await query.message.reply_text(f"Неверно! Это флаг {gent_current_country.word.capitalize()}, а флаг {gent_variant.word.capitalize()} выглядит так")
                    await context.bot.send_photo(chat_id=chat_id, photo=open(self.countries[current_continent]['countries'][variant]['flag'], 'rb'))
                    await query.message.reply_text("Следующий флаг!")
                    await self.send_flag_study(update, context)

        elif mode == 'test':
            current_country = self.get_user_countries(chat_id)
            current_continent = self.get_user_continent(chat_id)
            if variant == current_country:
                self.incr_user_points(chat_id)
                points = self.get_user_points(chat_id)
                lifes = self.get_user_lives(chat_id)
                await query.message.reply_text(
                    f"Поздравляю! Абсолютно верно, это {self.countries[current_continent]['countries'][variant]['name']}. Количество жизней: {lifes}. Количество очков: {points}")
                await self.send_flag_test(update, context)
            else:
                self.decr_user_lifes(chat_id)
                points = self.get_user_points(chat_id)
                lifes = self.get_user_lives(chat_id)
                if lifes > 0:
                    await query.message.reply_text(
                        f"Неверно! Количество жизней: {lifes}. Количество очков: {points}")
                    await query.message.reply_text("Следующий флаг!")
                    await self.send_flag_test(update, context)
                else:
                    await query.message.reply_text(
                        f"Вы ПРОИГРАЛИ! Количество жизней: {lifes}. Количество очков: {points}. Для начала /start")

    async def test(self, update, context):
        query = update.callback_query
        chat_id = query.message['chat']['id']
        self.set_life_default(chat_id)
        self.set_points_default(chat_id)
        lifes = self.get_user_lives(chat_id)
        points = self.get_user_points(chat_id)
        await query.message.reply_text(f"Проверь себя:D Выберите правильный вариант ответа! Количество жизней: {lifes}. Количество очков: {points}")
        await self.send_flag_test(update, context)

    async def send_flag_test(self, update, context):
        query = update.callback_query
        chat_id = query.message['chat']['id']
        current_continent = choice(list(self.countries.keys()))

        key_list = list(self.countries[current_continent]['countries'].keys())
        key = choice(key_list)
        random_country = self.countries[current_continent]['countries'][key]
        path = random_country['flag']
        self.set_user_countries(chat_id, key)
        self.set_user_continent(chat_id, current_continent)
        countries = [*self.get_random_country_without_current(key, key_list), key]
        shuffle(countries)

        keyboard = [
            [
                InlineKeyboardButton(self.countries[current_continent]['countries'][countries[0]]['name'],
                                     callback_data=countries[0]),
                InlineKeyboardButton(self.countries[current_continent]['countries'][countries[1]]['name'],
                                     callback_data=countries[1]),
            ],
            [
                InlineKeyboardButton(self.countries[current_continent]['countries'][countries[2]]['name'],
                                     callback_data=countries[2]),
                InlineKeyboardButton(self.countries[current_continent]['countries'][countries[3]]['name'],
                                     callback_data=countries[3]),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'))
        await query.message.reply_text("Какой стране принадлежит этот флаг? Для остановки /stop", reply_markup=reply_markup)

    async def search(self, update):
        query = update.callback_query
        await query.message.reply_text(f"Введите название страны:")

    async def study(self, update):
        query = update.callback_query
        keyboard = [
            [
                InlineKeyboardButton("Южная америка", callback_data='southAmerica'),
                InlineKeyboardButton("Северная Америка", callback_data='northAmerica'),
            ],
            [
                InlineKeyboardButton("Океания", callback_data='oceania'),
                InlineKeyboardButton("Азия", callback_data='asia'),
            ],
            [
                InlineKeyboardButton("Африка", callback_data='africa'),
                InlineKeyboardButton("Европа", callback_data='eur'),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_html(
            rf"Выберите часть света:",
            reply_markup=reply_markup)


    async def send_flag_study(self, update, context):
        query = update.callback_query
        chat_id = query.message['chat']['id']
        current_continent = self.get_user_continent(chat_id)

        key_list = list(self.countries[current_continent]['countries'].keys())
        key = choice(key_list)
        random_country = self.countries[current_continent]['countries'][key]
        path = random_country['flag']
        self.set_user_countries(chat_id, key)
        countries = [*self.get_random_country_without_current(key, key_list), key]
        shuffle(countries)

        keyboard = [
            [
                InlineKeyboardButton(self.countries[current_continent]['countries'][countries[0]]['name'],
                                     callback_data=countries[0]),
                InlineKeyboardButton(self.countries[current_continent]['countries'][countries[1]]['name'],
                                     callback_data=countries[1]),
            ],
            [
                InlineKeyboardButton(self.countries[current_continent]['countries'][countries[2]]['name'],
                                     callback_data=countries[2]),
                InlineKeyboardButton(self.countries[current_continent]['countries'][countries[3]]['name'],
                                     callback_data=countries[3]),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'))
        await query.message.reply_text("Какой стране принадлежит этот флаг? Для остановки /stop", reply_markup=reply_markup)

    def get_random_country_without_current(self, key, key_list):
        key_list.remove(key)
        return sample(key_list, 3)

    async def send_flag_search(self, update, context):
        country = update.message.text

        flag = False
        for key in self.countries.keys():
            for i in self.countries[key]['countries'].keys():
                if self.countries[key]['countries'][i]['name'].lower() == country.lower():
                    path = self.countries[key]['countries'][i]['flag']
                    await context.bot.send_photo(chat_id=update.message['chat']['id'], photo=open(path, 'rb'))
                    await update.message.reply_text(f"Столица: {self.countries[key]['countries'][i]['capital']}")
                    await update.message.reply_text(f"{self.countries[key]['countries'][i]['text']} Для остановки /stop")
                    flag = True

        if flag is False:
            await update.message.reply_text("Такой страны не существует. Для остановки /stop")

    async def stop(self, update, _):
        chat_id = update.message['chat']['id']
        self.set_user_default(chat_id)
        await update.message.reply_text("Используйте `/start` для начала <3")


def main():
    bot = GeographyBot()
    application = Application.builder().token(BOT_TOKEN).build()

    text_handler = MessageHandler(filters.TEXT, bot.send_flag_search)

    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CallbackQueryHandler(bot.button))
    application.add_handler(CommandHandler("stop", bot.stop))
    application.add_handler(CommandHandler("search", bot.search))

    application.add_handler(text_handler)

    application.run_polling()


if __name__ == '__main__':
    main()