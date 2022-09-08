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
        if not(65 >= percent >= 40 and row[2] > 100 and row[4] > 10000 and (row[3] / row[2]) * 100 >= 1):
            # remove the stock from the list if the following requirements aren't met:
            #  - short volume is within 40%-65% of the total volume
            #  - short exempt volume is more than 100
            #  - total volume exceeds 10,000
            sorted_df.drop(row[0], inplace=True)
    sorted_df.sort_values("TVol", ascending=False, inplace=True)
    print(sorted_df)
    return sorted_df


def createFile(url):
    req = Request(url=url, headers={'User-Agent': 'XYZ/3.0'})
    page = urlopen(req, timeout=10).read()
    webpage = BeautifulSoup(page, "html.parser")
    with open("raw.txt", "w") as file:
        file.write(str(webpage))
    df = pd.read_csv("raw.txt", delimiter="|")
    new_df = sortFile(df)
    new_df.to_csv("fin.csv", index=None)
    new_df.to_excel("fin.xlsx", sheet_name="Seet")


def createWindow():
    df = pd.read_csv('fin.csv', delimiter=',')
    csv = [list(row) for row in df.values]
    csv.insert(0, df.columns.to_list())
    layout = [
        [sg.Table
         (csv,
          headings=["Sym", "SVol", "SXVol", "TVol", "Mrkt"],
          selected_row_colors=("white", "gray"),
          expand_y=True,
          enable_events=True,
          right_click_selects=True)
         ]
    ]

    window = sg.Window("CSV Viewer", layout, size=(500, 300))
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break


def exampleOne():
    url = "https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data/daily-short-sale-volume-files"
    htmlpage = urlopen(url)
    htmltext = htmlpage.read().decode("utf-8")
    soup = BeautifulSoup(htmltext, "html.parser")
    for text in soup.findAll('a', attrs={'href': re.compile("^https://")}):
        link = text.get('href')
        if "txt" in link:
            createFile(link)
            break


def exampleTwo():
    # skip all the fancy link scraping and "bruteforce"
    # if today is saturday, sunday, or monday, and monday's info isn't available, then return friday's information
    # otherwise return today's information (only available after market close)
    # otherwise return yesterday's information
    date = datetime.datetime.now()
    match date.weekday():
        case 0:  # Monday
            try:
                createFile("https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt"
                           .format(date.strftime("%Y%m%d")))
            except HTTPError:
                new_date = date.replace(day=date.day - 3)
                print("Could not reach Monday's data.\nFriday's data:\n")
                createFile("https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt"
                           .format(new_date.strftime("%Y%m%d")))
        case 5:  # Saturday
            new_date = date.replace(day=date.day - 1)
            createFile("https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt"
                       .format(new_date.strftime("%Y%m%d")))
        case 6:  # Sunday
            new_date = date.replace(day=date.day - 2)
            createFile("https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt"
                       .format(new_date.strftime("%Y%m%d")))
        case default:
            try:
                createFile("https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt".format(date.strftime("%Y%m%d")))
            except HTTPError:
                new_date = date.replace(day=date.day - 1)
                print("Could not reach today's data.\nPrevious day's data:\n")
                createFile("https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt"
                           .format(new_date.strftime("%Y%m%d")))


if __name__ == '__main__':
    exampleOne()
    createWindow()
