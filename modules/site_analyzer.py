import asyncio
import re
import aiohttp
from urllib.parse import urljoin, quote, unquote
from selectolax.lexbor import LexborHTMLParser as HTMLParser
from notifier import send_lead

TARGET_QUERIES = [
    "автосервис официальный сайт услуги",
    "стоматология запись на прием сайт",
    "ремонт квартир цены заказать сайт",
    "доставка еды суши пицца сайт",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}


def extract_contacts(html: str) -> dict:
    if not html:
        return {"emails": [], "phones": [], "messengers": []}

    emails = list(set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html)))
    emails = [e for e in emails if
              not any(e.endswith(ext) for ext in ['.png', '.jpg', '.gif', '.svg', '.webp', '.js', '.css'])]

    phones = list(set(re.findall(r"(?:\+7|8)\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}", html)))
    messengers = list(set(re.findall(r"(?:https?://)?(?:t\.me|vk\.com|wa\.me|api\.whatsapp\.com)/\w+", html)))

    return {
        "emails": emails,
        "phones": phones,
        "messengers": messengers
    }


async def search_sites_by_query(session: aiohttp.ClientSession, query: str) -> list:
    url = "https://html.duckduckgo.com/html/"
    payload = {"q": query}
    search_headers = {
        **HEADERS,
        "Referer": "https://html.duckduckgo.com/",
        "Origin": "https://html.duckduckgo.com",
    }
    try:
        async with session.post(url, data=payload, headers=search_headers, timeout=12) as response:
            if response.status != 200:
                print(f"[-] DuckDuckGo вернул статус: {response.status}")
                return []

            html = await response.text()
            parser = HTMLParser(html)

            links = []
            for a in parser.css(".result__url"):
                href = a.attributes.get("href")
                if href and "uddg=" in href:
                    real_url = href.split("uddg=")[1].split("&")[0]
                    real_url = unquote(real_url)
                    if real_url.startswith("http"):
                        links.append(real_url)

            return list(set(links))[:6]
    except Exception as e:
        print(f"[-] Ошибка поиска по запросу {query}: {e}")
        return []


async def check_site(session: aiohttp.ClientSession, url: str):
    try:
        async with session.get(url, headers=HEADERS, timeout=8, allow_redirects=True) as response:
            html = await response.text()
            parser = HTMLParser(html)

            issues = []

            # 1. Проверка протокола
            if not url.startswith("https"):
                issues.append("Отсутствует SSL-сертификат (HTTP)")

            # 2. Проверка адаптивности
            viewport_meta = parser.css_first("meta[name='viewport']")
            if not viewport_meta:
                issues.append("Нет мобильной адаптации (отсутствует Viewport)")

            # 3. Проверка SEO заголовка и описания
            title_tag = parser.css_first("title")
            if not title_tag or len(title_tag.text().strip()) < 3:
                issues.append("Слабый или пустой Title")

            description_meta = parser.css_first("meta[name='description']")
            if not description_meta:
                issues.append("Отсутствует SEO-описание (Description)")

            # 4. Поиск устаревших элементов
            html_lower = html.lower()
            if "<marquee" in html_lower or "<center>" in html_lower or "<font" in html_lower:
                issues.append("Устаревший HTML-код (анахронизмы в верстке)")

            # 5. Проверка интерактивных элементов (форм захвата)
            forms = parser.css("form")
            if not forms:
                issues.append("Нет форм обратной связи / лид-форм")

            # 6. Проверка фавиконки
            favicon = parser.css_first("link[rel*='icon']")
            if not favicon:
                issues.append("Отсутствует Favicon")

            # Если изъянов нет — пропускаем сайт
            if not issues:
                return

            # Сбор контактов
            contacts = extract_contacts(html)

            if not contacts["emails"] and not contacts["phones"]:
                for link in parser.css("a"):
                    href = link.attributes.get("href")
                    if href:
                        lower_href = href.lower()
                        if any(k in lower_href for k in ["contact", "kontakty", "about", "o-nas", "связь"]):
                            contact_url = urljoin(url, href)
                            try:
                                async with session.get(contact_url, headers=HEADERS, timeout=5) as sub_resp:
                                    if sub_resp.status == 200:
                                        sub_html = await sub_resp.text()
                                        sub_contacts = extract_contacts(sub_html)
                                        contacts["emails"].extend(sub_contacts["emails"])
                                        contacts["phones"].extend(sub_contacts["phones"])
                                        contacts["messengers"].extend(sub_contacts["messengers"])
                                        break
                            except:
                                pass

            contacts["emails"] = list(set(contacts["emails"]))
            contacts["phones"] = list(set(contacts["phones"]))
            contacts["messengers"] = list(set(contacts["messengers"]))

            contact_info = []
            if contacts["emails"]:
                contact_info.append(f"📧 Email: {', '.join(contacts['emails'])}")
            if contacts["phones"]:
                contact_info.append(f"📞 Телефон: {', '.join(contacts['phones'])}")
            if contacts["messengers"]:
                contact_info.append(f"💬 Мессенджеры: {', '.join(contacts['messengers'])}")

            contact_str = " | ".join(contact_info) if contact_info else "⚠️ Контакты на сайте не найдены"
            details_str = f"⚠️ Обнаруженные изъяны:\n• " + "\n• ".join(issues)

            # Отправка лида в Telegram
            await send_lead(
                source="Deep Lead Hunter",
                title=url,
                details=f"{details_str}\n\n{contact_str}",
                link=url
            )
            print(f"[+] Найден и отправлен проблемный сайт: {url} (Проблем: {len(issues)})")

    except Exception as e:
        pass


async def run_site_analyzer():
    async with aiohttp.ClientSession() as session:
        while True:
            for query in TARGET_QUERIES:
                print(f"🔍 Сканирование по запросу: {query}...")
                sites = await search_sites_by_query(session, query)

                if sites:
                    print(f"[~] Найдено сайтов: {len(sites)}. Запускаем глубокий аудит...")
                    tasks = [check_site(session, site) for site in sites]
                    await asyncio.gather(*tasks)
                else:
                    print(f"[-] По запросу '{query}' ничего не найдено.")

                await asyncio.sleep(3)

            print("⏳ Круг сканирования завершен. Пауза 60 секунд...")
            await asyncio.sleep(60)