from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import re
import pandas as pd
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


if __name__ == '__main__':
    url = "https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data/daily-short-sale-volume-files"
    htmlpage = urlopen(url)
    htmltext = htmlpage.read().decode("utf-8")
    soup = BeautifulSoup(htmltext, "html.parser")
    for text in soup.findAll('a', attrs={'href': re.compile("^https://")}):
        link = text.get('href')
        if "txt" in link:
            req = Request(url=link, headers={'User-Agent': 'XYZ/3.0'})
            page = urlopen(req, timeout=10).read()
            webpage = BeautifulSoup(page, "html.parser")
            with open("raw.txt", "w") as file:
                file.write(str(webpage))
            df = pd.read_csv("raw.txt", delimiter="|")
            new_df = sortFile(df)
            new_df.to_csv("fin.csv", index=None)
            new_df.to_excel("fin.xlsx", sheet_name="FINRA SHORT DATA")
            break
