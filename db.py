"""
Интерфейс БД.
"""
from PIL import Image
from urllib.request import urlopen

import db_connect.connect as dbc
from config import DB_CONNECT, PATH


class DB(dbc.DB):
    """
    Интерфейс БД.
    Класс-родитель — db_connect.connect.DB.
    """

    # Кортеж полей таблиц БД.
    # Для минимизации ошибок (опечаток) в указании имён полей далее вместо указания имени поля
    # указывается индекс в кортеже: self.fields[1].
    # В данном кортеже перечислены все поля из БД, но на данном этапе разработки в классе используются не все.
    fields = (
        "id",  # 0
        "name",  # 1
        "format",  # 2
        "number_of_episodes",  # 3
        "duration",  # 4
        "studio",  # 5
        "director",  # 6
        "rip",  # 7
        "subs",  # 8
        "rusvoiceover",  # 9
        "name_orig",  # 10 title
        "name_rom",  # 11
        "name_eng",  # 12
        "name_rus",  # 13
        "date_of_premiere",  # 14
        "genre",  # 15
        "name_orig",  # 16 ФИО
        "name_rom",  # 17
        "name_rus",  # 18
        "author_of_rip",  # 19
        "container",  # 20
        "videocodek",  # 21
        "resolution",  # 22
        "fps",  # 23
        "bitrade_of_video",  # 24
        "author_of_release",  # 25
        "type_of_",  # 26
        "audiocodek",  # 27
        "bitrade_of_audio",  # 28
        "hz",  # 29
        "channales",  # 30
        "notes",  # 31
        "w",  # 32
        "h",  # 33
        "author_of_rusvoiceover",  # 34
        "in_container",  # 35
        "author_of_translate",  # 36
        "author_of_subs",  # 37
        "format_of_subs",  # 38
        "viewed",  # 39
        "edited",  # 40
        "author_of_manga",  # 41
        "number_of_volumes",  # 42
        "number_of_chapters",  # 43
        "publishing",  # 44
        "publication",  # 45
        "translate",  # 46
        "translated_chapters",  # 47
        "readed_chapters",  # 48
        "type_of_publication",  # 49
        "manga",  # 50
        "anime",  # 51
        "adaptation",  # 52
        "person",  # 53
        "author"  # 54
    )

    def __init__(self):
        super().__init__(*DB_CONNECT)

    def __get_id(self, query: str, _fni: int = 0, _value: str | None = None) -> int | None:
        """
        Выполнение запроса из БД ID (указанного значения в указанной таблице).
        На случай, когда находится значение, содержащее искомое, раньше самого искомого, проводится проверка
        на равенство. Если равенство не выполняется, поиск продолжается.
        :param query: SQL-запрос.
        :param _fni: Индекс таблицы в кортеже полей self.fields.
        :param _value: Искомое значение.
        :return: ID значения (в соответствующей таблице) или None.
        """
        id_d = self._fetch(query)
        if id_d:
            if _fni and _value:
                query = (f'SELECT {self.fields[1]} FROM {self.fields[_fni]} '
                         f'WHERE {self.fields[0]} = {id_d[self.fields[0]]}')
                res = self._fetch(query)
                if res and res[self.fields[1]] != _value:
                    query = f'SELECT * FROM {self.fields[_fni]} WHERE InStr({self.fields[1]}, "{_value}") > 0'
                    res = self.dict_fetch_all(query)
                    for rec in res:
                        if rec[self.fields[1]] == _value:
                            return rec[self.fields[0]]
            return id_d[self.fields[0]]
        else:
            return

    def add(self, fni: int, data: dict[str, str]) -> int:
        """
        Добавление данных по сущности, имя которой определяется по индексу в кортеже полей.
        :param fni: Индекс таблицы в кортеже полей self.fields.
        :param data: Словарь данных по сущности.
        :return: Присвоенный ID.
        """
        query = f'INSERT INTO {self.fields[fni]} VALUES (DEFAULT, '
        if fni == 53:
            query += ((f'"{data[self.fields[16]]}"' if self.fields[16] in data and data[self.fields[16]] else "NULL") +
                      ', ' + f'"{data[self.fields[17]]}", ' +
                      (f'"{data[self.fields[18]]}"' if self.fields[18] in data and data[self.fields[18]] else "NULL"))
        else:
            f = fni if fni in (23, 29) else 1
            query += f'"{data[self.fields[f]]}"'
        query += ')'
        return self.execute(query)

    def add_anime(self, data: dict[str, str | int | list[str | dict[str, str] | int]]) -> int:
        """
        Добавление данных по anime.
        :param data: Словарь данных по anime:
            {
                'name_orig': str,
                'name_rom': str,
                'name_eng': str,
                'name_rus': str,
                'format': str,
                'number_of_episodes': int,
                'duration': str,
                'date_of_premiere': str,
                'studio': list[str],
                'director': list[dict[str, str]],
                'genre': list[str],
                'notes': str,
                'manga': list[int | dict[str, str]]
            }
        :return: Присвоенный ID anime в БД.
        """
        query = (f'INSERT INTO {self.fields[51]} VALUES (DEFAULT, '
                 f'"{data[self.fields[10]]}", '
                 f'"{data[self.fields[11]]}", ' +
                 (f'"{data[self.fields[12]]}"' if self.fields[12] in data and data[self.fields[12]] else "NULL") +
                 ', ' +
                 (f'"{data[self.fields[13]]}"' if self.fields[13] in data and data[self.fields[13]] else "NULL") + ', '
                 f'{self.get_id_add(2, data[self.fields[2]])}, '
                 f'{data[self.fields[3]]}, '
                 f'"{data[self.fields[4]]}", '
                 f'"{data[self.fields[14]]}", ' +
                 (f'"{data[self.fields[31]]}"' if self.fields[31] in data and data[self.fields[31]] else "NULL") + ')')
        aid = self.execute(query)
        for f in (5, 6, 15, 50):
            if self.fields[f] in data and data[self.fields[f]]:
                for value in data[self.fields[f]]:
                    if value:
                        if isinstance(value, int):
                            id_ = value
                        else:
                            if f in (5, 15):
                                id_ = self.get_id(f, value)
                                if not id_:
                                    id_ = self.add(f, {self.fields[1]: value})
                            elif f == 6:
                                id_ = self.get_id(53, value)
                                if not id_:
                                    id_ = self.add(53, value)
                            else:
                                id_ = self.get_id(50, value[self.fields[11]])
                        if id_:
                            query = (f"INSERT INTO {f'{self.fields[51]}_{self.fields[f]}' if f in (5, 15) else
                                     self.fields[52 if f == 50 else f]} VALUES ({aid}, {id_})")
                            self.execute(query)
        return aid

    def add_manga(self, data: dict[str, str | int | list[dict[str, str] | str]]) -> int:
        """
        Добавление данных по манге.
        :param data: Словарь данных по манге:
            {
                'name_orig': str,
                'name_rom': str,
                'name_eng': str,
                'name_rus': str,
                'author_of_manga': list[dict[str, str]],
                'number_of_volumes': int,
                'number_of_chapters': int,
                'date_of_premiere': str,
                'publication': list[dict[str, str]],
                'genre': list[str],
                'notes': str
            }
        :return: Присвоенный ID манге в БД.
        """
        query = (f'INSERT INTO {self.fields[50]} VALUES (DEFAULT, '
                 f'"{data[self.fields[10]]}", '
                 f'"{data[self.fields[11]]}", ' +
                 (f'"{data[self.fields[12]]}"' if self.fields[12] in data and data[self.fields[12]] else "NULL") +
                 ', ' +
                 (f'"{data[self.fields[13]]}"' if self.fields[13] in data and data[self.fields[13]] else "NULL") + ', '
                 f'{data[self.fields[42]]}, '
                 f'{data[self.fields[43]]}, '
                 f'"{data[self.fields[14]]}", ' +
                 (f'"{data[self.fields[31]]}"' if self.fields[31] in data and data[self.fields[31]] else "NULL") + ')')
        mid = self.execute(query)
        for f in (41, 45, 15, 51):
            if self.fields[f] in data and data[self.fields[f]]:
                for value in data[self.fields[f]]:
                    if value:
                        if isinstance(value, int):
                            id_ = value
                        else:
                            if f == 41:
                                id_ = self.get_id(53, value)
                                if not id_:
                                    id_ = self.add(53, value)
                            elif f == 45:
                                id_ = self.get_id(f, value[self.fields[f]])
                                if not id_:
                                    id_ = self.add_publication(value)
                            elif f == 15:
                                id_ = self.get_id(f, value)
                                if not id_:
                                    id_ = self.add(f, {self.fields[1]: value})
                            else:
                                id_ = self.get_id(51, value[self.fields[11]])
                        if id_:
                            query = (f"INSERT INTO {self.fields[f] if f == 52 else (
                                self.fields[f] if f == 41 else f'{self.fields[50]}_{self.fields[f]}')} "
                                     f"VALUES ({id_ if f == 52 else mid}, {mid if f == 52 else id_})")
                            self.execute(query)
        return mid

    def add_publication(self, data: dict[str, str]) -> int:
        """
        Добавление данных по изданию.
        :param data: Словарь данных по изданию:
            {
                'name': str,
                'publishing': str,
                'type_of_publication': str  # необязательно
            }
        :return: Присвоенный ID изданию в БД.
        """
        query = (f'INSERT INTO {self.fields[45]} VALUES (DEFAULT, '
                 f'"{data[self.fields[1]] if self.fields[1] in data else data[self.fields[45]]}", '
                 f'{self.get_id_add(49, data[self.fields[49]] if self.fields[49] in data else 1)}, '
                 f'{self.get_id_add(44, data[self.fields[44]])})')
        return self.execute(query)

    def get_anime_id(self, data: dict[str, str | int | list[str | dict[str, str] | int]]) -> int | None:
        """
        Запрос из БД ID anime.
        :param data: Словарь данных по anime.
        :return: ID anime или None.
        """
        return self.get_id(51, data)

    def get_id(self, fni: int, value: dict[str, str | int | list[str | dict[str, str] | int]] | int | str
               ) -> int | None:
        """
        Запрос из БД ID указанного значения в указанной таблице.
        :param fni: Индекс таблицы в кортеже полей self.fields.
        :param value: Искомое значение.
        :return: ID значения в соответствующей таблице или None.
        """
        if fni in (50, 51):
            query = (f'SELECT {self.fields[0]} FROM {self.fields[fni]} WHERE ({self.fields[16]} = '
                     f'"{value['name_orig']}") OR ({self.fields[17]} = "{value['name_rom']}")')
            return self.__get_id(query)
        query_ = f'SELECT {self.fields[0]} FROM {self.fields[fni]} WHERE InStr('
        if fni == 53:
            query = f'{query_}{self.fields[17]}, "{value[self.fields[17]]}") > 0'
            res = self.__get_id(query)
            if not res and self.fields[16] in value and value[self.fields[16]]:
                query = f'{query_}{self.fields[16]}, "{value[self.fields[16]]}") > 0'
                res = self.__get_id(query)
            if not res and self.fields[16] in value and value[self.fields[16]]:
                query = f'{query_}{self.fields[16]}, "{value[self.fields[16]].replace(' ', '')}") > 0'
                res = self.__get_id(query)
        else:
            query = f'SELECT {self.fields[0]} FROM {self.fields[fni]} WHERE {self.fields[1]} = "{value}"'
            res = self.__get_id(query, fni, value)
        return res

    def get_id_add(self, fni: int, value: int | str) -> int:
        """
        Запрос из БД ID указанного значения в указанной таблице.
        Если значение в таблице отсутствует, то значение добавляется, а присвоенный ID возвращается.
        :param fni: Индекс таблицы в кортеже полей self.fields.
        :param value: Искомое значение.
        :return: ID значения в соответствующей таблице.
        """
        if not isinstance(value, int):
            id_ = self.get_id(fni, value)
            if not id_:
                id_ = self.add(fni, {self.fields[1]: value})
            return id_
        return value

    def get_manga_id(self, data: dict[str, str | int | list[dict[str, str] | str]]) -> int | None:
        """
        Запрос из БД ID манги.
        :param data: Словарь данных по манге.
        :return: ID манги или None.
        """
        return self.get_id(50, data)


def save_poster(url: str, id_: int, am: bool = False) -> None:
    """
    Сохранение микропостера.
    :param url: URL-адрес постера.
    :param id_: ID anime или манги в БД (возвращённое add_anime или add_manga).
    :param am: Переключатель anime/manga (False/True).
    """
    img = Image.open(urlopen(url))
    img.thumbnail((100, 100))
    img.save(f'{PATH}{'m' if am else 'a'}/{id_}.jpg')
