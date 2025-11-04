import time
import ubluetooth
from micropython import const
from commands import PRE_COMMANDS_RESULTS, COMMANDS_RESULTS
from simple import MQTTClient

MQTT_BROKER = "<mqtt_server_ip>"  # Adresse du broker MQTT
MQTT_PORT = 1883                   # Port MQTT (1883 pour non sécurisé)
MQTT_TOPIC = "elm327report/report"          # Sujet où publier les messages
MQTT_CLIENT_ID = "ESP32-ELM"  # Identifiant unique du client
MQTT_USER = "<mqtt_username>"          # Login MQTT
MQTT_PASS = "<mqtt_password>"
ELM_NAME = "<ELM_bluetooth_visible_name>"

def connect_mqtt():
    print("Connexion au broker MQTT...")
    try:
        client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, MQTT_PORT, user=MQTT_USER, password=MQTT_PASS)
        client.connect()
        print(f"Connecté au broker MQTT {MQTT_BROKER} sur le port {MQTT_PORT}")
        return client
    except Exception as e:
        print(f"Erreur lors de la connexion au broker MQTT : {e}")
        return None

# BLE IRQ events
class BLEEvents:
    IRQ_SCAN_RESULT = const(5)
    IRQ_SCAN_COMPLETE = const(6)
    IRQ_PERIPHERAL_CONNECT = const(7)
    IRQ_PERIPHERAL_DISCONNECT = const(8)
    IRQ_GATTC_SERVICE_RESULT = const(9)
    IRQ_GATTC_SERVICE_DONE = const(10)
    IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
    IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
    IRQ_GATTC_NOTIFY = const(18)
    IRQ_GATTC_WRITE_DONE = const(17)
    IRQ_CONNECTION_UPDATE = const(27)

