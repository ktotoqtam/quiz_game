from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import requests

passable_tests = {}
checkbox_options = []
logining = False
tele_token = '5522035331:AAEgdpuFeH4TvobyHNr6vW7YaJdfRQKO90w'


async def finish_test(user_id, message):
    global checkbox_options
    result = passable_tests[user_id]['correctly_answered_questions'] / len(passable_tests[user_id]['test']['questions'])
    await message.reply_html(f"ваш процент прохождения теста: {str(result * 100)[:5]}%")
    del passable_tests[user_id]
    checkbox_options = []


async def ask_question(message, user_id):
    passable_test = passable_tests[user_id]

    if passable_test['num_question'] >= len(passable_test['test']['questions']):
        await finish_test(user_id, message)
        return

    question = passable_test['test']['questions'][passable_test['num_question']]
    if question['type'] == 'ord':
        await message.reply_html(question['question'])
    elif question['type'] == 'rad':
        buttons = [InlineKeyboardButton(text=option, callback_data=f'change_option;{option};{user_id}')
                   for option in question['question'][1]]
        reply_keyboard = [[]]
        for button in buttons:
            if len(reply_keyboard[-1]) < 3:
                reply_keyboard[-1].append(button)
            else:
                reply_keyboard.append([button])
        markup = InlineKeyboardMarkup(reply_keyboard)
        await message.reply_html(question['question'][0], reply_markup=markup)
    elif question['type'] == 'check':
        buttons = [InlineKeyboardButton(text=option, callback_data=f'change_checkbox;{option};{user_id}')
                   for option in question['question'][1]]
        reply_keyboard = [[]]
        for button in buttons:
            if len(reply_keyboard[-1]) < 3:
                reply_keyboard[-1].append(button)
            else:
                reply_keyboard.append([button])
        reply_keyboard.append([InlineKeyboardButton(text='отправить', callback_data=f'submit_options;{user_id}')])
        markup = InlineKeyboardMarkup(reply_keyboard)
        await message.reply_html(
            question['question'][0] + '\nвыберите несколько вариантов ответа', reply_markup=markup)


async def check_answer(answer, message, user_id):
    passable_test = passable_tests[user_id]
    question = passable_test['test']['questions'][passable_test['num_question']]
    if question['type'] == 'ord':
        if str(passable_test['test']['questions'][passable_test['num_question']]['answer']) == str(answer):
            passable_tests[user_id]['correctly_answered_questions'] += 1
        passable_tests[user_id]['num_question'] += 1
        await ask_question(message, user_id)


async def user_response_handler(update, context):
    if update.message.from_user.id in passable_tests.keys():
        await check_answer(update.message.text, update.message, update.message.from_user.id)
    if logining:
        user_id = requests.get(f'http://127.0.0.1:8080/api/telegram_keys/{update.message.text}')
        if str(user_id) == '<Response [404]>':
            await update.message.reply_text('Ключ не найден.')
        elif str(user_id) == '<Response [400]>':
            await update.message.reply_text('Ключ истёк.')
        elif str(user_id) == '<Response [200]>':
            with open('users.txt', 'r') as file1:
                lines = file1.readlines()
                if any([line.split(':')[0] == str(update.message.from_user.id) for line in lines]):
                    reply_keyboard = [[InlineKeyboardButton(
                        text='выйти', callback_data=f'logout;{update.message.from_user.id}')]]
                    markup = InlineKeyboardMarkup(reply_keyboard)
                    await update.message.reply_text('Вы уже авторизовались.', reply_markup=markup)
                    return
            with open('users.txt', 'w') as file:
                print(lines)
                if lines:
                    lines.append(f'\n{update.message.from_user.id}:{user_id.json()["user"]}')
                else:
                    lines.append(f'{update.message.from_user.id}:{user_id.json()["user"]}')
                file.writelines(lines)
                await update.message.reply_text('Вы авторизовались.')


async def start(update, context):
    if update.message.from_user.id in passable_tests.keys():
        del passable_tests[update.message.from_user.id]

    reply_keyboard = [[InlineKeyboardButton(text='показать все тесты',
                                            callback_data=f'get_all_tests;{update.message.from_user.id}')],
                      [InlineKeyboardButton(text='войти', callback_data=f'login')]]
    markup = InlineKeyboardMarkup(reply_keyboard)
    await update.message.reply_html('Здравсвуйте! Выберите действие.', reply_markup=markup)


async def callbacks_handler(update, context):
    global checkbox_options, logining
    if 'get_all_tests' in update.callback_query.data:
        tests = requests.get('http://127.0.0.1:8080/api/tests').json()['tests']
        for test in tests:
            message = f'''{test["name"].upper()} 
тема: {test["category"]}    количество вопросов: {len(test["questions"])} 
{test["about"]}'''
            reply_keyboard = [[InlineKeyboardButton(
                text='пройти', callback_data=f'take_test;{test["key"]};{update.callback_query.data.split(";")[1]}')]]
            markup = InlineKeyboardMarkup(reply_keyboard)
            await update.callback_query.message.reply_text(message, reply_markup=markup)
    elif 'take_test' in update.callback_query.data:
        user_id = int(update.callback_query.data.split(";")[2])
        key = update.callback_query.data.split(";")[1]
        if user_id in passable_tests.keys():
            await update.callback_query.message.reply_text('вы уже проходите тест')
        else:
            test = requests.get(f'http://127.0.0.1:8080/api/tests/{key}').json()['test']
            passable_tests[user_id] = {
                'test': test,
                'num_question': 0,
                'user_id': user_id,
                'correctly_answered_questions': 0
            }
            await ask_question(update.callback_query.message, user_id)
    elif 'change_option' in update.callback_query.data:
        user_id = int(update.callback_query.data.split(";")[2])
        if update.callback_query.data.split(";")[1] == \
                passable_tests[user_id]['test']['questions'][passable_tests[user_id]['num_question']]['answer']:
            passable_tests[user_id]['correctly_answered_questions'] += 1
        passable_tests[user_id]['num_question'] += 1
        await ask_question(update.callback_query.message, user_id)
    elif 'change_checkbox' in update.callback_query.data:
        option = update.callback_query.data.split(";")[1]
        checkbox_options.append(option)
        await update.callback_query.message.reply_text(f'вы выбрали {option}, чтобы отпраить ответы, нажмите отправить')
    elif 'submit_options' in update.callback_query.data:
        user_id = int(update.callback_query.data.split(";")[1])
        if set(checkbox_options) == set(
                passable_tests[user_id]['test']['questions'][passable_tests[user_id]['num_question']]['answer']):
            passable_tests[user_id]['correctly_answered_questions'] += 1
        passable_tests[user_id]['num_question'] += 1
        checkbox_options = []
        await ask_question(update.callback_query.message, user_id)
    elif 'login' in update.callback_query.data:
        await update.callback_query.message.reply_text(f'введите ключ')
        logining = True
    elif 'logout' in update.callback_query.data:
        with open('users.txt', 'r') as f:
            lines = f.readlines()
        lines = [line for line in lines if line.split(':') != update.callback_query.data.split(";")[1]]
        with open('users.txt', 'w') as f:
            f.writelines(lines)
        await update.callback_query.message.reply_text(f'вы вышли')


def main():
    application = Application.builder().token(tele_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(callbacks_handler))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, user_response_handler))
    application.run_polling()


if __name__ == '__main__':
    main()