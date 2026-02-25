from config import WINDOWS_VER, FIREFOX_VER

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
WPE_SEARCH = 'https://en.wikipedia.org/w/index.php?title=Special%3ASearch&fulltext=1&ns0=1&search='

AMU = 'https://api.mangaupdates.com/v1/'
AMUS = AMU + 'series/'
AMUA = AMU + 'authors/'
WMU = 'http://www.mangaupdates.com/series.html'

USER_AGENT = (f'Mozilla/5.0 (Windows NT {WINDOWS_VER}.0; Win64; x64; rv:{FIREFOX_VER}) '
              f'Gecko/20100101 Firefox/{FIREFOX_VER}')