class BLE_ELM:
    def __init__(self, cmd_handler=None):
        self.cmd_handler = cmd_handler  # Référence à SEND_CMD
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self.irq)
        self.scan_callback = None
        self.connect_callback = None
        self.discover_services_callback = None
        self.standby_callback = None
        self.current_service = 0
        self.services = []
        self.command_queue = []  # Liste des commandes à envoyer
        self.pending_command = None  # Commande en attente
        self.response = ""
        self.pre_commands_results = PRE_COMMANDS_RESULTS
        self.commands_results = COMMANDS_RESULTS
        self.rawSoc = ""
        self.rawRange = ""
        self.rawEnergy = ""
        self.rawOdometer = ""
        self.conn_handle = None
        self.device_found = False
        self.notify_handle = None
        self.write_handle = None


    def irq(self, event, data):
        if event == BLEEvents.IRQ_PERIPHERAL_CONNECT:
            self.conn_handle, addr_type, addr = data
            print(f"Connected to device: {bytes(addr)}")
            self.device_connected = True
            if self.connect_callback:
                self.connect_callback()

        elif event == BLEEvents.IRQ_PERIPHERAL_DISCONNECT:
            conn_handle, addr_type, addr = data
            print("Disconnected from device: {bytes(addr)}")
            self.conn_handle = None
            self.cmd_handler.command_queue = []
            self.cmd_handler.pending_command = None
            self.device_connected = False
            self.ble.gap_scan(10000, 30000, 30000)

        elif event == BLEEvents.IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            name = self.decode_name(adv_data)
            if name == ELM_NAME:
                print(f"Found bluedev: {bytes(addr)}")
                self.ble.gap_scan(None)  # Stop scanning
                self.device_found = True
                if self.scan_callback:
                    self.scan_callback(addr_type, addr)

        elif event == BLEEvents.IRQ_SCAN_COMPLETE:
            print("scan done")
            if not self.device_found:
                time.sleep(2)
                self.ble.gap_scan(10000, 30000, 30000)

        elif event == BLEEvents.IRQ_GATTC_SERVICE_RESULT:
            conn_handle, start_handle, end_handle, uuid = data
            #print(f"Discovered service: UUID={uuid}, Start={start_handle}, End={end_handle}")
            self.services.append({'uuid': str(uuid), 'start': start_handle, 'end': end_handle})
            #print(self.services)

        elif event == BLEEvents.IRQ_GATTC_SERVICE_DONE:
            conn_handle, status = data
            print("Service discovery complete.")
            self.current_service = 0
            self.discover_next_characteristic()

        elif event == BLEEvents.IRQ_GATTC_CHARACTERISTIC_RESULT:
            conn_handle, def_handle, value_handle, properties, uuid = data
            #print(f"Characteristic: UUID={uuid}, Handle={value_handle}, Properties={properties}")
            if properties & 0x10:
                self.notify_handle = value_handle
            elif properties & 0x04 or properties & 0x08:
                self.write_handle = value_handle



        elif event == BLEEvents.IRQ_GATTC_CHARACTERISTIC_DONE:
            conn_handle, status = data  # Ajout de `status` si disponible
            if status != 0:  # Vérifiez les erreurs
                print(f"Error discovering characteristics: status={status}")
            else:
                self.current_service += 1
                self.discover_next_characteristic()
                #print(self.services)

        elif event == BLEEvents.IRQ_GATTC_NOTIFY:
            conn_handle, char_handle, value = data
            decoded_value = str(value, "utf-8").replace('\r', '')
            #print(f"Reponse: {decoded_value}")
            self.response += decoded_value
            if ">" in decoded_value:
                #print(self.response)

                if self.cmd_handler:  # Transmettre la réponse à SEND_CMD
                    self.cmd_handler.on_notification(self.response, self.write_cmd)  # Appel à SEND_CMD
                    self.response = ""




        elif event == BLEEvents.IRQ_GATTC_WRITE_DONE:
            conn_handle, value_handle, status = data
            if status == 0:
                print(f"Write to characteristic {value_handle} successful.")
            else:
                print(f"Write to characteristic {value_handle} failed with status {status}.")

        elif event == BLEEvents.IRQ_CONNECTION_UPDATE:
            conn_handle, conn_interval, conn_latency, supervision_timeout, status = data
            print(f"Update received, conn_interval: {conn_interval} conn_latency: {conn_latency} supervision_timeout: {supervision_timeout}, status: {status} ", )
            # for response in self.responses:
            #     #decoded_response = self.filter_printable_chars(response)
            #     print(f"response: {response}\r")
        else:
            print("Événement inconnu :", event)

    def decode_name(self, adv_data):
        name = ""
        i = 0
        while i < len(adv_data):
            length = adv_data[i]
            if length == 0:
                break
            type = adv_data[i + 1]
            if type == 0x09:  # Complete Local Name
                name = str(adv_data[i + 2:i + 1 + length], "utf-8").strip().replace('\x00', '')
            i += length + 1
        return name

    def convert_characteristic_properties(self, properties):
        prop_str = ""
        if properties & 0x01:
            prop_str += "Broadcast "
        if properties & 0x02:
            prop_str += "Read "
        if properties & 0x04:
            prop_str += "Write Without Response "
        if properties & 0x08:
            prop_str += "Write "
        if properties & 0x10:
            prop_str += "Notify "
        if properties & 0x20:
            prop_str += "Indicate "
        if properties & 0x40:
            prop_str += "Authenticated Signed Writes "
        if properties & 0x80:
            prop_str += "Extended Properties "
        return prop_str.strip()
    def discover_next_characteristic(self):
        if self.current_service >= len(self.services):
            print("All services and characteristics discovered.")

            if self.discover_services_callback:
                self.discover_services_callback()
            return  # Sortie pour éviter des appels supplémentaires

        service = self.services[self.current_service]
        try:
            #print(f"Discovering characteristics for service UUID={service['uuid']}")
            self.ble.gattc_discover_characteristics(self.conn_handle, service['start'], service['end'])
        except Exception as e:
            print(f"Error discovering characteristics: {e}")


    def scan(self, callback):
        self.scan_callback = callback
        self.ble.gap_scan(10000, 30000, 30000)

    def connect(self, addr_type, addr, callback):
        self.connect_callback = callback
        self.ble.gap_connect(addr_type, addr)

    def discover_services(self, callback):
        self.discover_services_callback = callback
        self.ble.gattc_discover_services(self.conn_handle)

    def write_cmd(self, value):
        # Convertir la commande en bytes si ce n'est pas déjà fait
        if isinstance(value, str):
            value = value.encode('utf-8')
        try:
            self.ble.gattc_write(self.conn_handle, self.write_handle, value)  # Mode True = sans réponse
            print(f"Writing value {value} to characteristic with handle {self.write_handle}")
        except Exception as e:
            print(f"Failed to write characteristic: {e}")

    def enable_notifications(self, callback):
        cccd_handle = self.notify_handle + 1  # CCCD est généralement juste après la caractéristique
        try:
            self.ble.gattc_write(self.conn_handle, cccd_handle, b'\x01\x00')
            print(f"Notifications enabled for characteristic {self.notify_handle}")
            time.sleep(0.2)
            callback()
        except Exception as e:
            print(f"Failed to enable notifications: {e}")

    def filter_printable_chars(self, raw_data):
        """
        Filtre les caractères imprimables d'une réponse brute.
        :param raw_data: Données brutes sous forme de bytes ou de string.
        :return: Chaîne contenant uniquement les caractères imprimables.
        """
        # Si les données sont en bytes, convertissez-les en string
        raw_data = str(raw_data,'utf-8')

        # Filtrer les caractères imprimables (ASCII 32 à 126 inclus)
        elm_response = ''.join(c for c in raw_data if 32 <= ord(c) <= 126)
        return elm_response



