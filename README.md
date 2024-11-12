# Enviro-Plus-Web
Adds free OpenWeather winddirection and -speed to Enviro+ webapp (https://gitlab.com/idotj/enviroplusweb)

As winddirection and -speed influence the Enviro+ sensor readings free OpenWeather info is added to the webapp that can be found here https://gitlab.com/idotj/enviroplusweb

Add your free OpenWeather API key and your latitude and longitude to Enviroplusweb.py
Get your free API key: https://home.openweathermap.org/users/sign_up and read: https://openweathermap.org/appid
API_KEY = "Your API-KEY" # Your API-KEY
LAT = Your latitude  # Your latitude
LON = Your longitude  # Your longitude

Make an free API call no more than once in 10 minutes for your location otherwise you will be blocked.
The update frequency of the OpenWeather model is not higher than once in 10 minutes.
The update frequency is set in Enviroplusweb.py to 10 minutes/600 seconds before fetching data again.

For now it works but isn't perfect yet so please improve, such as:
- Still have to set stepSize in main.js
- Making setting True or False in enviroplusweb.py work to select if OpenWeatherMap wind speed or direction data is displayed or not, now they are always displayed
- Windspeed is only in km/h units
- ...

![Windspeed and -direction](https://github.com/user-attachments/assets/03c23231-667f-4b2a-9844-245ac759b7f6)

Added translation in Dutch, rename index(Dutch).html to index.html
