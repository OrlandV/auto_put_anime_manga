import MySQLdb


class DB:
    def __init__(self, *param):
        self._db = MySQLdb.connect(*param)

    def dict_fetch_all(self, query: str, all_one: bool = False) -> list[dict] | dict:
        """
        Преобразование строк курсора (кортежей) в словари.
        (Идея функции взята из документации Django.)
        :param query: Строка SQL-запроса.
        :param all_one: Переключатель между fetchall (False) и fetchone (True).
        :return: Если all_one == True, то возвращает словарь с результатом запроса (dict).
            Если all_one == False, то возвращает список словарей с результатами запроса (list[dict]).
        """
        with self._db.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            if all_one:
                return dict(zip(columns, cursor.fetchone()))
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def execute(self, query: str, param: tuple = ()) -> int:
        with self._db.cursor() as cursor:
            cursor.execute(query, param)
            self._db.commit()
            return cursor.lastrowid

    def _fetch(self, query: str) -> dict | None:
        try:
            return self.dict_fetch_all(query, True)
        except TypeError:
            return
