from api import api, api2
import requests 

url = api 


res = requests.get(url)
print(res)
if res == 200 :

    b1 = requests.cget(api2)
    print(b1)