class SEND_CMD:
    def __init__(self):
        self.command_queue = []  # Liste des commandes à envoyer
        self.pending_command = None  # Commande en attente
        self.response = ""
        self.pre_commands_results = PRE_COMMANDS_RESULTS
        self.commands_results = COMMANDS_RESULTS
        self.rawSoc = ""
        self.rawRange = ""
        self.rawEnergy = ""
        self.rawOdometer = ""
        self.standby_callback = None

    def send_command(self, cmd, write_cmd):
        self.command_queue.append(cmd)
        if not self.pending_command:  # Si aucune commande n'est en cours
            self.on_notification("", write_cmd)

    def on_notification(self, response, write_cmd):
        if not response  == "":
            expected_result = self.pending_command
            if expected_result is None:
                raise KeyError(f"Command {self.pending_command} not found in pre_commands_results or commands_results")

            elif expected_result[2] and expected_result[1] in response:
                print(f"Partial Result matches! {response}")
                if len(expected_result) > 3:
                    key = "raw" + expected_result[3]
                    setattr(self, key, response)

                self.pending_command = None
                self.response = ""

            elif not expected_result[2] and expected_result[1] == response:
                print("Result matches!")
                self.pending_command = None


            else:
                print(f"wrong response {response}")
                return

        if not self.command_queue:
            print("No more commands to process.")
            self.standby_callback()
            return

        if not self.pending_command:
            # Envoyer la prochaine commande
            self.pending_command = self.command_queue.pop(0)
            print(f"Sending command: {self.pending_command}")
            write_cmd(self.pending_command[0] + "\r")

def main():
    client = connect_mqtt()
    if not client:
        print("Échec de la connexion au broker MQTT. Vérifiez vos paramètres.")
        return

    # Publier des messages si connecté
    try:
        message = "ESP32-ELM"
        client.publish(MQTT_TOPIC, message)
        print(f"Publié: {message} sur le sujet {MQTT_TOPIC}")

    except Exception as e:
        print(f"Erreur lors de l'envoi des messages : {e}")

    def on_device_found(addr_type, addr):
        print("Connecting to device...")
        my_ble.connect(addr_type, addr, on_connected)

    def on_connected():
        print("Discovering services...")
        my_ble.discover_services(on_services_discovered)
        #, on_services_discovered#)

    def on_services_discovered():
        print("Services discovered")
        if my_ble.notify_handle is not None and my_ble.write_handle is not None:
            print("Notify and Write caracteristics found")
            my_ble.enable_notifications(launch)


        else:
            print("No writable or Notify characteristic found.")
            my_ble.scan(on_device_found)

    def launch():
        print("lanched")
        my_ble.standby_callback = on_standby

        for pre_cmd in my_ble.pre_commands_results:
            # print(f"PRE_CMD: {pre_cmd} {pre_response}, {pre_partial}" )
            my_cmd.send_command(pre_cmd, my_ble.write_cmd)
            # print(f"CMD: {cmd} {response}, {partial}" )

        for cmd in my_ble.commands_results:
            my_cmd.send_command(cmd, my_ble.write_cmd)

    def on_standby():
        print(f"SOC: {my_ble.rawSoc}")
        # Suppression du préfixe "05622002"
        soc = my_ble.rawSoc.replace("05622002", "")
        # Extraction des 4 premiers caractères
        soc = soc[:4]
        # Conversion hexadécimale en entier
        soc_int = int(soc, 16)
        # Calcul de la valeur SoCf
        soc_float = 0.02 * soc_int
        print(f"SoC (float): {soc_float}")

        print(f"Range: {my_ble.rawRange}")
        # Suppression du préfixe "05623451"
        available_range = my_ble.rawRange.replace("05623451", "")
        # Extraction des 4 premiers caractères
        available_range = available_range[:4]
        # Conversion hexadécimale en entier
        available_range_int = int(available_range, 16)
        print(f"Available Range (int): {available_range_int}")

        print(f"Energy: {my_ble.rawEnergy}")
        # Suppression du préfixe "0562320C"
        available_energy = my_ble.rawEnergy.replace("0562320C", "")
        # Extraction des 4 premiers caractères
        available_energy = available_energy[:4]
        # Conversion hexadécimale en entier
        available_energy_int = int(available_energy, 16)
        # Conversion en énergie avec le facteur 0.005
        available_energy_float = 0.005 * available_energy_int
        print(f"Available Energy (float): {available_energy_float}")

        print(f"Meter: {my_ble.rawOdometer}")
        # Suppression du préfixe "03222006"
        odometer = my_ble.rawOdometer.replace("03222006", "")
        # Extraction des caractères de position 8 à 13 (6 caractères)
        odometer = odometer[8:14]
        # Conversion hexadécimale en entier
        odometer_int = int(odometer, 16)
        print(f"Odometer (integer): {odometer_int}")

        time.sleep(30)
        launch()

    my_cmd = SEND_CMD()
    my_ble = BLE_ELM(cmd_handler=my_cmd)
    my_ble.scan(on_device_found)


if __name__ == "__main__":
    main()
