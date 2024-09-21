import time
import winsound
import json
import requests as req
import math
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtWidgets import QListWidgetItem, QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, QEvent, Qt
import gui
import binance_api

is_track = True
track_list = list()
available_pairs = dict()
active_alarms = dict()
trade_alarms = dict()
alarm_parameters = dict()
alarm_list = [active_alarms, trade_alarms]

class Worker(QObject):
    alarm_completed = pyqtSignal(float, dict, int)
    alarm_requested = pyqtSignal(int)

    track_completed = pyqtSignal(dict)
    track_requested = pyqtSignal(int)

    @pyqtSlot(int)
    def activate_alarms(self, n):
        endpoint = 'https://api.binance.com/api/v3/ticker/price'

        while True:
            try:
                temp_active_alarms = active_alarms
                temp_trade_alarms = trade_alarms
                temp_alarm_list = [temp_active_alarms, temp_trade_alarms]

                tickers = list()
                for alarm_dict in temp_alarm_list:
                    for key, value in alarm_dict.items():
                        tickers.append(value["pair"])

                response = req.get(endpoint).json()
                all_ticker_prices = {item['symbol']: item['price'] for item in response if item['symbol'] in tickers}

                for alarm_dict in temp_alarm_list:
                    for key, value in alarm_dict.items():
                        price = float(all_ticker_prices[value["pair"]])

                        if value["direction"] == "Rises above" and float(value["price"]) <= price:
                            self.alarm_completed.emit(price, value, 0)
                            self.annoy(0)
                        elif value["direction"] == "Drops below" and float(value["price"]) >= price:
                            self.alarm_completed.emit(price, value, 1)
                            self.annoy(1)
            except:
                pass

            time.sleep(3)

    @pyqtSlot(int)
    def track(self, n):
        endpoint = 'https://api.binance.com/api/v3/ticker/price'

        while True:
            if is_track:
                try:
                    response = req.get(endpoint).json()
                    track_dict = {item['symbol']: item['price'] for item in response if item['symbol'] in track_list}
                    self.track_completed.emit(track_dict)
                except:
                    pass

            time.sleep(2)

    def annoy(self, mod):
        if not alarm_parameters["is_mute"]:
            for j in range(1, alarm_parameters["alarm_duration"]):
                for i in range(1, 5):
                    if mod == 0:
                        winsound.Beep(i * 100, 200)
                    elif mod == 1:
                        winsound.Beep(i * 140, 300)
                    else:
                        winsound.Beep(i * 160, 200)


