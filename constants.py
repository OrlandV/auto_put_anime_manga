from config import FIREFOX_VER

A = 'anime'
M = 'manga'

WA = 'http://www.world-art.ru/'
AN = 'animation'
WAA = WA + AN + '/'
WAAA = WAA + AN + '.php'
WAAM = WAA + M + '.php'

ANN = 'animenewsnetwork.com/'
_ANNE = f'{ANN}encyclopedia/'
ANNE = f'http://www.{_ANNE}'
CANNE = f'https://cdn.{_ANNE}'
SANNE = f'https://www.{_ANNE}'

WPE = 'http://en.wikipedia.org/wiki/'
WPES = 'https://en.wikipedia.org/wiki/'

AMU = 'https://api.mangaupdates.com/v1/'
AMUS = AMU + 'series/'
AMUA = AMU + 'authors/'
WMU = 'http://www.mangaupdates.com/series.html'

# USER_AGENT = UserAgent().firefox
USER_AGENT = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{FIREFOX_VER}) Gecko/20100101 Firefox/{FIREFOX_VER}'
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'Host': 'en.wikipedia.org',
    'Priority': 'u=0, i',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'TE': 'trailers',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': USER_AGENT
}
