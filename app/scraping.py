import re
from string import printable
from time import strptime

import httpx
from bs4 import BeautifulSoup, Tag

BASE_URL = "http://scoresheet.ffhaltero.fr/scoresheet/"

months = {
    "Jan": "Jan",
    "Fév": "Feb",
    "Mar": "Mar",
    "Avr": "Apr",
    "Mai": "May",
    "Jui": "Jun",
    "Jul": "Jul",
    "Aoû": "Aug",
    "Sep": "Sep",
    "Oct": "Oct",
    "Nov": "Nov",
    "Déc": "Dec",
}

ASCII = set(printable)


def to_text(tag) -> str:
    if not isinstance(tag, Tag):
        return ""
    return tag.text.strip()


def to_date(text: str):
    groups = text.split(" ")[1:]
    groups[1] = months[groups[1]]
    return strptime(" ".join(groups), "%d %b %Y")


def to_float(tag) -> float:
    return float(to_text(tag).replace(",", "."))


async def scrap_sheets():
    link_regex = r"/scoresheet/(?:team/)?competition/view/(\d+)"

    async with httpx.AsyncClient() as client:
        res = await client.get(BASE_URL)
        soup = BeautifulSoup(res.content.decode("utf-8"), "html.parser")

        table = soup.find("table", {"id": "competitionSet"})
        if not isinstance(table, Tag):
            return {}

        tbody = table.findChild("tbody")
        if not isinstance(tbody, Tag):
            return {}

        data = {}
        for row in tbody.find_all("tr"):
            cells = row.find_all("td")

            link = cells[0].find("a")
            name = to_text(link)
            matches = re.search(link_regex, link["href"])

            if matches is None:
                continue

            gender = to_text(cells[2])
            if gender == "masculin":
                gender = "M"
            elif gender == "feminin":
                gender = "F"
            else:
                gender = "MF"

            id = int(matches.group(1))

            data[id] = {
                "name": name,
                "team": to_text(cells[3]) == "Equipes",
                "gender": gender,
                "open": to_text(cells[5]) == "Ouverte",
                "date": to_date(to_text(cells[4])),
                "serie": to_text(cells[6]),
                "region": to_text(cells[1]),
            }

        return data


async def scrap_sheet(id, team=False, closed=True):
    async with httpx.AsyncClient() as client:
        url = BASE_URL + ("team/" if team else "") + f"competition/view/{id}"
        res = await client.get(url)
        soup = BeautifulSoup(res.content.decode("utf-8"), "html.parser")

        tables = soup.find_all("table", class_="event-datatable")

        if not team and closed:
            return [scrap_individual_closed(table) for table in tables]
        elif not team and not closed:
            return [scrap_individual_open(table) for table in tables]
        elif team and closed:
            return [scrap_team_closed(table) for table in tables]
        else:
            return [scrap_team_open(table) for table in tables]


def scrap_individual_closed(table: Tag):
    tbody = table.find("tbody")
    if not isinstance(tbody, Tag):
        return None

    data = []
    for row in tbody.find_all("tr"):
        data.append(scrap_row(row))

    return data


def scrap_individual_open(table: Tag):
    data = []

    for tbody in table.find_all("tbody"):
        tr = tbody.find("tr")
        if isinstance(tr, Tag):
            data.append(scrap_row(tr))

    return data


def scrap_team_closed(table: Tag):
    data = []

    for row in table.find_all("tr"):
        td = row.find_all("td", recursive=False)
        tr = row.find_all("tr", recursive=False)

        if len(td) == 3:
            data.append(
                {
                    "team": to_text(td[0]),
                    "iwf_points": float(
                        "".join(filter(lambda x: x in ASCII, to_text(td[1])))
                        .split(" ")[-1]
                        .replace(",", ".")
                    ),
                    "athletes": [],
                }
            )
        elif len(tr):
            for sub_row in tr:
                data[-1]["athletes"].append(scrap_row(sub_row))

    return data


def scrap_team_open(table: Tag):
    data = []

    for row in table.find_all(["tbody", "tr"]):
        if row.name == "tbody":
            row = row.find("tr")

        if not isinstance(row, Tag):
            continue

        td = row.find_all("td", recursive=False)

        if len(td) == 5:
            data.append(
                {
                    "team": to_text(td[1]),
                    "iwf_points": float(
                        "".join(filter(lambda x: x in ASCII, to_text(td[3])))
                        .split(" ")[-1]
                        .replace(",", ".")
                    ),
                    "athletes": [],
                    "drawing_number": int(to_text(td[4]).split(" ")[-1]),
                }
            )
        elif len(td) > 5:
            data[-1]["athletes"].append(scrap_row(row))

    return data


def scrap_row(row):
    all_cells = row.find_all("td")
    cells = []

    for cell in all_cells:
        if to_text(cell):
            cells.append(cell)

    drawing_number = None if len(cells) <= 18 else int(to_text(cells[0]))
    if drawing_number is not None:
        cells = cells[1:]

    return {
        "drawing_number": drawing_number,
        "licence": int(to_text(cells[0])),
        "name": to_text(cells[1]),
        "year_of_birth": int(to_text(cells[2])),
        "club": to_text(cells[3]),
        "nationality": to_text(cells[4]),
        "body_weight": to_float(cells[5]),
        "snatch_attemps": [
            int(to_text(cells[6])),
            int(to_text(cells[7])),
            int(to_text(cells[8])),
        ],
        "snatch_result": int(to_text(cells[9])),
        "clean_and_jerk_attemps": [
            int(to_text(cells[10])),
            int(to_text(cells[11])),
            int(to_text(cells[12])),
        ],
        "clean_and_jerk_result": int(to_text(cells[13])),
        "total": int(to_text(cells[14])),
        "serie": to_text(cells[15]),
        "categorie": to_text(cells[16]),
        "iwf_points": to_float(cells[17]),
    }


if __name__ == "__main__":
    import asyncio
    import json

    # data = asyncio.run(scrap_sheets())
    data = asyncio.run(scrap_sheet(9175, closed=False, team=True))
    print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
