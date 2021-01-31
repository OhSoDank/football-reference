from bs4 import BeautifulSoup
import os
import pandas as pd
import numpy as np
import regex as re
import requests
import time


def extract_pick(row):
    """
    Extract the pick value from the football reference string representation.
    :param row:
        The pandas row to process. Must have a "Drafted (tm/rnd/yr)" value.
    :return:
        The overall numeric value of the pick, or np.NaN if not found.
    """

    match = re.search(r"(\d*)\w{2} pick", str(row["Drafted (tm/rnd/yr)"]))
    if match:
        return int(match.group(1))
    return np.NaN


def get_height(row):
    """
    Extract the height from the football reference string representation.
    :param row:
        The pandas row to process. Must have a "Ht" value.
    :return:
        The height in cm, or np.NaN if not found.
    """
    match = re.search(r"(\d)-(\d){1,2}", str(row["Ht"]))
    if match:
        inches = int(match.group(2)) + 12 * int(match.group(1))
        return inches * 2.54
    return np.NaN


def add_av(row, url_mapping):
    """
    Extract the sum of the AV accumulated by the given player in their first 5 years.
    :param row:
        The pandas row to process. Must have a "Player" value.
    :param url_mapping:
        A dict mapping player name to pro-football-reference URL extension.
    :return:
        The sum of AV accumulated by the player in their first 5 years in the NFL, or NaN
        if unable to calculate.
    """
    try:
        url = f"https://www.pro-football-reference.com{url_mapping[row['Player']]}"
    except:
        return np.NaN
    try:
        df = pd.read_html(url)[1]
        av = df.iloc[:5, df.columns.get_indexer(["AV"])].sum()
        print(row["Player"])
        return int(av)
    except:
        try:
            df = pd.read_html(url)[0]
            av = df.iloc[:5, df.columns.get_indexer(["AV"])].sum()
            print(row["Player"])
            return int(av)
        except:
            return np.NaN


def scrape_data():
    """
    Scrape pro-football-reference for NFL combine data from the years 2000 to 2016.
    :return:
        An unprocessed pandas dataframe with combine data for each player, and the sum of their
        AV in their first 5 years.
    """
    global dir_path
    ret = pd.DataFrame()
    for year in range(2000, 2017):
        start_time = time.time()
        url = f"https://www.pro-football-reference.com/draft/{year}-combine.htm"
        r = requests.get(url)
        soup = BeautifulSoup(r.content, "html.parser")
        parsed_table = soup.find_all("table")[0]
        df = pd.read_html(url)[0]
        url_mapping = dict()
        # Parse the BeautifulSoup data to construct a mapping of player name to
        # pro-football-reference URL extension.
        for i, row in enumerate(parsed_table.find_all("tr")[0:]):
            dat = row.find("th", attrs={"data-stat": "player"})
            try:
                name = dat.a.get_text()
                stub = dat.a.get("href")
                url_mapping[name] = stub
            except:
                pass
        # Add a column for the first 5 year AV accumulated by the player.
        df["5AV"] = df.apply(lambda row: add_av(row, url_mapping), axis="columns")
        ret = ret.append(df)
        print(f"------{year} done------")
        print(f"Took {time.time() - start_time}s")
        df.to_csv(os.path.join(dir_path, "data", f"{year}.csv"))
    return ret


def process_main_df(df):
    """
    Process the dataframe, converting the column values into useable values.
    :param df:
        The datagrame to process.
    :return:
        The same dataframe, but will all numeric values as floats, all rows with NaNs removed,
        and unnecessary columns removed.
    """
    df["Pick"] = df.apply(lambda row: extract_pick(row), axis="columns")
    df["Height (cm)"] = df.apply(lambda row: get_height(row), axis="columns")
    df = df.drop(
        labels=["School", "College", "Drafted (tm/rnd/yr)", "Ht", "Bench"],
        axis="columns",
    )
    df = df.dropna()
    for col in ["Wt", "40yd", "Vertical", "Broad Jump", "3Cone", "Shuttle"]:
        df[col] = df[col].astype(float)
    return df


def segment(df):
    """
    Segment the supplied dataframe into different positions.
    :param df:
        The dataframe to segment.
    :return:
        A dictionary keyed by position, with each value being the dataframe corresponding to
        that position.

        The keys are {"RB", "TE", "WR", "OL", "S", "CB", "LB", "Edge", "DL"}
    """
    ret = dict()
    ret["RB"] = df[df["Pos"] == "RB"]
    ret["TE"] = df[df["Pos"] == "TE"]
    ret["WR"] = df[df["Pos"] == "WR"]
    ret["OL"] = df[(df["Pos"] == "C") | (df["Pos"] == "OG") | (df["Pos"] == "OT")]
    ret["S"] = df[df["Pos"] == "S"]
    ret["CB"] = df[df["Pos"] == "CB"]
    ret["LB"] = df[(df["Pos"] == "ILB") | ((df["Pos"] == "OLB") & (df["Wt"] < 247))]
    ret["Edge"] = df[
        ((df["Pos"] == "OLB") & (df["Wt"] >= 247))
        | ((df["Pos"] == "DE") & (df["Wt"] < 277))
    ]
    ret["DL"] = df[(df["Pos"] == "DT") | ((df["Pos"] == "DE") & (df["Wt"] >= 277))]
    return ret


pd.set_option("display.max_columns", None)
dir_path = os.path.dirname(os.path.realpath(__file__))
main = scrape_data()
main = process_main_df(main)
df_dict = segment(main)
for pos in df_dict:
    print(df_dict[pos])
    df_dict[pos].to_csv(os.path.join(dir_path, "data", f"{pos}.csv"))
