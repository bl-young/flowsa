# write_FIPS_from_Census.py (scripts)
# !/usr/bin/env python3
# coding=utf-8
# ingwersen.wesley@epa.gov


"""
Grabs FIPS codes from static URLs and creates crosswalk over the years.

- Shapes the set to include State and County names for all records.
- Writes reshaped file to datapath as csv.
"""

import pandas as pd
import io
from flowsa.common import datapath, clean_str_and_capitalize
from flowsa.datapull import make_http_request

def stripcounty(s):
    """
    Removes " County" from county name
    :param s: a string ending with " County"
    :return:
    """
    if s.__class__ == str:
        if s.endswith(" County"):
            s = s[0:len(s)-7]
    return s


def annual_fips(years):
    """Fxn to pull the FIPS codes/names from the Census website. Columns are renamed amd subset."""
    # list of years to include in FIPS crosswalk
    df_list = {}
    for year in years:
        # only works for 2015 +....contacted Census on 5/1 to ask for county level fips for previous years
        url = "https://www2.census.gov/programs-surveys/popest/geographies/" + year + "/all-geocodes-v" + year + ".xlsx"
        r = make_http_request(url)
        raw_df = pd.io.excel.read_excel(io.BytesIO(r.content)).dropna()

        # skip the first few rows
        FIPS_df = pd.DataFrame(raw_df.loc[4:]).reindex()
        # Assign the column titles
        FIPS_df.columns = raw_df.loc[3, ]

        original_cols = FIPS_df.columns

        # Create a dictionary of geographic levels
        geocode_levels = {"010": "Country",
                          "040": "State",
                          "050": "County_" + year}
        level_codes = geocode_levels.keys()
        # filter df for records with the levels of interest
        FIPS_df = FIPS_df[FIPS_df["Summary Level"].isin(level_codes)]

        # split df by level to return a list of dfs
        # use a list comprehension to split it out
        FIPS_bylevel = [pd.DataFrame(y) for x, y in FIPS_df.groupby("Summary Level", as_index=False)]

        # Assume df order in list is in geolevels keys order

        state_and_county_fields = {"Country": ["State Code (FIPS)"],  # country does not have its own field
                                   "State": ["State Code (FIPS)"],
                                   "County_" + year: ["State Code (FIPS)", "County Code (FIPS)"]}

        name_field = "Area Name (including legal/statistical area description)"

        new_dfs = {}
        for df in FIPS_bylevel:
            df = df.reset_index(drop=True)
            level = geocode_levels[df.loc[0, "Summary Level"]]
            new_df = df[original_cols]
            new_df = new_df.rename(columns={name_field: level})
            fields_to_keep = [str(x) for x in state_and_county_fields[level]]
            fields_to_keep.append(level)
            new_df = new_df[fields_to_keep]
            # Write each to the list
            new_dfs[level] = new_df

        # New merge the new dfs to add the info
        # FIPS_df_new = FIPS_df
        for k, v in new_dfs.items():
            fields_to_merge = [str(x) for x in state_and_county_fields[k]]
            # FIPS_df_new = pd.merge(FIPS_df_new,v,on=fields_to_merge,how="left")
            FIPS_df = pd.merge(FIPS_df, v, on=fields_to_merge, how="left")

        # combine state and county codes
        FIPS_df['FIPS_' + year] = FIPS_df[state_and_county_fields["County_" + year][0]] + FIPS_df[state_and_county_fields["County_" + year][1]]

        fields_to_keep = ["State", "County_" + year, "FIPS_" + year]
        FIPS_df = FIPS_df[fields_to_keep]

        # Clean the county field - remove the " County"
        # FIPS_df["County"] = FIPS_df["County"].apply(lambda x:stripcounty(x))
        FIPS_df["County_" + year] = FIPS_df["County_" + year].apply(stripcounty)
        FIPS_df["County_" + year] = FIPS_df["County_" + year].apply(clean_str_and_capitalize)
        FIPS_df["State"] = FIPS_df["State"].apply(clean_str_and_capitalize)

        # add to data dictionary of fips years
        df_list["FIPS_" + year] = FIPS_df
    return df_list


def annual_fips_name(df_fips_codes, years):
    """Add county names for years (if county names exist)"""
    df = df_fips_codes
    for year in years:
        df = pd.merge(df, fips_dic['FIPS_' + year], on='FIPS_' + year)
    return df

if __name__ == '__main__':

    # years data interested in (list)
    years = ['2015']

    # read in the fips data dictionary
    fips_dic = annual_fips(years)

    # map county changes, based on FIPS 2015 df, using info from Census website
    # https://www.census.gov/programs-surveys/geography/technical-documentation/county-changes.html
    # Accessed 04/10/2020
    df = fips_dic['FIPS_2015']

    #### modify columns depicting how counties have changed over the years - starting 2010
    # 2019 one FIPS code deleted and split into two FIPS
    df_19 = pd.DataFrame(df['FIPS_2015'])
    df_19['FIPS_2019'] = df_19['FIPS_2015']
    df_19.loc[df_19['FIPS_2019'] == "02261", 'FIPS_2019'] = "02063"
    df_19 = df_19.append(pd.DataFrame([["02261", "02066"]], columns=df_19.columns))

    # 2013 had two different/renamed fips
    df_13 = pd.DataFrame(df['FIPS_2015'])
    df_13['FIPS_2013'] = df_13['FIPS_2015']
    df_13.loc[df_13['FIPS_2013'] == "02158", 'FIPS_2013'] = "02270"
    df_13.loc[df_13['FIPS_2013'] == "46102", 'FIPS_2013'] = "46113"

    # # 2013 had a fips code that was merged with an existing fips, so 2010 will have an additional row
    df_10 = pd.DataFrame(df_13["FIPS_2013"])
    df_10['FIPS_2010'] = df_13['FIPS_2013']
    df_10 = df_10.append(pd.DataFrame([["51019", "51515"]], columns=df_10.columns))

    # merge 2013 with 2014 dataframe
    df2 = pd.merge(df_10, df_13, how="left", on="FIPS_2013")
    # merge 2019 with 2017
    df3 = pd.merge(df_19, df2, on="FIPS_2015")

    # fips years notes
    # 2010, 2011, 2012       have same fips codes
    # 2013, 2014             have same fips codes
    # 2015, 2016, 2017, 2018 have same fips codes
    # 2019                   have same fips codes
    # df3['FIPS_2010'] = df3['FIPS_2012']
    # df3['FIPS_2011'] = df3['FIPS_2012']
    # df3['FIPS_2013'] = df3['FIPS_2014']
    # df3['FIPS_2015'] = df3['FIPS_2017']
    # df3['FIPS_2016'] = df3['FIPS_2017']
    # df3['FIPS_2018'] = df3['FIPS_2017']

    # Use Census data to assign county names to FIPS years. Some county names have changed over the years,
    # while FIPS remain unchanged
    df4 = annual_fips_name(df3, years)

    # drop repeated State columns and rename
    # df5 = df4.drop(columns=['State_x'])
    df5 = df4.loc[:, ~df4.columns.duplicated()]
    # df5 = df5.rename(columns={"State_y": "State"})

    # reorder dataframe
    fips_xwalk = df5[['State', 'FIPS_2010', 'FIPS_2013', 'FIPS_2015', 'County_2015', 'FIPS_2019']]

    # write fips crosswalk as csv
    fips_xwalk.to_csv(datapath+"Crosswalk_FIPS.csv", index=False)


