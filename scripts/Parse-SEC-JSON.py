import requests
import json
import pandas as pd

# set headers for API call
headers = {'User-Agent': "123@gmail.com"}

#set cik for the url string
cik = "0000320193"

#set the url string
URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK" + cik + ".json"
#response = requests.get("https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json", headers=headers)

#make the api call and set the response to a variable
response = requests.get(URL, headers=headers)

# set the keys of json file as variable X
x = response.json().keys()

data = pd.json_normalize(response.json(), max_level = 2 ,meta='units')

