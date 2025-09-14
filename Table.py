"""
Таблица, выводимая в консоль
"""


class Content:
    """
    Контент
    """
    _index = 0  # Текущий номер.

    def __init__(self, data: dict[str, str | list[dict[str, str]] | int | list[str] | None], number: int | None = None):
        """
        :param data: Словарь данных по контенту.
        :param number: Начальный номер.
        """
        if number:
            self.number = number
            if number > Content._index:
                Content._index = number
        else:
            Content._index += 1
            self.number = Content._index
        for key, value in data.items():
            if value is None or (isinstance(value, list) and not len(value)):
                setattr(self, key, "")
            elif isinstance(value, str):
                setattr(self, key, value)
            elif isinstance(value, int):
                setattr(self, key, str(value))
            elif not isinstance(value[0], dict):
                setattr(self, key, ", ".join(map(str, value)))
            else:
                s = []
                for el in value:
                    s.append(" / ".join(map(str, el.values())))
                setattr(self, key, ", ".join(s))


class Table:
    """
    Таблица
    """

    def __init__(self, data: list[dict[str, str | list[dict[str, str]] | int | list[str] | None]], caption: str = '',
                 number: int | None = None):
        """
        :param data: Данные для таблицы.
        :param caption: Заголовок.
        :param number: Начальный номер.
        """
        self.caption = caption
        self.result = ''  # Текст (строка) для вывода в консоль.
        self.name_length = dict(number=1)  # Длины строк-ячеек.
        self.contents = []
        for i, content_ in enumerate(data):
            content = Content(content_, number if not i else None)
            self._set_name_length(content)
            self.contents.append(content)
        self._set_result()

    def _set_name_length(self, content: Content):
        """
        Установка длин строк-ячеек.
        :param content: Объект Content, выводимый в строку таблицы, ячейки которой будут сравниваться
            с ранее установленными длинами.
        """
        for key, item in vars(content).items():
            k = len(key)
            x = len(str(item))
            if key not in self.name_length or self.name_length[key] < x:
                self.name_length[key] = max(k, x)

    def _set_result(self):
        """
        Формирование текста для вывода в консоль.
        """
        # Ширина таблицы.
        width = sum(i for i in self.name_length.values()) + int(0.55 * self.name_length['name_orig'])
        width += 3 * len(self.name_length)
        # Заголовок таблицы.
        self.result += f'{'-' * width}\n'
        self.result += f'{self.caption:^{width}}\n'
        self.result += f'{'—' * width}\n'
        # Заголовки столбцов таблицы.
        self.result += f'{'№':^{self.name_length['number']}}'
        for key, item in self.name_length.items():
            if key != 'number':
                self.result += f' | {key:^{int(1.55 * item) if key == 'name_orig' else (
                    item + 3 if key in ('author_of_manga', 'director') else item)}}'
        self.result += f'\n{'—' * width}'
        # Данные.
        for content in self.contents:
            self.result += '\n'
            for cell in self.name_length.keys():
                if cell != 'number':
                    self.result += ' | '
                self.result += f'{getattr(content, cell) if hasattr(content, cell) else "":^{self.name_length[cell]}}'
        self.result += f'\n{'—' * width}'

    def __str__(self):
        return self.result
