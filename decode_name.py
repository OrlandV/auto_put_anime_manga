"""
Функции декодирования символов Юникод или их замены.
"""
import re
import dateutil.parser as date_parser
import datetime


def decode_name(name: str) -> str:
    """
    Декодирование символов Юникод в наименовании.
    :param name: Наименование с закодированными символами.
    :return: Декодированное наименование.
    """
    return re.sub(r'&#(\d+);', lambda m: chr(int(m[1])), name)


def normal_name(name: str) -> str:
    """
    Нормализация наименования. Удаление пунктуации и замена символов «ō» и «ū» на «ou» и «uu».
    :param name: Наименование.
    :return: Нормализованное наименование.
    """
    name = name.lower().replace('ō', 'ou').replace('ū', 'uu').replace('×', 'x')
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