class MyMainWindow(QtWidgets.QMainWindow, gui.Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.alarm_actions = ["Delete"]
        self.orders_dict = dict()
        self.configuration = dict()
        self.latest_right_click = -1
        self.current_row = -1
        self.is_tracking = 0

        self.setupUi(self)
        self.initialize()


    def tradeAlarmsMousePressEvent(self, event):
        try:
            self.current_row = (event.pos().y() // 30) + self.tradeAlarmsListWidget.verticalScrollBar().value()

            if event.button() == 1:
                self.tradeAlarmActions.setVisible(False)

            elif event.button() == 2:
                self.tradeAlarmActions.move(event.x(), event.y())
                self.tradeAlarmActions.setVisible(True)
                self.latest_right_click = 1

            QtWidgets.QListWidget.mousePressEvent(self.tradeAlarmsListWidget, event)
        except:
            pass

    def activeAlarmsMousePressEvent(self, event):
        try:
            self.current_row = (event.pos().y() // 30) + self.activeAlarmsListWidget.verticalScrollBar().value()

            if event.button() == 1:
                self.activeAlarmActions.setVisible(False)

            elif event.button() == 2:
                self.activeAlarmActions.move(event.x(), event.y())
                self.activeAlarmActions.setVisible(True)
                self.latest_right_click = 0

            QtWidgets.QListWidget.mousePressEvent(self.activeAlarmsListWidget, event)
        except:
            pass

    def alarmsActionsListWidgetMousePressEvent(self, event):
        global active_alarms, trade_alarms

        if event.button() == 1:
            try:
                if self.latest_right_click == 0:
                    for idx, (key, value) in enumerate(active_alarms.items()):
                        if idx == self.current_row:
                            active_alarms.pop(key)
                            break
                    self.activeAlarmsListWidget.takeItem(self.current_row)
                    active_alarms = self.arange_alarm_dict(active_alarms)

                elif self.latest_right_click == 1:
                    for idx, (key, value) in enumerate(trade_alarms.items()):
                        if idx == self.current_row:
                            trade_alarms.pop(key)
                            break
                    self.tradeAlarmsListWidget.takeItem(self.current_row)
                    trade_alarms = self.arange_alarm_dict(trade_alarms)

            except:
                pass

            self.tradeAlarmActions.setVisible(False)

        elif event.button() == 2:
            self.tradeAlarmActions.setVisible(False)

        QtWidgets.QListWidget.mousePressEvent(self.tradeAlarmActions, event)

    def custom_round(self, value):
        if abs(value) >= 1:
            return round(value, 2)
        else:
            if value == 0:
                return 0
            else:
                return round(value, 4 - int(math.floor(math.log10(abs(value)))) - 1)

    def add_alarm(self, _type=False):
        try:
            coin = self.alarmCoinLineEdit.text().upper()
            pair = coin + "USDT"

            if pair in available_pairs:
                price = 0 if self.priceLineEdit.text() == "" else float(self.priceLineEdit.text())
                price_range = 0 if self.rangeLineEdit.text() == "" else float(self.rangeLineEdit.text())
                is_range = self.rangeCheckBox.isChecked()
                is_trade = self.tradeCheckBox.isChecked()
                direction = self.alarmComboBox.currentText()
                symbol = "▲" if direction == "Rises above" else "▼"

                alarm_string = f"{pair} | {price} | {symbol}"
                alarm_value = {"row_id": -1, "name": coin, "pair": coin + "USDT", "price": float(price),
                               "range": price_range, "is_range": is_range, "is_trade": is_trade, "direction": direction}

                if price_range != 0 and is_range:
                    current_price = req.get(
                        'https://api.binance.com/api/v3/ticker/price?symbol=' + coin.upper() + "USDT").json()
                    current_price = float(current_price['price'])

                    symbol = "▼"
                    price = self.custom_round(current_price * (1 - price_range / 100))
                    alarm_string = f"{pair} | {price} | {symbol}"
                    alarm_value = {"row_id": -1, "name": coin, "pair": coin + "USDT", "price": float(price),
                                   "range": price_range, "is_range": is_range, "is_trade": is_trade,
                                   "direction": "Drops below"}

                    self.activeAlarmsListWidget.addItem(alarm_string)
                    alarm_value["row_id"] = len(active_alarms)
                    active_alarms[str(len(active_alarms))] = alarm_value

                    symbol = "▲"
                    price = self.custom_round(current_price * (1 + price_range / 100))
                    alarm_string = f"{pair} | {price} | {symbol}"
                    alarm_value = {"row_id": -1, "name": coin, "pair": coin + "USDT", "price": float(price),
                                   "range": range, "is_range": is_range, "is_trade": is_trade,
                                   "direction": "Rises above"}

                    self.activeAlarmsListWidget.addItem(alarm_string)
                    alarm_value["row_id"] = len(active_alarms)
                    active_alarms[str(len(active_alarms))] = alarm_value

                elif _type:
                    self.tradeAlarmsListWidget.addItem(alarm_string)
                    alarm_value["row_id"] = len(trade_alarms)
                    trade_alarms[str(len(trade_alarms))] = alarm_value

                else:
                    self.activeAlarmsListWidget.addItem(alarm_string)
                    alarm_value["row_id"] = len(active_alarms)
                    active_alarms[str(len(active_alarms))] = alarm_value

            else:
                self.warn("Pair is not available.")

        except:
            pass

    def set_order(self, symbol, side, _type, price, amount):
        try:
            response = binance_api.set_order(symbol, side, _type, price, amount, self.api_secret, self.api_key).json()

            if 'msg' in response.keys():
                self.warn(response['msg'])

        except Exception as e:
            self.warn("Invalid or missing parameters.")

    def cancel_order(self):
        try:
            symbol = self.orders_dict[str(self.ordersListWidget.currentRow() - 1)]["symbol"]
            order_id = self.orders_dict[str(self.ordersListWidget.currentRow() - 1)]["order_id"]

            response = binance_api.cancel_order(symbol, order_id, self.api_secret, self.api_key)

            time.sleep(1)
            self.query_orders()

        except:
            self.warn(response['msg'])

    def query_price(self, pair, _id):
        try:
            response = req.get('https://api.binance.com/api/v3/ticker/price?symbol=' + pair.upper() + "USDT").json()

            if _id == 0:
                self.retrievedPriceLabel.setText(response['price'].strip(" "))
            elif _id == 1:
                self.retrievedPriceLabel2.setText(response['price'].strip(" "))

        except:
            self.warn(response['msg'])

    def query_balances(self):
        try:
            response = binance_api.query_balances(self.api_secret, self.api_key)
            balances_dict = json.loads(str(response.content)[2:-1])
            balances = dict()

            for balance in balances_dict["balances"]:
                amount = float(balance["free"]) + float(balance["locked"])

                if balance["asset"] == "USDT":
                    balances["USDTTRY"] = amount

                if amount > 0:
                    balances[balance["asset"].upper() + "USDT"] = amount

            endpoint = 'https://api.binance.com/api/v3/ticker/price'
            response = req.get(endpoint).json()

            new_balances = dict()
            ticker_prices = {item['symbol']: item['price'] for item in response if item['symbol'] in balances.keys()}

            for ticker, price in ticker_prices.items():
                if ticker != "USDTTRY":
                    value = float(balances[ticker]) * float(price)
                    if value > 10:
                        new_balances[ticker.replace("USDT", "")] = [value, float(balances[ticker])]
                else:
                    value = float(balances[ticker])
                    new_balances["USDT"] = [value, value]

            self.balancesListWidget.clear()
            self.balancesListWidget.addItem(f"{'COIN':<8} {'VALUE':<8} {'AMOUNT':<8}")

            for key, value in new_balances.items():
                self.balancesListWidget.addItem(
                    f"{key + ':':<8}{str(round(value[0], 2)) + '$':<13}{str(round(value[1], 2)):<8}")

        except:
            self.warn("An error occurred.")

    def query_orders(self):
        try:
            response = binance_api.query_orders(self.api_secret, self.api_key)

            content = str(response.content)[2:-1]
            order_list = json.loads(content)

            self.ordersListWidget.clear()
            self.ordersListWidget.addItem(f"{'PAIR':<8} {'PRICE':<8} {'AMOUNT':<8}")

            for idx, order in enumerate(order_list):
                order_id = order["orderId"]
                symbol = str(order['symbol'])
                coin = str(order['symbol']).replace('USDT', '')
                side = str(order["side"])
                price = format(float(order["price"]), 'g')
                amount = format(float(order["origQty"]), 'g')
                order_string = f"{coin:<8} {price:<8} {amount:<8}"

                item = QListWidgetItem(order_string)
                item.setForeground(QtGui.QColor("green" if side == "BUY" else "red"))

                self.ordersListWidget.addItem(item)
                self.orders_dict[str(idx)] = {"order_id": order_id, "symbol": symbol, "price": price, "side": side,
                                              "amount": amount}

        except:
            pass
            #self.warn(response)

    def initialize(self):
        global trade_alarms, alarm_parameters, available_pairs, track_list

        try:
            with open('conf.json', 'r') as json_file:
                self.configuration = json.load(json_file)

            track_list = self.configuration['tracks']
            self.api_key = self.configuration['api_key']
            self.api_secret = self.configuration['api_secret']
            self.alarm_duration = self.configuration['alarm_duration']
            self.alarm_sound = self.configuration['alarm_sound']
            self.is_mute = self.configuration['is_mute']
            alarm_parameters = {"alarm_duration": self.alarm_duration,
                                "alarm_sound": self.alarm_sound,
                                "is_mute": self.is_mute}

            self.apiKeyLineEdit.setText(self.api_key)
            self.apiSecretLineEdit.setText(self.api_secret)
            self.alarmDurationComboBox.setCurrentIndex(self.alarm_duration - 1)
            self.alarmSoundSlider.setValue(self.alarm_sound)
            self.muteCheckBox.setChecked(self.is_mute)

            for alarm_id, alarm_info in self.configuration['alarms'].items():
                symbol = "▲" if alarm_info['direction'] == "Rises above" else "▼"
                self.tradeAlarmsListWidget.addItem(f"{alarm_info['pair']} | {alarm_info['price']} | {symbol}")
                trade_alarms[alarm_id] = alarm_info

            for ticker in track_list:
                self.trackListListWidget.addItem(f"{ticker} | ")

        except:
            pass
            self.api_key = self.configuration['api_key'] = ""
            self.api_secret = self.configuration['api_secret'] = ""
            self.alarm_duration = self.configuration['alarm_duration'] = 3
            self.alarm_sound = self.configuration['alarm_sound'] = 30
            self.is_mute = self.configuration['is_mute'] = False
            alarm_parameters = {"alarm_duration": self.alarm_duration,
                                "alarm_sound": self.alarm_sound,
                                "is_mute": self.is_mute}

            with open('conf.json', 'w') as save_file:
                json.dump(self.configuration, save_file, indent=4)

        self.get_klines()

        self.alarm_thread = QThread()
        self.alarm_worker = Worker()
        self.alarm_worker.alarm_completed.connect(self.alarm)
        self.alarm_worker.moveToThread(self.alarm_thread)
        self.alarm_worker.alarm_requested.connect(self.alarm_worker.activate_alarms)
        self.alarm_worker.alarm_requested.emit(1)
        self.alarm_thread.start()

        self.track_thread = QThread()
        self.track_worker = Worker()
        self.track_worker.track_completed.connect(self.track)
        self.track_worker.moveToThread(self.track_thread)
        self.track_worker.track_requested.connect(self.track_worker.track)
        self.track_worker.track_requested.emit(1)
        self.track_thread.start()

    def alarm(self, price, alarm_value, direction):
        try:
            mod = 0 if alarm_value["direction"] == "Rises above" else 1
            symbol = "▲" if alarm_value["direction"] == "Rises above" else "▼"

            if alarm_value["is_trade"]:
                self.tradeAlarmsListWidget.setCurrentRow(alarm_value["row_id"])
                self.tradeAlarmsListWidget.currentItem().setText(
                    f"{alarm_value['pair']} | {str(alarm_value['price'])} | {symbol} | {price}")
            else:
                self.activeAlarmsListWidget.setCurrentRow(alarm_value["row_id"])
                self.activeAlarmsListWidget.currentItem().setText(
                    f"{alarm_value['pair']} | {str(alarm_value['price'])} | {symbol} | {price}")

        except Exception as e:
            pass

    def track(self, track_dict):
        self.trackListListWidget.clear()

        try:
            for ticker, price in track_dict.items():
                percentage_change = ((float(price) - available_pairs[ticker]) / available_pairs[ticker]) * 100
                item = QListWidgetItem(f"{ticker:<10} {price.rstrip('0'):<10} {percentage_change:.2f}%")
                item.setForeground(QtGui.QColor("green" if percentage_change >= 0 else "red"))
                self.trackListListWidget.addItem(item)

        except:
            pass

    def save_settings(self):
        try:
            self.configuration['api_key'] = self.api_key = self.apiKeyLineEdit.text()
            self.configuration['api_secret'] = self.api_secret = self.apiSecretLineEdit.text()
            self.configuration['alarm_duration'] = self.alarm_duration = int(self.alarmDurationComboBox.currentText())
            self.configuration['alarm_sound'] = self.alarm_sound = self.alarmSoundSlider.value()
            self.configuration['is_mute'] = self.is_mute = self.muteCheckBox.isChecked()
            alarm_parameters = {"alarm_duration": self.alarm_duration,
                                "alarm_sound": self.alarm_sound,
                                "is_mute": self.is_mute}

            with open('conf.json', 'w') as json_file:
                json.dump(self.configuration, json_file, indent=4)

        except Exception as e:
            self.warn("An error occurred while saving the settings.")

    def open_settings_menu(self):
        self.stackedWidget.setCurrentIndex(1 - (self.stackedWidget.currentIndex()))

    def mute(self):
        alarm_parameters["is_mute"] = bool(1 - int(alarm_parameters["is_mute"]))
        self.is_mute = alarm_parameters["is_mute"]

    def arange_alarm_dict(self, alarm_dict):
        temp_dict = dict()
        for id, (key, value) in enumerate(alarm_dict.items()):
            value["row_id"] = id
            temp_dict[str(id)] = value

        return temp_dict

    def add_track(self):
        try:
            pair = self.trackCoinLineEdit.text().upper() + "USDT"

            if pair in available_pairs.keys() and pair not in track_list:
                track_list.append(self.trackCoinLineEdit.text().upper() + "USDT")
                self.get_klines()
                self.trackCoinLineEdit.clear()
            else:
                self.warn("Pair is not available or already in the list.")
        except:
            pass

    def delete_track(self):
        track_list.pop(self.trackListListWidget.currentRow())
        self.trackListListWidget.takeItem(self.trackListListWidget.currentRow())
        self.trackListListWidget.setCurrentRow(-1)

    def start_stop_tracking(self):
        global is_track
        is_track = not is_track

    def get_klines(self):
        response = req.get("https://api.binance.com/api/v3/ticker/price").json()
        for ticker in response:
            available_pairs[ticker['symbol']] = 0

        params = {
            "symbols": str(track_list).replace("'", '"').replace(" ", ""),
            "timeZone": 0
        }

        response = req.get("https://api.binance.com/api/v3/ticker/tradingDay", params=params).json()

        try:
            try:
                for symbol in response:
                    available_pairs[symbol["symbol"]] = float(symbol['openPrice'])
            except:
                pass
        except:
            pass

    def warn(self, warning):
        msgBox = QMessageBox()
        msgBox.setWindowTitle("Warning")
        msgBox.setText(warning)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()

    def closeEvent(self, event):
        global trade_alarms

        temp_dict = dict()
        for id, (key, value) in enumerate(trade_alarms.items()):
            value["row_id"] = id
            temp_dict[str(id)] = value
        self.configuration["alarms"] = temp_dict

        temp_list = list()
        for id, value in enumerate(track_list):
            temp_list.append(value)
        self.configuration["tracks"] = temp_list

        with open("conf.json", "w") as save_file:
            json.dump(self.configuration, save_file, indent=4)

    def changeEvent(self, event):
        global is_track

        if event.type() == QEvent.WindowStateChange:
            if event.oldState() and Qt.WindowMinimized:
                is_track = True
            elif event.oldState() == Qt.WindowNoState or self.windowState() == Qt.WindowMaximized:
                is_track = False

if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet("""
            QMessageBox {
                background-color: #f0f0f0;
                font-size: 14px;
                color: #333;
            }

            QMessageBox QLabel {
                color: #0066cc;
                font-weight: bold;
            }

            QMessageBox QPushButton {
                background-color: #0066cc;
                color: white;
                border-radius: 10px;
                padding: 5px 10px;
                font-size: 12px;
            }

            QMessageBox QPushButton:hover {
                background-color: #0044cc;
            }

    		QListWidget {
    			border: 1px solid white;
    			color: white;
    			font-family: Arial; font-size: 15pt; 
    		}

    		QScrollBar {
    		    width: 8px;
    		    background-color: black;
    		}

    		QScrollBar::sub-page {
    		    background-color: black;
    		}

    		QScrollBar::add-page {
    		    background-color: black;
    		}

    		QScrollBar::handle {
    		    background-color: gray;
    		}

    		QTabWidget {
    			background-color: rgb(20,30,40); 
    		}

    		QTabWidget:pane {
    		    border: 1px solid gray;
    		}

    		QTabBar::tab {
    		    background-color: rgb(50,100,130);
    		    width: 100px;
    		    height: 30px;
    		    border: 2px solid rgb(20,30,40);
    		    font: 18px;
    		    margin-left: 5px
    		}

    		QTabBar::tab:selected {
    		  	background: rgb(245, 245, 245);
    		  	padding-bottom: -2px;
    		}
    		""")

    MainWindow = MyMainWindow()
    MainWindow.show()
    sys.exit(app.exec_())
