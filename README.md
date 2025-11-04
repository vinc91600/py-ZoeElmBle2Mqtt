# Micropython Zoe Ble Elm to MQTT - Draft
Micropython ESP32 tool to connect ELM BLE OBD2 to HomeAssistant with MQTT

# Origin
This tool is inspired from this project: https://github.com/sanchosk/ZoeELM2MQTT which is similar but only work with classic bluetooth ELM but not bluetooth 5.0 low energy BLE.
As for this statment, I decided to rewrite it for BLE and with micropython that is more in my taste.
I am not a developper and this project is written with assumed help of AI. Through, this BLE implementation gave me a lot of headheck but it works for me and allow me to cut the charge at 80% with smartplug. I hope it can work for you too.

# Setup
1. Select hardware, most of esp32 should work. I use ESP-WROOM- 32. I use KONNWEI ELM from official aliexpress store. It use BLE. As it doesn't ask for PIN, the code doesn't handle PIN if required.
2. Flash with micropython. You can use esp tool or Thonny.
3. Download files, edit main.py with MQTT settings and ELM name. Edit boot.py with Wifi settings. 
4. Write file to ESP with esp tool or Thonny.
5. Configure Home assistant
6. Connect ELM to car ODB2 and power the ESP. It should connect to Wifi first the to ELM. Note that OBD2 only work when car is on or plug to AC.

# To Do
1. Translate comments and debug output
2. Develop the documentation
3. Handle WIFI disconnection event
4. Implement PIN for ELM
5. Retrieve more data.
