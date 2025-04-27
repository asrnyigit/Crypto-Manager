import time, winsound, json, math, ast
import requests as req
import pandas as pd
from dataclasses import dataclass, asdict
from readerwriterlock import rwlock

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtWidgets import QListWidgetItem, QMessageBox, QMenu
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, QEvent, Qt

import gui
import binance_api

lock = rwlock.RWLockFair()

@dataclass
class Alarm:
    list_id: int
    coin: str
    pair: str
    price: float
    type: str
    direction: str

@dataclass
class Order:
    order_id: int
    symbol: str
    coin: str
    side: str
    price: float
    quantity: str

class AlarmThread(QThread):
    alarm_completed = pyqtSignal(float, pd.core.series.Series)

    def __init__(self):
        super().__init__()
        self._is_running = True

    def set_data(self, alarms):
        with lock.gen_rlock():
            self.alarms = alarms.copy()

    def run(self):
        while self._is_running:
            try:
                tickers = self.alarms['pair'].values
            except Exception as e:
                print(f"Error gathering tickers: {e}")
                time.sleep(3)
                continue

            try:
                response = binance_api.query_price_all().json()
                all_ticker_prices = {
                    item['symbol']: item['price']
                    for item in response if item['symbol'] in tickers
                }
            except Exception as e:
                print(f"Error fetching prices: {e}")
                time.sleep(3)
                continue

            alarm_mode = -1
            for i, row in enumerate(self.alarms.iterrows()):
                row = row[1]
                try:
                    price = float(all_ticker_prices[row["pair"]])
                    target = float(row["price"])

                    if row["direction"] == "Rises above" and target <= price:
                        self.alarm_completed.emit(price, self.alarms.iloc[i])
                        if (alarm_mode in [-1, 0]):
                            alarm_mode = 0
                        else:
                            alarm_mode = 2

                    elif row["direction"] == "Drops below" and target >= price:
                        self.alarm_completed.emit(price, self.alarms.iloc[i])
                        if (alarm_mode in [-1, 1]):
                            alarm_mode = 1
                        else:
                            alarm_mode = 2
                except Exception as e:
                    print(f"Error processing alarm: {e}")

            self.alarm(alarm_mode)
            time.sleep(3)

    def stop(self):
        self._is_running = False
        self.wait()

    def alarm(self, mode):
        for j in range(1, 3):
            for i in range(1, 5):
                if mode == 0:
                    winsound.Beep(i * 100, 200)
                elif mode == 1:
                    winsound.Beep(i * 140, 300)
                elif mode == 2:
                    winsound.Beep(i * 160, 200)

class TrackThread(QThread):
    track_completed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._is_running = True

    def set_data(self, track_list):
        with lock.gen_rlock():
            self.track_list = track_list.copy()

    def run(self):
        while self._is_running:
            try:
                response = binance_api.query_price_all().json()
                track_dict = {item['symbol']: item['price'] for item in response if item['symbol'] in self.track_list}

                self.track_completed.emit(track_dict)
            except Exception as e:
                print(f"Error in track: {e}")

            time.sleep(2)

    def stop(self):
        self._is_running = False
        self.wait()

