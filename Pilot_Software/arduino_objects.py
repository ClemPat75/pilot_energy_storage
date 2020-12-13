import pyfirmata
import time
import numpy as np
import os
import datetime

from Create_excel_file import create_excel

"""
Voltmeter pin A0
sensor pin A1
tachymeter pin A2
IN3 pin d7
IN4 pin d8
ENB pin d9"""
"""740g 0,75cL"""

class Arduino_uno_board():

    def __init__(self, usb_port, analogs=[], output_pins=[], pwm_pins=[], servo_pins=[]):
        """analogs = [0, 1, 2, 3, 4, 5], output_pins = [2, 4, 7, 8, 12, 13], pwm_pins=[3, 5, 6, 9, 10, 11]"""

        self.name = "board_" + usb_port
        self.port = usb_port
        self.arduinoboard = None
        self.analog_pins = analogs
        self.digital_pins = output_pins + pwm_pins + servo_pins
        self.pwm_pins = pwm_pins
        self.servo_pins = servo_pins
        self.app = None
        self.pin = None
        self.analog_Umes, self.analog_sens, self.analog_tach = self.get_voltmeter_value(), self.get_sensor_value(), self.get_rotation_speed_value()
        self.motor_is_on = False
        self.pilot_mode = "manual"
        self.record_demanded = False
        self.record_period = 0.1  # période d'acquisition en secondes
        self.t0_record, self.time_list, self.Umes_list, self.distance_list, self.rotation_list, self.bits_list, self.motor_is_on_list = time.time(), [0], [0.0], [self.analog_sens], [self.analog_tach], [0], [int(self.motor_is_on)]
        self.time_list_plot, self.Umes_list_plot, self.distance_list_plot, self.rotation_list_plot, self.bits_list_plot, self.motor_is_on_list_plot = [0], [0], [self.analog_sens], [self.analog_tach], [0], [int(self.motor_is_on)]
        self.excel_names_already_used = []
        self.path = os.path.dirname(os.path.abspath(__file__))

    def reload(self):
        try:
            self.arduinoboard = pyfirmata.Arduino(self.port)
            self.app.canvas[0].itemconfig(
                2,  text="Arduino branchée {}".format(self.port), fill="green")
        except:
            self.arduinoboard = None

        if self.arduinoboard != None:
            self.iterate = pyfirmata.util.Iterator(self.arduinoboard)
            self.iterate.start()
            time.sleep(1)

            self.pin = {}
            for i in self.analog_pins:
                self.arduinoboard.analog[i].enable_reporting()
                self.pin[f"A{i}"] = self.arduinoboard.analog[i]
                self.pin[f"A{i}"].value = self.pin[f"A{i}"].read()
                time.sleep(0.5)

            for j in self.digital_pins:
                if j in self.pwm_pins:
                    self.pin[f"d{j}"] = self.arduinoboard.get_pin(f"d:{j}:p")
                elif j in self.servo_pins:
                    self.pin[f"d{j}"] = self.arduinoboard.get_pin(f"d:{j}:s")
                else:
                    self.pin[f"d{j}"] = self.arduinoboard.get_pin(f"d:{j}:o")
                self.pin[f"d{j}"].value = None

            self.init_board()

        else:
            self.pin = {}
            for i in self.analog_pins:
                self.pin[f"A{i}"] = None
            for i in self.digital_pins:
                self.pin[f"d{i}"] = None

    def init_board(self):
        if self.arduinoboard != None:
            self.pin["d9"].write(0)
            self.pin["d7"].write(0)
            self.pin["d8"].write(1)

    def exit(self):
        if self.arduinoboard != None:
            self.arduinoboard.exit()

    def get_voltmeter_value(self):
        if self.arduinoboard != None:
            return (self.pin["A0"].read())*5
        else:
            return 0

    def get_sensor_value(self):
        """grâce à étude du capteur de distance Sensor_study"""
        if self.arduinoboard != None:
            if 1 in self.analog_pins:
                x = float(self.pin["A1"].read())
                # value = float(48.366*np.exp(-(float(x)-0.102)/0.109)+7.931) #3/2
                # value = float(71.36*np.exp(-(float(x)-78.2*10**(-3))/0.104)+9.445) #5/2 old
                if x > 0.43 and x <= 0.7:  # entre 5 et 13 cm
                    value = float(-24.891 * float(x) + 23.646)
                elif x >= 0.15 and x <= 0.43:  # entre 13cm et 40cm
                    value = float(28.553 * np.exp(-(float(x) - 0.154) / 0.13) + 9.706)
                elif x > 0.12 and x < 0.15:  # entre 40 et 50cm
                    value = float(-520 * float(x) + 117)
                elif x > 0.08 and x <= 0.12:  # entre 50 et 80cm
                    value = float(79.49 * np.exp(- (float(x) - 0.089) / 0.084762) - 0.512)
                else:
                    value = 80
                return value
        else:
            return 0

    def get_rotation_speed_value(self):
        """Grâce aux études de capteurs Tachymeter_study, et Violette"s study"""
        if self.arduinoboard != None:
            return 376.64 * self.pin["A2"].read() + 288.92  # Violette"s study
        else:
            return 0

    def change_motor_rotation(self, rotation_direction):
        if self.arduinoboard != None:
            if rotation_direction == "direct":
                self.pin["d7"].write(0)
                self.pin["d8"].write(1)
            elif rotation_direction == "indirect":
                self.pin["d7"].write(1)
                self.pin["d8"].write(0)

    def change_motor_speed(self, value):
        if self.arduinoboard != None and self.motor_is_on:
            self.pin["d9"].write(int(value) / 255)

    def stop_motor(self, forced=False):
        self.motor_is_on = False
        self.motor_is_forced = forced
        if self.arduinoboard != None:
            self.pin["d9"].write(0)

    def start_motor(self, forced=False):
        self.motor_is_on = True
        self.motor_is_forced = forced
        if self.arduinoboard != None:
            self.pin["d9"].write(int(self.app.scales[0].value) / 255)

    def start_recording(self):
        self.t0_record, self.time_list, self.Umes_list, self.distance_list, self.rotation_list, self.bits_list, self.motor_is_on_list = time.time(), [0.0], [self.analog_Umes], [self.analog_sens], [self.analog_tach], [self.app.scales[0].value], [int(self.motor_is_on)]
        self.record_demanded = True

    def record_mesures(self):
        if self.record_demanded == True:
            if (time.time() - self.t0_record) - self.time_list[-1] >= self.record_period:
                self.time_list.append(time.time() - self.t0_record)
                self.Umes_list.append(self.analog_Umes)
                self.distance_list.append(self.analog_sens)
                self.rotation_list.append(self.analog_tach)
                self.bits_list.append(self.app.scales[0].value)
                self.motor_is_on_list.append(int(self.motor_is_on))

        if (time.time() - self.app.t0) - self.time_list_plot[-1] >= self.record_period:
            self.time_list_plot.append(time.time() - self.app.t0)
            self.Umes_list_plot.append(self.analog_Umes)
            self.distance_list_plot.append(self.analog_sens)
            self.rotation_list_plot.append(self.analog_tach)
            self.bits_list_plot.append(self.app.scales[0].value)
            self.motor_is_on_list_plot.append(int(self.motor_is_on))
            if len(self.time_list_plot) > 30:
                self.time_list_plot.pop(0)
                self.Umes_list_plot.pop(0)
                self.distance_list_plot.pop(0)
                self.rotation_list_plot.pop(0)
                self.bits_list_plot.pop(0)
                self.motor_is_on_list_plot.pop(0)

            if self.app.plot_app != None:
                self.app.plot_app.plot_mesures()

    def stop_recording(self):
        def find_file_name():
            date = datetime.date.today().strftime("%d/%m/%Y").split("/")
            today = f"{date[0]}-{date[1]}"
            if self.app.entrys[1]["fg"] == "green": comment = f"_{str(self.app.entrys[1].get())}"
            else: comment = ""
            name = f"Expérience_{today}{comment}"
            i = 1
            if self.arduinoboard == None:
                while f"{name}_TEST({i})" in self.excel_names_already_used: i += 1
                name = f"{name}_TEST({i})"
            else:
                while f"{name}({i})" in self.excel_names_already_used: i += 1
                name = f"{name}({i})"
            self.excel_names_already_used.append(name)
            print(f"will create {name} ({len(self.time_list)} values)")
            return name
        def find_file_path():
            date = datetime.date.today().strftime("%d/%m/%Y").split("/")
            today = f"{date[0]}-{date[1]}"
            folder_path = f"{self.path}/{today}"
            try: os.mkdir(folder_path) #si le dossier n"existe pas on le crée
            except FileExistsError: pass #si le dossier existe déjà on ne fait rien
            return folder_path
        def console_text_back_to_normal():
            self.app.canvas[0].itemconfig(2, text=old_text, fill=old_color)

        self.record_demanded = False

        path = find_file_path()
        name = find_file_name()
        success = create_excel(self.time_list, self.Umes_list, self.distance_list, self.rotation_list,
                               self.bits_list, self.motor_is_on_list, path, name)
        if success:
            old_text, old_color = self.app.canvas[0].itemcget(2, "text"), self.app.canvas[0].itemcget(2, "fill")
            self.app.canvas[0].itemconfig(2, text=f"Fichier {name} créé ({len(self.time_list)} valeurs)", fill="green")
            self.app.fen.after(3000, console_text_back_to_normal)
        else:
            old_text, old_color = self.app.canvas[0].itemcget(2, "text"), self.app.canvas[0].itemcget(2, "fill")
            self.app.canvas[0].itemconfig(2, text=f"Une erreur est survenue !!", fill="red")
            self.app.fen.after(3000, console_text_back_to_normal)
            print("FAILED !")
            print("")
