"""
Функции декодирования символов Юникод или их замены, а так же преобразования даты и времени (продолжительности).
"""
import re
import dateutil.parser as date_parser
import datetime


def decode_name(name: str) -> str:
    """
    Декодирование символов Юникод и шестьнадцатиричных кодов в наименовании.
    :param name: Наименование с закодированными символами.
    :return: Декодированное наименование.
    """
    return re.sub(r'&#x(\w+);', lambda m: chr(int(m[1], 16)),
                  re.sub(r'&#(\d+);', lambda m: chr(int(m[1])), name.replace('&#160;', ' ')))


def o_ou(name: str) -> str:
    """
    Функция-сокращение записи замены символов «ō» и «ū» на «ou» и «uu».
    :param name: Наименование.
    :return: Отредактированное наименование.
    """
    # Используется в модулях отдельно.
    return name.replace('ō', 'ou').replace('ū', 'uu')


def normal_name(name: str) -> str:
    """
    Нормализация наименования. Удаление пунктуации и замена символов «ō» и «ū» на «ou» и «uu».
    :param name: Наименование.
    :return: Нормализованное наименование.
    """
    name = (o_ou(decode_name(name)).lower().replace('×', 'x').replace('_', ' ').
            replace('ö', 'o').replace('-', ' ').strip())
    chars = 'abcdefghijklmnopqrstuvwxyz 0123456789'
    name2 = ''
    for i in range(len(name)):
        if name[i] in chars:
            name2 += name[i]
    return re.sub(r'\s+', ' ', name2)


def points_codes(text: str) -> str:
    """
    Замена не буквенно-цифровых символов их кодами в формате «&#1;»–«&#127;».
    :param text: Текст.
    """
    text = text.replace('—', '-').replace('…', '...').replace('½', '1/2')
    points = (list(range(1, 32)) + list(range(33, 36)) + [37] + list(range(40, 48)) +
              list(range(58, 65)) + list(range(91, 97)) + list(range(123, 128)))
    text2 = ''
    for i in range(len(text)):
        p = ord(text[i])
        text2 += f'&#{p};' if p in points else text[i]
    return text2


def month(date: str) -> str:
    """
    Формирование строки даты в формате yyyy-mm-dd для указанных года и месяца.
    :param date: Строка с датой из года и месяца.
    :return: Строка даты в формате yyyy-mm-dd.
    """
    date = date_parser.parse(date)
    date = datetime.date(date.year + (date.month == 12), (date.month + 1 if date.month < 12 else 1),
                         1) - datetime.timedelta(1)
    return date.strftime('%Y-%m-%d')


def title_index(dict_: dict, title: str, index: int = 1) -> str:
    """
    Добавление индекса к строке (наименованию), если строка имеется в словаре как ключ.
    Проверка рекурсивная до определения свободного индекса.
    :param dict_: Словарь для сверки строки с ключами.
    :param title: Строка (наименование).
    :param index: Индекс.
    :return: Строка с индексом.
    """
    ttl = f'{title} ({index})' if index > 1 else title
    return title_index(dict_, title, index + 1) if ttl in dict_ else ttl


def hours_minutes(minutes: int) -> str:
    """
    Конвертирование числа минут в строку формата hh:mm.
    :param minutes: Число минут.
    :return: Строка формата hh:mm.
    """
    hours = 0
    if minutes > 59:
        hours = minutes // 60
        minutes = minutes - 60 * hours
    res = datetime.time(hours, minutes)
    return res.isoformat('minutes')
