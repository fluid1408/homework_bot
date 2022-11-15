import logging
import os
import time
import sys

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID")

TOKENS_ALL = ("PRACTICUM_TOKEN", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}
ERROR_DICTONARY = "Ответ пришел не в виде словаря. Тип данных: {}."
ERROR_KEY = "Ответ пришел не в виде ключа. Тип данных: {}."
ERROR_LIST = "Ответ пришел не в виде списка. Тип данных: {}."
MESSAGE_DEBUG = "Ошибка отправки сообщения {}"
EXCEPTION_ERROR = "Ошибка {}"
STATUS_HOMEWORK = "Полученный статус {} не определён в словаре HOMEWORK."
PARSE_STATUS = 'Изменился статус проверки работы "{}".{}'


HOMEWORK_STATUSES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(stream=sys.stdout)
file_handler = logging.FileHandler("homeworkbot.log", mode="w")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def send_message(bot, message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(MESSAGE_DEBUG.format(message))

    except telegram.error.TelegramError as error:
        logger.exception(EXCEPTION_ERROR.format(error))


def get_api_answer(current_timestamp):
    params = {"from_date": current_timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    return response.json()


def check_response(response):
    if not isinstance(response, dict):
        raise TypeError(ERROR_DICTONARY.format(type(response)))
    if "homeworks" not in response:
        raise KeyError(ERROR_KEY.format("homeworks"))
    homeworks = response.get("homeworks")
    if not isinstance(homeworks, list):
        raise TypeError(ERROR_LIST.format(type(homeworks)))
    return homeworks


def parse_status(homework):
    homework_name = homework["homework_name"]
    homework_status = homework["status"]

    if homework_status not in HOMEWORK_STATUSES:
        raise ValueError(STATUS_HOMEWORK).format(homework_status)
    return PARSE_STATUS.format(
        homework_name, HOMEWORK_STATUSES[homework_status]
    )


def check_tokens():
    status = True
    for check in TOKENS_ALL:
        if not globals()[check]:
            status = False
    return status


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0

    while True:
        try:
            response = get_api_answer(current_timestamp)
            correct_response = check_response(response)
            message = parse_status(correct_response[0])
            send_message(bot, message)

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logging.error(message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == "__main__":
    main()
