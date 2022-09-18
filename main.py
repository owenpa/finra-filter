import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import re
import pandas as pd
import datetime
import PySimpleGUI as sg

pd.options.mode.chained_assignment = None


def sortFile(raw):
    sorted_df = raw.dropna()
    sorted_df.drop("Date", axis="columns", inplace=True)
    sorted_df.columns = ["Sym", "SVol", "SXVol", "TVol", "Mrkt"]
    for row in sorted_df.itertuples(index=True, name="Model"):
        percent = (row[2] / row[4]) * 100
        if not (65 >= percent >= 40 and row[2] > 100 and row[4] > 10000 and (row[3] / row[2]) * 100 >= 1):
            # remove the stock from the list if the following requirements aren't met:
            #  - short volume is within 40%-65% of the total volume
            #  - short exempt volume is more than 100
            #  - total volume exceeds 10,000
            sorted_df.drop(row[0], inplace=True)
    sorted_df.sort_values("TVol", ascending=False, inplace=True)

    return sorted_df


def createFile(urls):
    for link in urls:
        date = re.search("\d+", link)
        req = Request(url=link, headers={'User-Agent': 'XYZ/3.0'})
        page = urlopen(req, timeout=10).read()
        webpage = BeautifulSoup(page, "html.parser")
        with open("finra/{}.txt".format(date.group()), "w") as file:
            file.write(str(webpage))
        df = pd.read_csv("finra/{}.txt".format(date.group()), delimiter="|")
        new_df = sortFile(df)
        new_df.to_csv("finra/{}.csv".format(date.group()), index=None)

    files = sorted(Path("finra/").glob("[0-9]*"))
    if len(files) >= 8:
        try:
            os.remove(files[0])
            os.remove(files[0])
        except FileNotFoundError:
            pass
    if len(files) >= 4:
        text = re.findall("\d+\.csv", files.__str__())
        return text[1], text[0]


def createWindow(date, yesterday):
    sg.theme("Dark Grey 14")

    df = pd.read_csv("finra/{}".format(date), delimiter=',')
    df2 = pd.read_csv("finra/{}".format(yesterday))
    csv = [list(row) for row in df.values]
    csv.insert(0, df.columns.to_list())
    layout = [
        [sg.Input(key="_input_"),
         sg.Button(button_text="search", enable_events=True, size=(5, 1))],
        [sg.Text(text="",
                 enable_events=True,
                 key="_output_")],
        [sg.Table
         (csv[1:],
          headings=["Sym", "SVol", "SXVol", "TVol", "Mrkt"],
          selected_row_colors=("white", "gray"),
          expand_y=True,
          enable_events=True,
          right_click_selects=True,
          key="_table_")
         ],
        [sg.Text(text="Total filtered stocks: " + str(len(df))),
         sg.Text(text="Previous days filtered stocks: " + str(len(df2)))]
    ]
    window = sg.Window("CSV Viewer", layout, size=(500, 300), resizable=True, element_justification="center")
    while True:
        event, values = window.read()

        if event == "search" and values["_input_"] != "":
            query = values["_input_"].upper()
            if query in df["Sym"].values:
                window.Element("_output_").update(df.loc[df["Sym"] == query])
                window.Element("search").update("search")
            else:
                window.Element("search").update("N/A")
        elif event == sg.WIN_CLOSED:
            break


def exampleOne():
    url = "https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data/daily-short-sale-volume-files"
    htmlpage = urlopen(url)
    htmltext = htmlpage.read().decode("utf-8")
    soup = BeautifulSoup(htmltext, "html.parser")
    returnvalues = []
    for text in soup.findAll('a', attrs={'href': re.compile("^https:\/.+txt")}):
        if len(returnvalues) != 2:
            link = text.get('href')
            returnvalues.append(link)
    return createFile(returnvalues)


def exampleTwo():
    # skip all the fancy link scraping and "bruteforce"
    # the problem with using this method is that it requires a LOT more lines of code
    # and doesn't automatically skip "over stock market holidays"
    # if today is saturday/sunday or monday, and monday's info isn't available, then return friday's/thursday's info
    # otherwise return monday's and friday's information
    # otherwise return today and yesterday's information
    date = datetime.datetime.now()
    match date.weekday():
        case 0:  # Monday
            try:
                yesterday = date.replace(day=date.day - 3)  # Friday
                returnvalues = ["https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt".format
                                (date.strftime("%Y%m%d")),
                                "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt".format
                                (yesterday.strftime("%Y%m%d"))
                                ]
                return createFile(returnvalues)
            except HTTPError:
                friday = date.replace(day=date.day - 3)
                thursday = date.replace(day=date.day - 4)
                print("Could not reach Monday's data.\nFriday's and Thursday's data:\n")
                returnvalues = ["https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt".format
                                (friday.strftime("%Y%m%d")),
                                "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt".format
                                (thursday.strftime("%Y%m%d"))
                                ]
                return createFile(returnvalues)
        case 5:  # Saturday
            friday = date.replace(day=date.day - 1)
            thursday = date.replace(day=date.day - 2)
            print("Friday's and Thursday's data:\n")
            returnvalues = ["https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt".format
                            (friday.strftime("%Y%m%d")),
                            "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt".format
                            (thursday.strftime("%Y%m%d"))
                            ]
            return createFile(returnvalues)
        case 6:  # Sunday
            friday = date.replace(day=date.day - 2)
            thursday = date.replace(day=date.day - 3)
            print("Friday's and Thursday's data:\n")
            returnvalues = ["https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt".format
                            (friday.strftime("%Y%m%d")),
                            "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt".format
                            (thursday.strftime("%Y%m%d"))
                            ]
            return createFile(returnvalues)
        case _:
            try:
                yesterday = date.replace(day=date.day - 1)
                returnvalues = ["https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt".format
                                (date.strftime("%Y%m%d")),
                                "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt".format
                                (yesterday.strftime("%Y%m%d"))
                                ]
                return createFile(returnvalues)
            except HTTPError:
                print("Could not find either today's or yesterday's information.")


if __name__ == '__main__':
    try:
        os.mkdir("finra")
    except FileExistsError:
        pass

    today, yesterday = exampleOne()
    createWindow(today, yesterday)
