import scrapy
from bs4 import BeautifulSoup
from common.io_handler.io_handler import IOHandler


class FinVizSpider(scrapy.Spider):
    name = "finviz_spider"
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36"
    }

    _current_symbol_index = 0

    def __init__(self, symbols: list[str], io_handler: IOHandler, *args, **kwargs):
        super(FinVizSpider, self).__init__(*args, **kwargs)

        self._symbols = symbols
        self._io_handler = io_handler
        self._data = self._io_handler.read()

        url = self._get_current_url()
        self.start_urls = [url] if url else []

    def parse(self, response):
        current_symbol = self._get_current_symbol()
        # Guard against index overflow
        if not current_symbol:
            return

        stat_name_1 = innertext(
            response.css("table.js-snapshot-table tr:nth-child(5) td:nth-child(5)")
        )
        stat_name_2 = innertext(
            response.css("table.js-snapshot-table tr:nth-child(6) td:nth-child(5)")
        )
        # Guard against changing layout, which may lead to wrong number
        if stat_name_1 != "EPS next Y" or stat_name_2 != "EPS next 5Y":
            raise Exception("FinViz table layout has changed.")
        stat_value_1 = innertext(
            response.css("table.js-snapshot-table tr:nth-child(5) td:nth-child(6)")
        )
        stat_value_2 = innertext(
            response.css("table.js-snapshot-table tr:nth-child(6) td:nth-child(6)")
        )
        additional_data = {
            "eps_growth_projection_1y": parse_percentage(stat_value_1),
            "eps_growth_projection_5y": parse_percentage(stat_value_2),
        }
        self._data[current_symbol] = {
            **self._data.get(current_symbol, {}),
            **additional_data,
        }

        self._next_symbol()
        next_url = self._get_current_url()
        if next_url:
            yield response.follow(next_url, self.parse)
        else:
            self._io_handler.write(self._data)

    def _get_current_url(self):
        current_symbol = self._get_current_symbol()
        if current_symbol:
            return f"https://finviz.com/quote.ashx?t={current_symbol}&p=d"
        else:
            return None

    def _get_current_symbol(self):
        if self._current_symbol_index < len(self._symbols):
            return self._symbols[self._current_symbol_index]
        else:
            return None

    def _next_symbol(self):
        self._current_symbol_index += 1


def innertext(selector):
    """
    Reference: https://github.com/ddikman/scrapy-innertext
    """
    html = selector.get()
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text().strip()


def parse_percentage(percentage: str) -> float:
    return float(percentage[:-1]) / 100
