# USGS_WU_Coef.py (flowsa)
# !/usr/bin/env python3
# coding=utf-8

"""
This script is run on it's own, not through datapull.py, as data pulled from csv in flowsa.

NOAA fisheries data obtained from: USGS Publication (Lovelace, 2005)

Data output saved as csv, retaining assigned file name "USGS_WU_Coef_Raw.csv"
"""

from flowsa.common import *
import pandas as pd
from flowsa.datapull import store_flowbyactivity
from flowsa.flowbyfunctions import add_missing_flow_by_fields


# 2012--2018 fisheries data at state level
csv_load = datapath + "USGS_WU_Coef_Raw.csv"


if __name__ == '__main__':
    # Read directly into a pandas df
    df_raw = pd.read_csv(csv_load)

    # read county fips from common.py
    # df_state = get_state_FIPS()
    # df_state['State'] = df_state["State"].str.lower()

    # new column includes state fips
    # df3 = df2.merge(df_state[["State", "FIPS"]], how="left", left_on="State", right_on="State")

    # rename columns to match flowbyactivity format
    df = df_raw.copy()
    df = df.rename(columns={"Animal Type": "ActivityConsumedBy",
                            "WUC_Median": "FlowAmount",
                            "WUC_Minimum": "Min",
                            "WUC_Maximum": "Max"
                            })

    # drop columns
    df = df.drop(columns=["WUC_25th_Percentile", "WUC_75th_Percentile"])

    # hardcode data
    df["Class"] = "Water"
    df["SourceName"] = "USGS_WU_Coef"
    df["Location"] = US_FIPS
    df['LocationSystem'] = "FIPS_2015"  # state FIPS codes have not changed over last decade
    df['Year'] = 2005
    df["Unit"] = "gallons/animal/day"

    # add missing dataframe fields (also converts columns to desired datatype)
    flow_df = add_missing_flow_by_fields(df, flow_by_activity_fields)
    parquet_name = 'USGS_WU_Coef_2005'
    store_flowbyactivity(flow_df, parquet_name)
