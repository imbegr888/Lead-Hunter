import sys
import os

# Принудительно прописываем абсолютный путь к корню проекта в Python Path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio
import logging
from modules.site_analyzer import run_site_analyzer
from modules.job_parser import run_job_parser

async def periodic_scanner():
    """Периодический запуск сайтов и вакансий раз в 30 минут"""
    while True:
        logging.info("🔄 Запуск планового сканирования сайтов и вакансий...")
        await run_site_analyzer()
        await run_job_parser()
        logging.info("💤 Сканирование завершено. Ожидание 30 минут...")
        await asyncio.sleep(1800) # 30 минут

async def main():
    logging.info("🚀 Lead Hunter запущен (режим сканирования сайтов и вакансий)!")
    # Запускаем только фоновый сканер
    await periodic_scanner()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 Программа остановлена пользователем.")