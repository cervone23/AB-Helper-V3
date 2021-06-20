"""
## App: URL Helper App with Streamlit
Author: Brandon Cervone 
Source: [Github](https://github.com/cervone23/news-url-testing-app)

Description:
This program is designed to help the AB team gather article information from URL links using Google RSS feed. 

** Program ONLY collects National and Online Media Coverage ** 

Purpose:
Allow users to paste a URL address to find title, media source, and publishing date for any news publication. 
New additions include SimilarWeb API to get impressions data. 

"""
# Core Pkgs
import streamlit as st 
import pandas as pd

import feedparser
import urllib
import json
import csv
from datetime import datetime
from tldextract import extract
import requests

import base64
import yaml
import os

import errors
import config

from PIL import Image

####################################################################
### Download URL Function ### 
####################################################################

def download_link(object_to_download, download_filename, download_link_text):
    """
    Generates a link to download the given object_to_download.
    object_to_download (str, pd.DataFrame):  The object to be downloaded.
    download_filename (str): filename and extension of file. e.g. mydata.csv, some_txt_output.txt
    download_link_text (str): Text to display for download link.
    Examples:
    download_link(YOUR_DF, 'YOUR_DF.csv', 'Click here to download data!')
    download_link(YOUR_STRING, 'YOUR_STRING.txt', 'Click here to download your text!')
    """
    if isinstance(object_to_download, pd.DataFrame):
        object_to_download = object_to_download.to_csv(index=False)

    # some strings <-> bytes conversions necessary here
    b64 = base64.b64encode(object_to_download.encode()).decode()

    return f'<a href="data:file/txt;base64,{b64}" download="{download_filename}">{download_link_text}</a>'

@errors.exception_handler
def main():
    """ URL Parse API APP with Streamlit """

    # Title
    st.title("Article Clipper Helper")
    
    # display image
    image = Image.open("ab_ws_logo.png")
    st.image(image, use_column_width=True)
    
    st.subheader("Paste URL(s) Here:")

    ####################################################################
    ### User Input Fields ###
    ####################################################################

    # User input -- User pastes all links here 
    user_url = st.text_input("Paste Link(s) Here:","")

    # Convert user input urls to str type
    urls = str(user_url)

    ####################################################################
    ### Extract URL Article Info from Google RSS Feed ### 
    ####################################################################

    # Create a submission button to parse URL information 
    if st.button("Get URL Info"):
 
        new_urls = []

        # Separate user input URLs 
        splited = urls.split("http")
        for each in splited:
            if "://" in each:
                new_urls.append("http" + each.strip())

        data = []
        # Output column names 
        columns = ['Article Title', 'Date', 'Outlet Name', 'Link']
        for s in new_urls:
            # Insert urls into google news url & query RSS feed
            url = "https://news.google.com/rss/search?q=" + s  

            d = feedparser.parse(url)
            if len(d['entries']) == 0:
                data.append(['NaN', 'NaN', 'NaN', s])
            try:
                for i, entry in enumerate(d.entries, 1):
                    p = entry.published_parsed
                    sortkey = "%04d%02d%02d%02d%02d%02d" % (p.tm_year, p.tm_mon, p.tm_mday, p.tm_hour, p.tm_min, p.tm_sec)
                    datetime_obj = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %Z")
                    tmp = {
                        "no" : i,
                        "title" : entry.title,
                        "summery" : entry.summary,
                        "link" : entry.link,
                        "published" : entry.published,
                        "sortkey" : sortkey,
                        "source": entry.source
                    }
                    if tmp['link'] == s:
                        src_ttl = tmp['source']['title'].split(".")[0].strip()
                        data.append([tmp['title'], datetime_obj.strftime("%m/%d/%y"), src_ttl, tmp['link']])
            except:
                print(f"No data returned for {s}")

        # Google RSS Feed Data
        df = pd.DataFrame(data=data, columns=columns)

        # Add Additional Media Tracking Columns 
        df['Market'] = 'National'
        df['Media Type'] = 'Online'
    
        ####################################################################
        ### Similar Web Data Extraction ### 
        #################################################################### 

        # Automatically update the date to use with API 
        lastmonth = int(pd.to_datetime("today").strftime("%Y%m"))-2
        lm = str(lastmonth)
        last_month = lm[:4] + '-' + lm[4:]

        # Create a list of domains 
        mass_urls = df['Link'].tolist()

        # Get Raw Domains 
        domains = []
        for x in mass_urls:
            tsd, td, tsu = extract(x) 

            url = td + '.' + tsu
            domains.append(url)

        df['Outlet Domain'] = domains

        # Similar Web API Creds
        payload = {'api_key': st.secrets['api_key'], 
                'start_date': last_month, 
                'end_date': last_month, 
                'country': 'US', 
                'granularity': 'monthly', 
                'main_domain_only': 'False', 
                'format': 'json'}

        sw_data = []
        # Output column names 
        sw_columns = ['Outlet Domain','Outlet Reach (Monthly)']
        
        data_list = []

        for visit in domains:

            url= 'https://api.similarweb.com/v1/website/{}/total-traffic-and-engagement/visits'.format(visit)

            r=requests.get(url,params=payload)
            sw_data = r.json()
            
            url_info = sw_data['meta']['request']['domain']

            visit_info = sw_data['visits'][0]['visits']
            #visit_info = my_value(round(visit_info,2))

            data_list.append([url_info, visit_info])

        sw_df = pd.DataFrame(data=data_list, columns=sw_columns)

        sw_df['Outlet Reach (Monthly)'] = pd.to_numeric(sw_df['Outlet Reach (Monthly)'], errors='coerce')
        sw_df['Outlet Reach (Weekly)'] = sw_df['Outlet Reach (Monthly)'] /4
        
        # ####################################################################
        # ### Merge Google RSS DF & Similar Web DF ### 
        # #################################################################### 

        # config path
        cfg_path = "config.yaml"
        cfg = yaml.safe_load(open(cfg_path))

        # create temp df
        tmp_df = pd.DataFrame(columns=[*range(42)])
        tmp_df = tmp_df.rename(columns=cfg["tracker_cols"])

        new_df = tmp_df.append(df)
        new_df[['Outlet Reach (Weekly)','Outlet Reach (Monthly)']] = new_df[['Outlet Reach (Weekly)','Outlet Reach (Monthly)']].apply(pd.to_numeric)

        output_df_one = pd.merge(df, sw_df, on="Outlet Domain", how="left")
        output_df = pd.concat([tmp_df, output_df_one])

        del output_df['Outlet Domain']

        st.dataframe(output_df)

        # write to file for download in Tracker Format
        tmp_download_link = download_link(
            output_df,
            "output.csv",
            "Click here to download in Tracker Format!",
        )
        st.markdown(tmp_download_link, unsafe_allow_html=True)

if __name__ == '__main__':
    main()
    
    
