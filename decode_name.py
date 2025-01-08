"""
Функции декодирования символов Юникод или их замены.
"""
import re


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
    name = name.lower().replace('ō', 'ou').replace('ū', 'uu')
    chars = 'abcdefghijklmnopqrstuvwxyz 0123456789'
    name2 = ''
    for i in range(len(name)):
        if name[i] in chars:
            name2 += name[i]
    return name2


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
