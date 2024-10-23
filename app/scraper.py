import threading
from asyncio import gather, new_event_loop, run, run_coroutine_threadsafe
from copy import deepcopy
from datetime import datetime
from time import sleep

from scraping import scrap_sheet, scrap_sheets


async def _try_scrap_sheet(id, team=False, open=False):
    try:
        return id, await scrap_sheet(id, team=team, closed=not open)
    except Exception:
        return id, None


class Scraper:
    def __init__(self):
        self._sheets = {}
        self._scraper_thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._loop = new_event_loop()

    def _scrap(self):
        run(self._update_all())

        counter = 0
        while not self._stop_event.is_set():
            if counter >= 100:
                run_coroutine_threadsafe(self._update_sheets(), self._loop)
                counter = 0

            run(self._update_open_sheets())
            counter += 1
            sleep(1)

    async def _update_open_sheets(self):
        sheets = {}
        with self._lock:
            sheets = deepcopy(self._sheets)

        pending = []
        for k, v in sheets.items():
            if not v["open"]:
                continue
            pending.append(_try_scrap_sheet(k, team=v["team"], open=True))

        for id, sheet in await gather(*pending):
            sheets[id]["sheet"] = sheet
            sheets[id]["updated_at"] = datetime.now()

        with self._lock:
            self._sheets |= sheets

    async def _update_sheets(self):
        sheets = await scrap_sheets()

        with self._lock:
            self._sheets |= sheets

    async def _update_all(self):
        sheets = await scrap_sheets()

        pending = []
        for k, v in sheets.items():
            pending.append(_try_scrap_sheet(k, team=v["team"], open=v["open"]))

        for id, sheet in await gather(*pending):
            sheets[id]["sheet"] = sheet
            sheets[id]["updated_at"] = datetime.now()

        with self._lock:
            self._sheets |= sheets

    def start(self):
        if not self._scraper_thread or not self._scraper_thread.is_alive():
            self._stop_event.clear()
            self._scraper_thread = threading.Thread(target=self._scrap)
            self._scraper_thread.daemon = True
            self._scraper_thread.start()

    def stop(self):
        if self._scraper_thread and self._scraper_thread.is_alive():
            self._stop_event.set()
            self._scraper_thread.join()
            self._loop.call_soon_threadsafe(self._loop.stop)

    def get_sheets(self):
        with self._lock:
            return deepcopy(self._sheets)

    def get_sheet(self, id):
        with self._lock:
            return deepcopy(self._sheets.get(id))


if __name__ == "__main__":
    import json

    scraper = Scraper()
    scraper.start()

    sleep(10)
    sheets = scraper.get_sheets()
    scraper.stop()

    data = json.dumps(
        sheets[9260],
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )

    print(data)
