import aiohttp
from selectolax.lexbor import LexborHTMLParser as HTMLParser
from notifier import send_lead

KEYWORDS = ["telegram", "бот", "parser", "парсер", "next.js", "python", "автоматизация"]


async def run_job_parser():
    # Пример запроса к условной API или доске заказов
    url = "https://habr.com/ru/all/"  # Или любая другая площадка с заказами
    async with aiohttp.ClientSession() as session:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return
                html = await resp.text()
                tree = HTMLParser(html)

                # Пример парсинга блоков (селекторы адаптируются под целевой ресурс)
                for article in tree.css("article.tm-article-snippet"):
                    title_node = article.css_first("h2.tm-title a")
                    if title_node:
                        title = title_node.text(strip=True)
                        link = "https://habr.com" + title_node.attributes.get("href", "")

                        if any(kw in title.lower() for kw in KEYWORDS):
                            await send_lead(
                                source="Job Parser",
                                title=title,
                                details="Найден горячий спрос по ключевым словам",
                                link=link
                            )
        except Exception as e:
            print(f"Ошибка в job_parser: {e}")