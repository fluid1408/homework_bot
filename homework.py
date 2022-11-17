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

TOKENS = ("PRACTICUM_TOKEN", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}
ERROR_DICTONARY = "Ответ пришел не в виде словаря. Тип данных: {}."
ERROR_KEY = "Ответ пришел не в виде ключа. Тип данных: {}."
ERROR_LIST = "Ответ пришел не в виде списка. Тип данных: {}."
MESSAGE_DEBUG = "Ошибка отправки сообщения {}"
MAIN_EXCEPTION_ERROR = "Ошибка {}"
MAIN_EXCEPTION_ERROR_MESSAGE = "Сбой в работе программы"
STATUS_HOMEWORK = "Полученный статус {} не определён в словаре HOMEWORK."
PARSE_STATUS = 'Изменился статус проверки работы "{}".{}'
GET_API_ANSWER_RESPONSE_STATUS_ERROR = (
    """
Статус сервера: {}.
Данные запроса: url = {url}, headers = {headers}, params = {params}
"""
)
JSON_ERRORS = ["error", "code"]
CHECK_TOKENS_CRITICAL_LOG = "Отсутствие обязательной переменной окружения {} "
SERVER_DENIAL_ERROR = "Отказ в обслуживании {}"
GET_API_ANSWER_REQUEST_ERROR = "Ошибка ответа запроса к API {}"

HOMEWORK_STATUSES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(stream=sys.stdout)
file_handler = logging.FileHandler(__file__ + '.log', mode='w')
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class RequestToYandexPracticumError(Exception):
    """Статус ответа от эндпоинта отличается от 200."""

    pass


class ServerError(Exception):
    """Ошибка сервера."""

    pass


def send_message(bot, message):
    """Отправка сообщения ботом."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(MESSAGE_DEBUG.format(message))
        return True

    except telegram.error.TelegramError as error:
        logger.exception(MAIN_EXCEPTION_ERROR.format(error))


def get_api_answer(current_timestamp):
    """Запрос к API."""
    params = {"from_date": current_timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    request_data = dict(
        url=ENDPOINT, headers=HEADERS, params={"from_date": current_timestamp}
    )
    try:
        response = requests.get(request_data)
    except requests.exceptions.RequestException as request_error:
        raise ConnectionError(
            GET_API_ANSWER_REQUEST_ERROR.format(request_error, request_data)
        )
    json = response.json()
    for error in JSON_ERRORS:
        if error in json:
            raise ServerError(
                SERVER_DENIAL_ERROR.format(
                    error, JSON_ERRORS[error], request_data
                )
            )
    if response.status_code != 200:
        raise RequestToYandexPracticumError(
            GET_API_ANSWER_RESPONSE_STATUS_ERROR.format(
                response.status_code, request_data
            )
        )
    return json


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(ERROR_DICTONARY.format(type(response)))
    if "homeworks" not in response:
        raise KeyError(ERROR_KEY.format("homeworks"))
    homeworks = response.get("homeworks")
    if not isinstance(homeworks, list):
        raise TypeError(ERROR_LIST.format(type(homeworks)))
    return homeworks


def parse_status(homework):
    """Получение статуста домашней работы."""
    name = homework["homework_name"]
    status = homework["status"]

    if status not in HOMEWORK_STATUSES:
        raise ValueError(STATUS_HOMEWORK).format(status)
    return PARSE_STATUS.format(
        name, HOMEWORK_STATUSES[status]
    )


def check_tokens():
    """Проверка переменных окружения."""
    status = True
    for check in TOKENS:
        if not globals()[check]:
            logger.critical(CHECK_TOKENS_CRITICAL_LOG.format(check))
            status = False
    return status


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        return
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    last_error_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            message = parse_status(homeworks[0])
            if send_message(bot, message):
                current_timestamp = response.get(
                    "current_date", current_timestamp
                )

        except Exception as error:
            message = MAIN_EXCEPTION_ERROR_MESSAGE.format(error)
            logger.exception(message)
            if message != last_error_message:
                if send_message(bot, message):
                    last_error_message = message

        finally:
            time.sleep(RETRY_TIME)


if __name__ == "__main__":
    main()
