import yaml
import sys
import uuid

from telebot import types
from telebot.async_telebot import AsyncTeleBot

from sql_db_pay import connect_and_create_db, add_user, get_users, update_payment_info

import asyncio
import requests
from bs4 import BeautifulSoup

import os

import aiofiles

try:
    with open("config.yml") as yaml_file:
        config = yaml.load(yaml_file, Loader=yaml.FullLoader)
except FileNotFoundError:
    with open("~/course_work/config.yml") as yaml_file:
        config = yaml.load(yaml_file, Loader=yaml.FullLoader)

bot = AsyncTeleBot(config['bot']['token'])

@bot.message_handler(commands=['start'])
async def send_welcome(message):
    user_id = message.from_user.id 
    user_name = message.from_user.username
    curr_users = [el[0] for el in await get_users()]
    if user_id in curr_users:
        await bot.send_message(599202079, text = f'Пользователь {message.from_user.username if message.from_user.username is not None else "Empty"} <b> ПРОДОЛЖИЛ </b> работу с ботом', 
                            parse_mode="HTML") 
    else:
        await bot.send_message(599202079, text = f'Пользователь {message.from_user.username if message.from_user.username is not None else "Empty"} <b> Начал </b> работу с ботом', 
                            parse_mode="HTML") 
        value = await add_user(user_id, user_name, False)
        if value == "Not having db files":
            await bot.send_message(599202079, text = f'Были удалены все БД. Пользователь {message.from_user.username} не смог добавиться', parse_mode="HTML") 
            sys.exit()


    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Получить доступ", callback_data="to_buying_enter")
    btn2 = types.InlineKeyboardButton("Прослушать промо книги", callback_data="get_promo")
    markup.add(btn1)
    markup.add(btn2)

    await bot.send_message(message.chat.id, text='📚 Добро пожаловать в бот аудиокниги «Город поющих мостов». Здесь можно прослушать отрывок из произведения, а также получить доступ к полной версии книги, в которой ты найдёшь захватывающие истории, загадочных персонажей и магические приключения. Погрузись в мир Сказки вместе с нами. 🌟🎧', reply_markup=markup)


@bot.message_handler(commands=['status'])
async def send_welcome(message):
    user_id = message.from_user.id
    users_or_value = await get_users()
    if users_or_value == 'Not having db files':
        await bot.send_message(599202079, text = f'Были удалены все БД. Пользователь {message.from_user.username} не смог перейти к оплате', parse_mode="HTML") 
        sys.exit()
        
    payments_info = {el[0] : el[2] for el in users_or_value}

    if payments_info[user_id] == True:
        await bot.send_message(message.chat.id, text=f"Оплата уже была успешно совершена. Ссылка на канал: {config['other']['link_for_joining']}")
    else:
        await bot.send_message(message.chat.id, text=f'Оплата еще не была произведена.')
        prices = [types.LabeledPrice(label='Город поющих мостов', amount=100000)] # amount в копейках
        await bot.send_invoice(
            chat_id=message.chat.id,
            title='Аудиокнига',
            description='Получение доступа к аудиокниге',
            invoice_payload=str(uuid.uuid1()),  # Уникальный идентификатор счета
            provider_token=config['other']['payment_token'],  # Токен провайдера платежей
            start_parameter="Buying",  # Уникальный параметр для начала оплаты
            currency='RUB',  # Валюта (например, RUB)
            prices=prices,
        )

@bot.message_handler(commands=['help'])
async def send_welcome(message):
    await bot.send_message(message.chat.id, text='Привет! Бот в первую очередь необходим для более удобного получения доступа к каналу. По всем вопросам обращайтесь ко мне.')

@bot.callback_query_handler(func=lambda call: call.data == 'get_promo')
async def getting_promo_mode(call): # проверить, что человек внутри канала + рекомендовать донат в ином случае
    async with aiofiles.open(config['other']['promo_file_path'], mode='rb') as f:
        audio_data = await f.read()
        await bot.send_audio(call.message.chat.id, audio_data, caption="Промо аудиокниги ⏯️")

