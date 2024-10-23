from fastapi import FastAPI
from scraper import Scraper

api = FastAPI()
scraper = Scraper()
scraper.start()


@api.get("/api/sheets")
def get_sheets():
    sheets = scraper.get_sheets()

    for k in sheets.keys():
        del sheets[k]["sheet"]

    return sheets


@api.get("/api/sheet/{id}")
def get_sheet(id: int):
    return scraper.get_sheet(id)


if __name__ == "__main__":
    import uvicorn

    scraper.start()
    uvicorn.run(api, port=8080)
