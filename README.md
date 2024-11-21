# Enviro-Plus-Web
Add-on Free OpenWeather winddirection and -speed

Add-on Turn PMS5003 sensor on/off between readings to extend sensor lifetime

Add-on Dewpoint

Add-on Wind chill

to Enviro+ webapp (https://gitlab.com/idotj/enviroplusweb)

# Winddirection and -speed from OpenWeather
As winddirection and -speed influence the Enviro+ sensor readings free OpenWeather info is added to the webapp that can be found here https://gitlab.com/idotj/enviroplusweb

Add your free OpenWeather API key and your latitude and longitude to Enviroplusweb.py
Get your free API key: https://home.openweathermap.org/users/sign_up and read: https://openweathermap.org/appid
API_KEY = "Your API-KEY" # Your API-KEY
LAT = Your latitude  # Your latitude
LON = Your longitude  # Your longitude.
Next to .py file you also need the .html file in templates directory and .js file in static/js directory

Make an free API call no more than once in 10 minutes for your location otherwise you will be blocked.
The update frequency of the OpenWeather model is not higher than once in 10 minutes.
The update frequency is set in Enviroplusweb.py to 10 minutes/600 seconds before fetching data again.

For now it works but isn't perfect yet so please improve, such as:
- Still have to set stepSize in main.js
- Making setting True or False in enviroplusweb.py work to select if OpenWeatherMap wind speed or direction data is displayed or not, now they are always displayed
- Windspeed is only in km/h units
- ...

![Windspeed and -direction](https://github.com/user-attachments/assets/03c23231-667f-4b2a-9844-245ac759b7f6)

# Extend pms5003 sensor lifetime
If you want to extend the lifetime of your pms5003 sensor and OpenWeather winddirection and -speed data use the other .py file.
It turns the PMS5003 sensor on/off between readings to extend sensor lifetime using Python's serial library.
The serial port shouldn't be used by other processes therefore disable Bluetooth and use the UART for PMS5003 Control. Edit the /boot/config.txt file:

    sudo nano /boot/config.txt
    
Add or ensure that the following lines are present and comment out #dtoverlay=pi3-miniuart-bt:

    enable_uart=1
    dtoverlay=pi3-disable-bt  # This disables Bluetooth and frees up the UART
    
Now the UART is available for communicating with the PMS5003 sensor. Reboot the Pi to apply changes:

    sudo reboot

# Dewpoint
Added dewpoint. In relation to humidity levels the dew point directly correlates with the amount of moisture in the air. Higher dew points (above 15–20°C): Indicate humid, sticky, and potentially uncomfortable conditions. Lower dew points (below 10°C): Indicate drier, more comfortable air. Unlike relative humidity, the dew point provides an absolute measure of moisture, making it easier to interpret. In relation to weather prediction there will be fog Formation: If the dew point is close to the air temperature, fog or dew is likely to form overnight. Precipitation Potential: A high dew point often indicates the potential for rain or storms, as it signifies more moisture in the atmosphere. Severe Weather: Dew points above 20°C are commonly associated with thunderstorms and tropical weather systems.

# Wind chill
Added wind chill. Wind chill (popularly wind chill factor) is the sensation of cold produced by the wind for a given ambient air temperature on exposed skin as the air motion accelerates the rate of heat transfer from the body to the surrounding atmosphere. Its values are always lower than the air temperature in the range where the formula is valid. When the temperature > 10 or windspd < 4.8 the wind chill is set equal to the temperature.

# Translation Dutch language
Added translation in Dutch for the text used in the webapp, rename index(Dutch).html to index.html