class MyMainWindow(QtWidgets.QMainWindow, gui.Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.orders_dict = dict()
        self.configuration = dict()
        self.is_track = True

        self.available_pairs = dict()

        self.alarms = pd.DataFrame(columns=["list_id", "coin", "pair", "price", "type", "direction"])

        self.setupUi(self)
        self.initialize()

    def open_temporary_alarms_context_menu(self, position):
        try:
            item = self.activeAlarmsListWidget.itemAt(position)
            if item is not None:
                menu = QMenu()
                delete_action = menu.addAction("Delete")
                action = menu.exec_(self.activeAlarmsListWidget.mapToGlobal(position))
                if action == delete_action:
                    row = self.activeAlarmsListWidget.row(item)
                    self.activeAlarmsListWidget.takeItem(row)

                    self.alarms = self.alarms.query(f"not (list_id == {row} and type == 'temporary')")
                    mask = self.alarms['type'] == 'temporary'
                    self.alarms.loc[mask, 'list_id'] = range(mask.sum())
                    self.alarm_thread.set_data(self.alarms)

        except Exception as e:
            self.warn("An error occurred while deleting the alarm.")

    def open_permanent_alarms_context_menu(self, position):
        try:
            item = self.tradeAlarmsListWidget.itemAt(position)
            if item is not None:
                menu = QMenu()
                delete_action = menu.addAction("Delete")
                action = menu.exec_(self.tradeAlarmsListWidget.mapToGlobal(position))
                if action == delete_action:
                    row = self.tradeAlarmsListWidget.row(item)
                    self.tradeAlarmsListWidget.takeItem(row)

                    self.alarms = self.alarms.query(f"not (list_id == {row} and type == 'permanent')")
                    mask = self.alarms['type'] == 'permanent'
                    self.alarms.loc[mask, 'list_id'] = range(mask.sum())
                    self.alarm_thread.set_data(self.alarms)

        except Exception as e:
            self.warn("An error occurred while deleting the alarm.")

    def custom_round(self, value):
        if abs(value) >= 1:
            return round(value, 2)
        else:
            if value == 0:
                return 0
            else:
                return round(value, 4 - int(math.floor(math.log10(abs(value)))) - 1)

    def create_and_append_alarm_string(self, alarm):
        symbol = "▲" if alarm.direction == "Rises above" else "▼"
        alarm_string = f"{alarm.pair} | {alarm.price} | {symbol}"

        if alarm.type == "temporary":
            self.activeAlarmsListWidget.addItem(alarm_string)
        elif alarm.type == "permanent":
            self.tradeAlarmsListWidget.addItem(alarm_string)

    def add_alarm(self):
        try:
            coin = self.alarmCoinLineEdit.text()
            pair = coin.upper() + "USDT"
            price = 0 if self.priceLineEdit.text() == "" else float(self.priceLineEdit.text())
            price_range = 0 if self.rangeLineEdit.text() == "" else float(self.rangeLineEdit.text())
            is_range = self.rangeCheckBox.isChecked()
            is_trade = self.tradeCheckBox.isChecked()
            direction = self.alarmComboBox.currentText()
            _type = "permanent" if is_trade else "temporary"
            symbol = "▲" if direction == "Rises above" else "▼"
            list_id = len(self.alarms[self.alarms["type"] == _type])

            if is_range and price_range != 0:
                current_price = req.get(
                    f'https://api.binance.com/api/v3/ticker/price?symbol={pair}').json()
                current_price = float(current_price['price'])

                upper_price = self.custom_round(current_price * (1 + price_range / 100))
                alarm = Alarm(list_id, coin, pair, price, _type, 'Rises above')
                self.alarms = pd.concat([self.alarms, pd.DataFrame([asdict(alarm)])], ignore_index=True)
                self.create_and_append_alarm_string(alarm)

                lower_price = self.custom_round(current_price * (1 - price_range / 100))
                alarm = Alarm(list_id, coin, pair, price, _type, 'Drops below')
                self.alarms = pd.concat([self.alarms, pd.DataFrame([asdict(alarm)])], ignore_index=True)
                self.create_and_append_alarm_string(alarm)

            else:
                alarm = Alarm(list_id, coin, pair, price, _type, direction)
                self.alarms = pd.concat([self.alarms, pd.DataFrame([asdict(alarm)])], ignore_index=True)
                self.create_and_append_alarm_string(alarm)

            self.alarm_thread.set_data(self.alarms)

        except Exception as e:
            self.warn("An error occurred while creating the alarm.")

    def set_order(self, symbol, side, _type, price, amount):
        try:
            response = binance_api.set_order(symbol, side, _type, price, amount, self.api_params).json()

            if 'msg' in response.keys():
                self.warn(response['msg'])

        except Exception as e:
            self.warn("Invalid or missing parameters.")

    def cancel_order(self):
        try:
            symbol = self.orders_dict[str(self.ordersListWidget.currentRow() - 1)]["symbol"]
            order_id = self.orders_dict[str(self.ordersListWidget.currentRow() - 1)]["order_id"]

            response = binance_api.cancel_order(symbol, order_id, self.api_params)

            time.sleep(1)
            self.query_orders()

        except:
            self.warn(response['msg'])

    def query_price(self, pair, _id):
        try:
            response = binance_api.query_price(pair).json()

            if _id == 0:
                self.retrievedPriceLabel.setText(response['price'].strip(" "))
            elif _id == 1:
                self.retrievedPriceLabel2.setText(response['price'].strip(" "))
        except:
            self.warn("An error occurred while querying the price.")

    def query_balances(self):
        try:
            response = binance_api.query_balances(self.api_params)
            balances_dict = response.json()
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
            self.balancesListWidget.addItem(f"{'COIN':<8} {'VALUE':<8} {'AMOUNT':<8} {'DAILY CHANGE':<15}")

            for key, value in new_balances.items():
                try:
                    current_value = round(value[0], 2)
                    amount = round(value[1], 2)
                    open_price = self.available_pairs[key+"USDT"]["openPrice"]
                    change = round(current_value - open_price * amount, 2)

                    item = QListWidgetItem(f"{key + ':':<8}{str(current_value) + '$':<13}{str(amount):<13}{str(change):<13}")
                    item.setForeground(QtGui.QColor("green" if change > 0 else "red"))

                    self.balancesListWidget.addItem(item)

                except:
                    if key == "USDT":
                        self.balancesListWidget.addItem(
                            f"{key + ':':<8}{str(round(value[0], 2)) + '$':<13}{str(round(value[1], 2)):<13}")

        except:
            self.warn("An error occurred while querying the wallet balances.")

    def query_orders(self):
        try:
            response = binance_api.query_orders(self.api_params)
            orders = response.json()

            self.ordersListWidget.clear()
            self.ordersListWidget.addItem(f"{'PAIR':<8} {'PRICE':<8} {'AMOUNT':<8}")

            for idx, item in enumerate(orders):
                order = Order(item["orderId"],
                              str(item['symbol']),
                              str(item['symbol']).replace('USDT', ''),
                              str(item["side"]),
                              format(float(item["price"]), 'g'),
                              format(float(item["origQty"]), 'g'))

                order_string = f"{order.coin:<8} {order.price:<8} {order.quantity:<8}"

                listwidgetitem = QListWidgetItem(order_string)
                listwidgetitem.setForeground(QtGui.QColor("green" if order.side == "BUY" else "red"))

                self.ordersListWidget.addItem(listwidgetitem)
                self.orders_dict[idx] = order

        except Exception as e:
            self.warn("An error occurred while querying the account's orders.")

    def initialize(self):
        try:
            with open('conf2.json', 'r') as json_file:
                self.configuration = json.load(json_file)

            self.alarms = pd.DataFrame(self.configuration['alarms'])
            self.track_list = self.configuration['track_list']
            self.api_params = self.configuration['api_params']
            self.alarm_params = self.configuration['alarm_params']

            self.apiKeyLineEdit.setText(self.api_params['api_key'])
            self.apiSecretLineEdit.setText(self.api_params['api_secret'])
            self.alarmDurationComboBox.setCurrentIndex(self.alarm_params['alarm_duration'] - 1)
            self.alarmSoundSlider.setValue(self.alarm_params['alarm_volume'])
            self.muteCheckBox.setChecked(self.alarm_params['is_mute'])

            for row in self.alarms.iterrows():
                row = row[1]
                self.create_and_append_alarm_string(row)

            for ticker in self.track_list:
                self.trackListListWidget.addItem(f"{ticker} | ")

        except Exception as e:
            self.api_params = self.configuration['api_params'] = {'api_key': "",
                                                                  'api_secret': ""}
            self.alarm_params = self.configuration['alarm_params'] = {'alarm_duration': 3,
                                                                      'alarm_volume': 30,
                                                                      'is_mute': False}
            self.save()

        self.get_klines()

        self.alarm_thread = AlarmThread()
        self.track_thread = TrackThread()

        self.alarm_thread.alarm_completed.connect(self.alarm)
        self.track_thread.track_completed.connect(self.track)

        self.alarm_thread.set_data(self.alarms)
        self.track_thread.set_data(self.track_list)

        self.alarm_thread.start()
        self.track_thread.start()

    def stop_threads(self):
        self.alarm_thread.stop()
        self.track_thread.stop()

    def alarm(self, price, alarm):
        try:
            symbol = "▲" if alarm["direction"] == "Rises above" else "▼"

            if alarm["type"] == "permanent":
                self.tradeAlarmsListWidget.setCurrentRow(alarm['list_id'])
                self.tradeAlarmsListWidget.currentItem().setText(
                    f"{alarm['pair']} | {str(alarm['price'])} | {symbol} | {price}")
            else:
                self.activeAlarmsListWidget.setCurrentRow(alarm['list_id'])
                self.activeAlarmsListWidget.currentItem().setText(
                    f"{alarm['pair']} | {str(alarm['price'])} | {symbol} | {price}")

        except Exception as e:
            self.warn("An error occurred while alarming.")

    def track(self, track_dict):
        self.trackListListWidget.clear()
        self.trackListListWidget.addItem(f"{'COIN':<10} {'PRICE':<10} {'PRC CHANGE':<15} {'LOW PRICE':<15} {'OPEN PRICE':<15} {'HIGH PRICE':<15}")

        for ticker, price in track_dict.items():
            try:
                percentage_change = ((float(price) - self.available_pairs[ticker]["openPrice"]) / self.available_pairs[ticker]["openPrice"]) * 100
                item = QListWidgetItem(f"{ticker:<10} {price.rstrip('0'):<10} {percentage_change:.2f}%   ---   {self.available_pairs[ticker]['lowPrice']:<10} {self.available_pairs[ticker]['openPrice']:<10} {self.available_pairs[ticker]['highPrice']:<10}")
                item.setForeground(QtGui.QColor("green" if percentage_change >= 0 else "red"))
                self.trackListListWidget.addItem(item)

            except Exception as e:
                pass

    def save_settings(self):
        try:
            self.configuration['api_params'] = self.api_params = {'api_key': self.apiKeyLineEdit.text(),
                                                                'api_secret': self.apiSecretLineEdit.text()}

            self.configuration['alarm_params'] = self.alarm_params = {'alarm_duration': int(self.alarmDurationComboBox.currentText()),
                                                                    'alarm_volume': self.alarmSoundSlider.value(),
                                                                    'is_mute': self.muteCheckBox.isChecked()}

            with open('conf2.json', 'w') as json_file:
                json.dump(self.configuration, json_file, indent=4)

        except Exception as e:
            self.warn("An error occurred while saving the settings.")

    def open_settings_menu(self):
        self.stackedWidget.setCurrentIndex(1 - (self.stackedWidget.currentIndex()))

    def mute(self):
        self.alarm_params["is_mute"] = not self.alarm_params["is_mute"]

    def add_track(self):
        try:
            pair = self.trackCoinLineEdit.text().upper() + "USDT"

            if pair in self.available_pairs.keys() and pair not in self.track_list:
                self.track_list.append(self.trackCoinLineEdit.text().upper() + "USDT")
                self.get_klines()
                self.trackCoinLineEdit.clear()
            else:
                self.warn("Pair is either not available or already in the track list.")

        except Exception as e:
            self.warn("An error occurred while adding the coin to the track list.")

    def delete_track(self):
        self.track_list.pop(self.trackListListWidget.currentRow())
        self.trackListListWidget.takeItem(self.trackListListWidget.currentRow())
        self.trackListListWidget.setCurrentRow(-1)

    def start_stop_tracking(self):
        self.is_track = not self.is_track

    def get_klines(self):
        response = req.get("https://api.binance.com/api/v3/ticker/price").json()

        for ticker in response:
            self.available_pairs[ticker['symbol']] = 0

        params = {
            "symbols": str(self.track_list).replace("'", '"').replace(" ", ""),
            "timeZone": 0
        }

        response = req.get("https://api.binance.com/api/v3/ticker/tradingDay", params=params).json()

        for symbol in response:
            try:
                self.available_pairs[symbol["symbol"]] = {"openPrice": float(symbol['openPrice']),
                                                    "highPrice": float(symbol['highPrice']),
                                                    "lowPrice": float(symbol['lowPrice']),
                                                    "priceChange": float(symbol['priceChange'])}
            except Exception as e:
                pass

    def warn(self, warning):
        msgBox = QMessageBox()
        msgBox.setWindowTitle("Warning")
        msgBox.setText(warning)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()

    def save(self):
        try:
            self.configuration['alarms'] = self.alarms.loc[self.alarms['type']=='permanent'].to_dict(orient="records")
            self.configuration['track_list'] = self.track_list

            with open("conf2.json", "w") as save_file:
                json.dump(self.configuration, save_file, indent=4)

        except Exception as e:
            self.warn("An error occurred while saving the configurations.")

    def closeEvent(self, event):
        self.save()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if event.oldState() and Qt.WindowMinimized:
                self.is_track = True
            elif event.oldState() == Qt.WindowNoState or self.windowState() == Qt.WindowMaximized:
                self.is_track = False

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