@bot.callback_query_handler(func=lambda call: call.data == 'to_buying_enter')
async def purchasing_mode(call): # проверить, что человек внутри канала + рекомендовать донат в ином случае
    user_id = call.from_user.id
    users_or_value = await get_users()
    if users_or_value == 'Not having db files':
        await bot.send_message(599202079, text = f'Были удалены все БД. Пользователь {call.from_user.username} не смог перейти к оплате', parse_mode="HTML") 
        sys.exit()
        
    payments_info = {el[0] : el[2] for el in users_or_value}
    if payments_info[user_id] == False:
        prices = [types.LabeledPrice(label='Город поющих мостов', amount=100000)] # amount в копейках

        await bot.send_invoice(
            chat_id=call.message.chat.id,
            title='Аудиокнига',
            description='Получение доступа к аудиокниге',
            invoice_payload=str(uuid.uuid1()),  # Уникальный идентификатор счета
            provider_token=config['other']['payment_token'],  # Токен провайдера платежей
            start_parameter="Buying",  # Уникальный параметр для начала оплаты
            currency='RUB',  # Валюта (например, RUB)
            prices=prices,
        )
    else:
        await bot.send_message(call.message.chat.id, text='Если вы хотите задонатить, то свяжитесь со мной')

@bot.pre_checkout_query_handler(func=lambda query: True)
async def checkout(pre_checkout_query):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                  error_message="Упс! 😅 Похоже, что-то пошло не так с вашей оплатой. Не волнуйтесь, давайте попробуем ещё раз! 🔄"
                                                "Пожалуйста, проверьте свои платежные данные и убедитесь, что все верно, затем попробуйте снова. Если у вас всё ещё возникают трудности, напишите нам, и мы поможем вам с радостью! 📚")

@bot.message_handler(content_types=['successful_payment'])
async def got_payment(message):
    user_id = message.from_user.id
    users_or_value = await get_users()
    if users_or_value == 'Not having db files':
        await bot.send_message(599202079, text = f'Были удалены все БД. Пользователь {message.from_user.username} после оплаты не получил сообщения об оплате. Пусть проверит списание', parse_mode="HTML") 
        sys.exit()
        
    payments_info = {el[0] : el[2] for el in users_or_value}
    if payments_info[user_id] == False:
        await bot.send_message(message.chat.id, f'''✅ Ваша подписка оформлена! 🎧
[🔗 Нажмите здесь, чтобы перейти в канал!]({config["other"]["link_for_joining"]})''', parse_mode="Markdown")
        await update_payment_info(user_id, 1)

@bot.chat_join_request_handler()
async def allow_request(message: types.ChatJoinRequest):
    user_id = message.from_user.id
    users_or_value = await get_users()
    if users_or_value == 'Not having db files':
        await bot.send_message(599202079, text = f'Были удалены все БД. Пользователь {message.from_user.username} после возможной оплаты не смог добавить к каналу. Необходимо проверить платеж и добавить человека', parse_mode="HTML") 
        sys.exit()
        
    payments_info = {el[0] : el[2] for el in users_or_value}

    if payments_info[user_id] == True:
        await bot.send_message(message.from_user.id, 
        '''🎶 Добро пожаловать в "Город Поющих Мостов"! 🌉

Вы успешно подключились к нашему эксклюзивному каналу, где звучат мелодии слов и волшебство сюжета. Приготовьтесь к путешествию по страницам этой захватывающей истории. Приятного прослушивания! 📖🎧''')	 
        await bot.send_message(599202079, f"{message.from_user.username if message.from_user.username is not None else 'Empty'}_{user_id} оплатил доступ" )
        await bot.approve_chat_join_request(
                message.chat.id,                                   
                message.from_user.id
        )

    else:
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("Получить доступ", callback_data="to_buying_enter")
        markup.add(btn)
        await bot.send_message(message.from_user.id, 
        '''Мы заметили, что вы активировали ссылку на "Город Поющих Мостов", но оплата еще не была подтверждена. 

Для полного доступа к аудиокниге, пожалуйста, завершите процесс оплаты. Если у вас возникли трудности или вопросы, мы всегда готовы помочь! 💳📖''', 
        reply_markup=markup)	 

if __name__ == '__main__':
    path_to_db = config['db']['source_db_path']
    path_to_dest = config['db']['dest_db_path']
        
    if not os.path.isfile(path_to_db) and not os.path.isfile(config['db']['dest_db_path']):
        asyncio.run(connect_and_create_db(isFirst=True))

    asyncio.run(bot.polling(non_stop=True, request_timeout=90))
