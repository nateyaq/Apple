import requests
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# set headers for API call
headers = {'User-Agent': "zz@gmail.com"}

#set cik for the url string
cik = "0000320193"

#set the url string
URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK" + cik + ".json"
#response = requests.get("https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json", headers=headers)

#make the api call and set the response to a variable
response = requests.get(URL, headers=headers)

#raise and exception if the response is not 200
#response.raise_for_status()  # raises exception when not a 2xx response
#if response.status_code != 204:
# print(response.json())


#set URL of SEC website for company names
#URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"

#load json data from URL and save as a variable called data
#data = json.loads(requests.get(URL).text)



# set the keys of json file as variable X
x = response.json().keys()
#show the keys saved to variable x
#x

data = pd.json_normalize(response.json(), max_level = 2 ,meta='units')

#data.info()
#data


#Command K + C to comment out multiple lines
#Command K + U to uncomment out multiple lines


# for i in range(1,5):    
# for col in data.columns():
# # store column name as a variable
# col_name = col
# z = col_name
# print(z)

#loop through the column names and store as variable x
#for x in data.columns:
#    z = x


z = data['facts.us-gaap.AccountsPayableCurrent']
#z =data[col]


data_elements = pd.json_normalize(z, record_path=['units','USD'])


data_elements[['end','val','fy','fp','form','filed']]
print(data_elements)
#data_elements.loc[(data_elements[['end','val','fy','fp','form','filed']]) & (data_elements[['form']] == '10-K')]
"""
#
plot_data = data_elements[data_elements.isin(['10-K']).any(axis=1)]

plot_data



z.name = z.name[14:]
plotTitle = str(data['entityName'] + ' ' + z.name) # add new line to string


#delete the first 2 characters of the string
plotTitle = plotTitle[5:-31]

#print(plotTitle)


plt.style.use('fivethirtyeight')
plt.figure(figsize=(14,6), layout="constrained")
plt.title(str(plotTitle))
plt.ylim(bottom = int(plot_data['val'].min()), top = int(plot_data['val'].max()))
plt.xlim(plot_data['end'].min(), plot_data['end'].max(), 10)
plt.plot(plot_data[['val']], color="Orange", label=(plot_data['val'].name))
plt.ylabel("USD")
plt.xlabel("Date")
plt.legend()
plt.grid(True)
plt.show()


#plt.plot(plot_data[['val']], color="Orange", label=(plot_data['val'].name))
#plt.xlim(plot_data['fy'].min(), plot_data['fy'].max())
#plt.ylim(plot_data['val'].min(), plot_data['val'].max())
#plt.ylabel("USD")
#plt.xlabel("Date")
#plt.legend()
#plt.grid(True)
#plt.show()


"""