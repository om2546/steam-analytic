import requests
import random
import re
import pandas as pd
import numpy as np
import time
import os
import sys
from datetime import datetime

PATH = os.path.dirname(__file__)
STEAM_CSV = PATH + '/steam.csv'
ERROR_LIST_CSV = PATH + '/error_list.csv'
LOG_CSV = PATH + '/log.csv'

DATETIME_READ = None
DATETIME_SLEEP = None
REASON = None
def get_all_app_id():
    # get all app id
    req = requests.get("https://api.steampowered.com/ISteamApps/GetAppList/v2/")

    if (req.status_code != 200):
        print("Failed to get all games on steam.")
        return
    
    try:
        data = req.json()
    except Exception as e:
        print(e)
        return
    
    apps_data = data['applist']['apps']

    apps_ids = []

    for app in apps_data:
        appid = app['appid']
        name = app['name']
        
        # skip apps that have empty name
        if not name:
            continue
        apps_ids.append(appid)
    return apps_ids

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    # remove multiple spaces
    cleantext = re.sub('\s+', ' ', cleantext)
    return cleantext

def error_list_concat(app_id,code):
    df = pd.read_csv(ERROR_LIST_CSV)
    print('error func',app_id,code)

    temp = pd.DataFrame(data=[[app_id, code]], columns=['app_id', 'error_code'])
    temp = temp.astype({'app_id': int, 'error_code': str})
    df = pd.concat([df, temp], ignore_index=True)
    df.to_csv(ERROR_LIST_CSV, index=False)
    return None

def update_log(time,length,status):
    df = pd.read_csv(LOG_CSV)
    temp = pd.DataFrame(data=[[time, length,status]], columns=['time','lenght','status'])
    df = pd.concat([df, temp], ignore_index=True)
    df.to_csv(LOG_CSV, index=False)
    return None

def get_app_details(app_id):
    global DATETIME_READ
    global DATETIME_SLEEP
    global REASON
    url = "http://store.steampowered.com/api/appdetails/"
    params = {
        "appids": app_id
    }
    req = requests.get(url, params=params)

    if (req.status_code == 429):
        datetime_now = datetime.now()
        if DATETIME_READ != None:
            update_log(datetime_now,datetime_now-DATETIME_READ,'read')
            DATETIME_READ = None
        if DATETIME_SLEEP == None:
            DATETIME_SLEEP = datetime.now()
        REASON = 'Too many requests'
        print(f"Too many requests")
        time.sleep(10)
        return get_app_details(app_id)
    elif (req.status_code == 403):
        datetime_now = datetime.now()
        if DATETIME_READ != None:
            update_log(datetime_now,datetime_now-DATETIME_READ,'read')
            DATETIME_READ = None
        if DATETIME_SLEEP == None:
            DATETIME_SLEEP = datetime.now()
        REASON = 'Forbidden'
        print(f"Forbidden")
        time.sleep(60*5)
        return get_app_details(app_id)  
    elif (req.status_code != 200):
        print(f"Failed to get app details for app_id: {app_id}")
        error_list_concat(app_id,str(req.status_code))
        return None
        
    try:
        data = req.json()
    except Exception as e:
        print('error',e)
        error_list_concat(app_id,'json error')
        return None
    
    if DATETIME_SLEEP != None:
        update_log(datetime.now(),datetime.now()-DATETIME_SLEEP,REASON)
        DATETIME_SLEEP = None
    
    if DATETIME_READ == None:
        DATETIME_READ = datetime.now()
    
    try:
        name = data[str(app_id)]['data']['name']
        about_game = clean_html(data[str(app_id)]['data']['about_the_game'])
        short_description = clean_html(data[str(app_id)]['data']['short_description'])
        detailed_description = clean_html(data[str(app_id)]['data']['detailed_description'])
        genres = [i['description'] for i in data[str(app_id)]['data']['genres']]
        categories = [i['description'] for i in data[str(app_id)]['data']['categories']]
        df = pd.DataFrame(
            columns=['app_id', 'name', 'about_game', 'short_description', 'detailed_description', 'genres', 'categories'],
            data=[[app_id, name, about_game, short_description, detailed_description, genres, categories]]
        )
    except Exception as e:
        error_list_concat(app_id,'data error')
        print('error',e)

        return None
    
    return df

def scraping_list(app_id_list):
    count = 0
    success = 0
    failed = 0
    last_save = 0
    df = pd.read_csv(STEAM_CSV)
    exist_game_id = df['app_id'].values
    exist_game_id = set(exist_game_id) 
    app_id_list = [app_id for app_id in app_id_list if app_id not in exist_game_id]
    error_list = pd.read_csv(ERROR_LIST_CSV)
    error_list = set(error_list['app_id'].values)
    app_id_list = [app_id for app_id in app_id_list if app_id not in error_list]
    
    len_app_id_list = len(app_id_list)
    for app_id in app_id_list:
        app_details = get_app_details(app_id)
        if app_details is not None:
            success += 1
            df = pd.concat([df, app_details], ignore_index=True)
        else:
            failed += 1
        os.system('cls')
        count += 1
        print(f"Progress: {count}/{len_app_id_list}")
        print(f"Last save: {last_save}")
        print(f"Success: {success}")
        print(f"Failed: {failed}")
        if count % 50 == 0:
            last_save = count
            df.to_csv(STEAM_CSV, index=False)
    df.to_csv(STEAM_CSV, index=False)
        
def main():
    app_id_list = sorted(get_all_app_id())
    scraping_list(app_id_list[:1000])
    scraping_list(app_id_list[1000:10000])
    scraping_list(app_id_list[10000:100000])
    scraping_list(app_id_list[100000:])
    
    
    
if __name__ == "__main__":
    main()

