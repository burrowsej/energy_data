from os import listdir
from types import SimpleNamespace
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
import numpy as np
from textwrap import TextWrapper

SETTINGS = SimpleNamespace(
    RAW_DATA_PATH="data_raw",
)

files = listdir(SETTINGS.RAW_DATA_PATH)

df = pd.DataFrame()
for f in files:

    if not (f.startswith("DemandData_") | f.startswith("Demand_Data")):
        continue

    print(f)
    df_year = pd.read_csv(
        f"{SETTINGS.RAW_DATA_PATH}/{f}",
        parse_dates=["SETTLEMENT_DATE"],
        dayfirst=True,
    )

    df = pd.concat([df, df_year])


# add settlement period start times from the 30-min settlement periods
df.SETTLEMENT_DATE = df.apply(
    lambda x: x.SETTLEMENT_DATE + pd.Timedelta((x.SETTLEMENT_PERIOD - 1) / 2, "h"),
    axis=1,
)
df.drop(columns="SETTLEMENT_PERIOD", inplace=True)
df.set_index("SETTLEMENT_DATE", inplace=True)
df.sort_index(inplace=True)


################################ Plotting

sns.set_style("whitegrid")
sns.despine(offset=0, trim=True)
wrapper = TextWrapper(width=145, break_long_words=False)


########### Demand

title = """
National Demand is calculated as a sum of generation based on National Grid 
operational generation metering. 

This is the Great Britain generation requirement and is equivalent to the 
Initial National Demand Outturn (INDO) and National Demand Forecast as 
published on BM Reports. National Demand is the sum of metered generation, but 
excludes generation required to meet station load, pump storage pumping and 
interconnector exports.
""".replace(
    "\n", ""
)
title = "\n".join(wrapper.wrap(title))

fig, ax = plt.subplots(figsize=(14, 6))

ax.plot(
    df.ND,
    alpha=0.2,
    color="black",
    label="Settlement period (30min) average",
)

ax.plot(
    df.ND.rolling(48 * 28, center=True, closed="both").mean(),
    alpha=1,
    color="#003763",
    ls="--",
    label="28-day rolling average",
)

ax.plot(
    df.ND.rolling(48 * 365, center=True, closed="both").mean(),
    alpha=1,
    color="#ff3902",
    label="1-year rolling average",
)

ax.set_xlabel("")
ax.set_ylabel("National Energy Demand (MW)")
ax.set_title(title, loc="left")
ax.margins(x=0)
ax.legend()
fig.tight_layout()
fig.show()


##### diurnal

df["month"] = df.index.month

seasons = {
    1: "Winter",
    2: "Winter",
    3: "Spring",
    4: "Spring",
    5: "Spring",
    6: "Summer",
    7: "Summer",
    8: "Summer",
    9: "Autumn",
    10: "Autumn",
    11: "Autumn",
    12: "Winter",
}
df["year"] = df.index.year
df["season"] = df.month.map(seasons).astype("category")
df["hour"] = df.index.hour + df.index.minute / 60


diurnal = df.groupby(["year", "season", "hour"]).ND.agg(["min", "mean", "max"])
diurnal = diurnal / 1000  # GW
diurnal.reset_index(inplace=True)
diurnal.set_index("hour", inplace=True)
# plt.style.use('ggplot')

fig, axes = plt.subplots(figsize=(12, 6), ncols=4, sharey=True, sharex=True)

for i, year in enumerate([2005, 2010, 2015, 2020]):

    df_year = diurnal.loc[diurnal.year == year]

    seasons = dict(
        Winter="#00B9E3", Spring="#7CAE00", Summer="#FF61C9", Autumn="#ED8141"
    )

    for j, season in enumerate(seasons):
        df_season = df_year.loc[df_year.season == season]
        axes[i].plot(
            df_season["mean"],
            color=seasons[season],
            label=season,
        )
        axes[i].fill_between(
            df_season.index,
            df_season["min"],
            df_season["max"],
            alpha=0.1,
            color=seasons[season],
        )
    axes[i].legend()
    axes[i].margins(x=0)
    axes[i].yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    axes[i].set_title(year)
    axes[i].set_xlabel("Hour of day")
    axes[i].set_xticks(np.arange(0, 24, 2))
    axes[i].set_yticks(np.arange(20, 65, 5))
    axes[i].xaxis.grid(False)


axes[0].set_ylabel("UK national energy demand (GW)")
fig.tight_layout(w_pad=0.1)
axes[0].text(
    0,
    9,
    "Source: National Grid demand data, accessed 03/11/2021. Shaded areas display min and max for the season and hour.",
    alpha=0.5,
)
plt.show()

# TODO: should vary more - check this!
########### Import/Export

title = f"""
The flow on the interconnectors (French, BritNed, Moyle, East-West). -ve 
signifies export power out from GB; +ve signifies import power into GB. Mean 
flow is {df[connectors].sum(axis=1).mean():,.0f}MW into GB.
""".replace(
    "\n", ""
)
title = "\n".join(wrapper.wrap(title))

connectors = ["FRENCH_FLOW", "BRITNED_FLOW", "MOYLE_FLOW", "EAST_WEST_FLOW"]

fig, ax = plt.subplots(figsize=(14, 6))

ax.plot(
    df[connectors].sum(axis=1),
    alpha=0.2,
    color="black",
    label="Settlement period (30min) average",
)

ax.plot(
    df[connectors].sum(axis=1).resample("MS", loffset=pd.Timedelta(15, "days")).mean(),
    alpha=1,
    ls="--",
    color="#003763",
    label="Monthly average",
)

ax.plot(
    df[connectors].sum(axis=1).resample("YS", loffset=pd.Timedelta(183, "days")).mean(),
    alpha=1,
    color="#ff3902",
    label="Annual average",
)

ax.set_xlabel("")
ax.set_ylabel("Interconnector Flow (MW)")
ax.set_title(title, loc="left")
ax.margins(x=0)
ax.legend()
fig.tight_layout()
plt.show()
