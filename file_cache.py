"""
Работа с временными файлами:

    а) HTML/XML, полученными пользователем через браузер;

    б) TXT с новыми жанрами.
"""


def anti_bot(_res: str, url: str, ext: str = "html") -> str:
    """
    Вариант ручного обхода анти-бот-защиты.
    :param _res: Краткое наименование ресурса: ANN/WP.
    :param url: Адрес страницы на ресурсе или запрос к ресурсу (ссылка).
    :param ext: Формат ожидаемых и сохраняемых данных: html/xml.
    :return: Содержимое сохранённого пользователем файла в строковом формате.
    """
    ext = ext.lower()
    print(f"Анти-бот-защита {_res}!\n1. Откройте в своём браузере ссылку")
    print(url)
    print("2. Откройте исходный код страницы.\n"
          f"3. Скопируйте (с заменой) {"XML-структуру" if ext == "xml" else "HTML-код"} в файл «{_res}_temp.{ext}», "
          "находящийся в папке проекта.\n"
          "4. Когда файл будет готов, просто нажмите здесь ENTER.")
    input()
    with open(f"{_res}_temp.{ext}", encoding="utf8") as file:
        return file.read()


class NewGenre:
    """
    Кэш новых жанров, которые пользователю желательно перенести из TXT-файла в «config.py» после завершения работы кэша.
    """
    def __init__(self, _res: str):
        """
        Создание экземпляра кэша новых жанров.
        :param _res: Краткое наименование ресурса: ANN/WP.
        """
        self.res = _res
        self.filepath = f"{_res}_new_genres.txt"  # Путь к TXT-файлу.
        self.content = {}  # Кэш — словарь: жанр_на_ресурсе = жанр_на_World_Art.
        self.load()

    def load(self) -> None:
        """
        Загрузка кэша — текущего содержимого TXT-файла.
        """
        with open(self.filepath, "r", encoding="utf8") as file:
            ng = file.readlines()
        for g in ng:
            z = g.find(":")
            self.content.update({g[:z]: g[z + 2:-1]})

    def search(self, genre: str) -> str | None:
        """
        Поиск жанра в кэше.
        :param genre: Жанр на ресурсе.
        :return: Жанр на World Art, если жанр найден в кэше, либо None.
        """
        if genre in self.content:
            return self.content[genre]

    def add(self, genre: str) -> None:
        """
        Добавление жанра в кэш.
        :param genre: Жанр на ресурсе.
        """
        self.content[genre] = input("Наименование жанра на русском (как на World Art): ")

    def search_or_add(self, genre: str) -> str | None:
        """
        Поиск жанра в кэше и добавление его, если не найден.
        :param genre:  Жанр на ресурсе.
        :return: Жанр на World Art, если жанр найден в кэше или добавлен,
            либо None, если пользователь отказался добавлять жанр.
        """
        if res := self.search(genre):
            return res
        else:
            print(f"\nНовый жанр в {self.res}!", genre)
            add = input("Добавить жанр? Y/N: ")
            if add in ("Y", "y"):
                self.add(genre)
                return self.content[genre]

    def save(self) -> None:
        """
        Сохранение кэша в TXT-файл.
        """
        txt = ""
        for ag, g in self.content.items():
            txt += f"{ag}: {g}\n"
        with open(self.filepath, "w", encoding="utf8") as file:
            file.write(txt)
        print(f"Перенесите новые жанры в «config.py» из «{self.filepath}».")

    def __del__(self):
        """
        Сохранение не пустого кэша при завершении работы кэша.
        """
        if len(self.content):
            self.save()
