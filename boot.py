import network
from time import sleep
import esp

esp.osdebug(None)


import gc
gc.collect()

#Entrer les paramètres du point d'accès
ssid = '<ssid_name>'
password = '<ssid_password>'

#Connexion au point d'accès
station = network.WLAN(network.STA_IF)
#station.ifconfig(('192.168.1.200', '255.255.255.0', '192.168.1.1', '192.168.1.1'))    # IP fixe sinon supprimer la ligne
station.active(True)
station.connect(ssid, password)


#Attendre que l'ESP soit connecté avant de poursuivre

print("Connexion ESP32 au point d'acces ", ssid)

while station.isconnected() == False:
    print('.', end = " ")
    sleep(1)
print("Connexion réussie")
print ("ESP32 : Adresse IP, masque, passerelle et DNS", station.ifconfig())