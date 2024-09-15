import sys, os, time, cv2, datetime, math, threading, winsound, tweepy, json, hashlib, hmac, ast
import numpy as np
import requests as req
from bs4 import BeautifulSoup
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QListWidgetItem, QMainWindow, QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, Qt, QEvent

lock = threading.Lock()

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
        global alarm_parameters, alarm_list, lock

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
                ticker_prices = dict()
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

            except Exception as e:
                pass

            time.sleep(3)

    @pyqtSlot(int)
    def track(self, n):
        global track_list, is_track

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
        global alarm_parameters

        if not alarm_parameters["is_mute"]:
            for j in range(1, alarm_parameters["alarm_duration"]):
                for i in range(1, 5):
                    if mod == 0:
                        winsound.Beep(i * 100, 200)
                    elif mod == 1:
                        winsound.Beep(i * 140, 300)
                    else:
                        winsound.Beep(i * 160, 200)

class Ui_MainWindow(object):

    def changeEvent(self, event):
        global is_track
        if event.type() == QEvent.WindowStateChange:
            if event.oldState() and Qt.WindowMinimized:
                is_track = True
            elif event.oldState() == Qt.WindowNoState or self.windowState() == Qt.WindowMaximized:
                is_track = False
    
    def setupUi(self, MainWindow):
        self.alarm_actions = ["Delete"]
        self.orders_dict = dict()
        self.configuration = dict()
        self.latest_right_click = -1
        self.current_row = -1
        self.is_tracking = 0

        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(571, 645)
        MainWindow.setMinimumSize(QtCore.QSize(0, 645))
        font = QtGui.QFont()
        font.setBold(False)
        font.setWeight(50)
        MainWindow.setFont(font)
        MainWindow.setStyleSheet("background-color: rgb(20,30,40);")

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_5.setContentsMargins(5, 5, 5, 5)
        self.verticalLayout_5.setSpacing(5)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.stackedWidget = QtWidgets.QStackedWidget(self.centralwidget)
        self.stackedWidget.setObjectName("stackedWidget")
        self.mainPage = QtWidgets.QWidget()
        self.mainPage.setMinimumSize(QtCore.QSize(0, 600))
        self.mainPage.setObjectName("mainPage")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.mainPage)
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_6.setSpacing(0)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.mainPageVerticalLayout = QtWidgets.QVBoxLayout()
        self.mainPageVerticalLayout.setObjectName("mainPageVerticalLayout")
        self.tabWidget = QtWidgets.QTabWidget(self.mainPage)
        self.tabWidget.setObjectName("tabWidget")
        self.alarmsTab = QtWidgets.QWidget()
        self.alarmsTab.setObjectName("alarmsTab")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.alarmsTab)
        self.horizontalLayout_2.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout_2.setSpacing(3)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.alarmLeftVerticalLayout = QtWidgets.QVBoxLayout()
        self.alarmLeftVerticalLayout.setContentsMargins(2, 2, 2, 2)
        self.alarmLeftVerticalLayout.setSpacing(6)
        self.alarmLeftVerticalLayout.setObjectName("alarmLeftVerticalLayout")
        self.activeAlarmsLabel = QtWidgets.QLabel(self.alarmsTab)
        self.activeAlarmsLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.activeAlarmsLabel.setFont(font)
        self.activeAlarmsLabel.setStyleSheet("\n"
                                             "padding: 5px 0px 5px 0px;\n"
                                             "color: white;")
        self.activeAlarmsLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.activeAlarmsLabel.setObjectName("activeAlarmsLabel")
        self.alarmLeftVerticalLayout.addWidget(self.activeAlarmsLabel)
        self.activeAlarmsListWidget = QtWidgets.QListWidget(self.alarmsTab)
        self.activeAlarmsListWidget.setMinimumSize(QtCore.QSize(330, 230))
        self.activeAlarmsListWidget.setGridSize(QtCore.QSize(0, 30))
        self.activeAlarmsListWidget.setItemAlignment(QtCore.Qt.AlignLeading)
        self.activeAlarmsListWidget.mousePressEvent = self.activeAlarmsMousePressEvent
        self.activeAlarmsListWidget.setObjectName("activeAlarmsListWidget")
        self.alarmLeftVerticalLayout.addWidget(self.activeAlarmsListWidget)

        self.alarmsHorizontalLine = QtWidgets.QFrame(self.alarmsTab)
        self.alarmsHorizontalLine.setStyleSheet("background-color: black;")
        self.alarmsHorizontalLine.setFrameShape(QtWidgets.QFrame.HLine)
        self.alarmsHorizontalLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.alarmsHorizontalLine.setObjectName("alarmsHorizontalLine")
        self.alarmLeftVerticalLayout.addWidget(self.alarmsHorizontalLine)
        self.tradeAlarmsLabel = QtWidgets.QLabel(self.alarmsTab)
        self.tradeAlarmsLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.tradeAlarmsLabel.setFont(font)
        self.tradeAlarmsLabel.setStyleSheet("\n"
                                            "padding: 5px 0px 5px 0px;\n"
                                            "color: white;")
        self.tradeAlarmsLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.tradeAlarmsLabel.setObjectName("tradeAlarmsLabel")
        self.alarmLeftVerticalLayout.addWidget(self.tradeAlarmsLabel)

        self.tradeAlarmsListWidget = QtWidgets.QListWidget(self.alarmsTab)
        self.tradeAlarmsListWidget.setMinimumSize(QtCore.QSize(330, 230))
        self.tradeAlarmsListWidget.setGridSize(QtCore.QSize(0, 30))
        self.tradeAlarmsListWidget.setItemAlignment(QtCore.Qt.AlignLeading)
        self.tradeAlarmsListWidget.mousePressEvent = self.tradeAlarmsMousePressEvent
        self.tradeAlarmsListWidget.setObjectName("tradeAlarmsListWidget")
        self.alarmLeftVerticalLayout.addWidget(self.tradeAlarmsListWidget)

        self.horizontalLayout_2.addLayout(self.alarmLeftVerticalLayout)
        self.alarmsVerticalLine = QtWidgets.QFrame(self.alarmsTab)
        self.alarmsVerticalLine.setStyleSheet("background-color: black;")
        self.alarmsVerticalLine.setFrameShape(QtWidgets.QFrame.VLine)
        self.alarmsVerticalLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.alarmsVerticalLine.setObjectName("alarmsVerticalLine")
        self.horizontalLayout_2.addWidget(self.alarmsVerticalLine)
        self.alarmRightVerticalLayout = QtWidgets.QVBoxLayout()
        self.alarmRightVerticalLayout.setContentsMargins(2, 2, 2, 2)
        self.alarmRightVerticalLayout.setSpacing(10)
        self.alarmRightVerticalLayout.setObjectName("alarmRightVerticalLayout")
        self.addAlarmLabel = QtWidgets.QLabel(self.alarmsTab)
        self.addAlarmLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.addAlarmLabel.setFont(font)
        self.addAlarmLabel.setStyleSheet("\n"
                                         "padding: 5px 0px 5px 0px;\n"
                                         "color: white;")
        self.addAlarmLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.addAlarmLabel.setObjectName("addAlarmLabel")
        self.alarmRightVerticalLayout.addWidget(self.addAlarmLabel)
        self.alarmGridLayout = QtWidgets.QGridLayout()
        self.alarmGridLayout.setContentsMargins(-1, 10, -1, 10)
        self.alarmGridLayout.setSpacing(10)
        self.alarmGridLayout.setObjectName("alarmGridLayout")

        self.rangeLineEdit = QtWidgets.QLineEdit(self.alarmsTab)
        self.rangeLineEdit.setMinimumSize(QtCore.QSize(110, 25))
        self.rangeLineEdit.setStyleSheet("border: 1px solid white; height: 25px; color: white;")
        self.rangeLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.rangeLineEdit.setObjectName("rangeLineEdit")
        self.alarmGridLayout.addWidget(self.rangeLineEdit, 2, 1, 1, 1)

        self.alarmCoinLineEdit = QtWidgets.QLineEdit(self.alarmsTab)
        self.alarmCoinLineEdit.setMinimumSize(QtCore.QSize(0, 25))
        self.alarmCoinLineEdit.setStyleSheet("border: 1px solid white; height: 25px; color: white;")
        self.alarmCoinLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.alarmCoinLineEdit.setObjectName("alarmCoinLineEdit")
        self.alarmGridLayout.addWidget(self.alarmCoinLineEdit, 0, 1, 1, 1)

        self.alarmCoinLabel = QtWidgets.QLabel(self.alarmsTab)
        self.alarmCoinLabel.setMinimumSize(QtCore.QSize(80, 25))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        self.alarmCoinLabel.setFont(font)
        self.alarmCoinLabel.setStyleSheet("color: white; background-color: rgb(50,100,130);")
        self.alarmCoinLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.alarmCoinLabel.setObjectName("alarmCoinLabel")
        self.alarmGridLayout.addWidget(self.alarmCoinLabel, 0, 0, 1, 1)

        self.priceLineEdit = QtWidgets.QLineEdit(self.alarmsTab)
        self.priceLineEdit.setMinimumSize(QtCore.QSize(0, 25))
        self.priceLineEdit.setObjectName("priceLineEdit")
        self.priceLineEdit.setStyleSheet("border: 1px solid white; height: 25px; color: white;")
        self.priceLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.alarmGridLayout.addWidget(self.priceLineEdit, 1, 1, 1, 1)

        self.priceLabel = QtWidgets.QLabel(self.alarmsTab)
        self.priceLabel.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        self.priceLabel.setFont(font)
        self.priceLabel.setStyleSheet("color: white; background-color: rgb(50,100,130);")
        self.priceLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.priceLabel.setObjectName("priceLabel")
        self.alarmGridLayout.addWidget(self.priceLabel, 1, 0, 1, 1)
        self.rangeLabel = QtWidgets.QLabel(self.alarmsTab)
        self.rangeLabel.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        self.rangeLabel.setFont(font)
        self.rangeLabel.setStyleSheet("color: white; background-color: rgb(50,100,130);")
        self.rangeLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.rangeLabel.setObjectName("rangeLabel")
        self.alarmGridLayout.addWidget(self.rangeLabel, 2, 0, 1, 1)
        self.alarmGridLayout.setColumnStretch(0, 1)
        self.alarmGridLayout.setColumnStretch(1, 2)
        self.alarmRightVerticalLayout.addLayout(self.alarmGridLayout)
        self.alarmGridLayout2 = QtWidgets.QGridLayout()
        self.alarmGridLayout2.setObjectName("alarmGridLayout2")
        self.tradeCheckBox = QtWidgets.QCheckBox(self.alarmsTab)
        self.tradeCheckBox.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        self.tradeCheckBox.setFont(font)
        self.tradeCheckBox.setStyleSheet("color: white;")
        self.tradeCheckBox.setObjectName("tradeCheckBox")
        self.alarmGridLayout2.addWidget(self.tradeCheckBox, 1, 1, 1, 1)
        self.rangeCheckBox = QtWidgets.QCheckBox(self.alarmsTab)
        self.rangeCheckBox.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        self.rangeCheckBox.setFont(font)
        self.rangeCheckBox.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.rangeCheckBox.setStyleSheet("color: white;")
        self.rangeCheckBox.setObjectName("rangeCheckBox")
        self.alarmGridLayout2.addWidget(self.rangeCheckBox, 1, 0, 1, 1)
        self.alarmComboBox = QtWidgets.QComboBox(self.alarmsTab)
        self.alarmComboBox.setMinimumSize(QtCore.QSize(95, 25))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.alarmComboBox.setFont(font)
        self.alarmComboBox.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.alarmComboBox.setStyleSheet("color: white; border: 1px solid white;")
        self.alarmComboBox.setObjectName("alarmComboBox")
        self.alarmComboBox.addItem("")
        self.alarmComboBox.addItem("")
        self.alarmGridLayout2.addWidget(self.alarmComboBox, 2, 0, 1, 1)
        self.addAlarmButton = QtWidgets.QPushButton(self.alarmsTab)
        self.addAlarmButton.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(False)
        font.setWeight(50)
        self.addAlarmButton.setFont(font)
        self.addAlarmButton.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.addAlarmButton.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.addAlarmButton.setAcceptDrops(False)
        self.addAlarmButton.setStyleSheet("color: white;  background-color: rgb(100,30,40)")
        self.addAlarmButton.clicked.connect(lambda: self.add_alarm(self.tradeCheckBox.isChecked()))
        self.addAlarmButton.setObjectName("addAlarmButton")
        self.alarmGridLayout2.addWidget(self.addAlarmButton, 2, 1, 1, 1)
        self.alarmGridLayout2.setColumnStretch(0, 1)
        self.alarmGridLayout2.setColumnStretch(1, 1)
        self.alarmRightVerticalLayout.addLayout(self.alarmGridLayout2)
        self.alarmsHorizontalLine2 = QtWidgets.QFrame(self.alarmsTab)
        self.alarmsHorizontalLine2.setFrameShape(QtWidgets.QFrame.HLine)
        self.alarmsHorizontalLine2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.alarmsHorizontalLine2.setObjectName("alarmsHorizontalLine2")
        self.alarmRightVerticalLayout.addWidget(self.alarmsHorizontalLine2)
        self.priceQueryGridLayout = QtWidgets.QGridLayout()
        self.priceQueryGridLayout.setSpacing(10)
        self.priceQueryGridLayout.setObjectName("priceQueryGridLayout")
        self.coinDisplayLabel = QtWidgets.QLabel(self.alarmsTab)
        self.coinDisplayLabel.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        self.coinDisplayLabel.setFont(font)
        self.coinDisplayLabel.setStyleSheet("color: white; background-color: rgb(50,100,130);")
        self.coinDisplayLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.coinDisplayLabel.setObjectName("coinDisplayLabel")
        self.priceQueryGridLayout.addWidget(self.coinDisplayLabel, 0, 0, 1, 1)

        self.coinDisplayLineEdit = QtWidgets.QLineEdit(self.alarmsTab)
        self.coinDisplayLineEdit.setMinimumSize(QtCore.QSize(0, 25))
        self.coinDisplayLineEdit.setStyleSheet("border: 1px solid white; height: 25px; color: white;")
        self.coinDisplayLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.coinDisplayLineEdit.setObjectName("coinDisplayLineEdit")
        self.priceQueryGridLayout.addWidget(self.coinDisplayLineEdit, 0, 1, 1, 1)

        self.queryPriceButton = QtWidgets.QPushButton(self.alarmsTab)
        self.queryPriceButton.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(False)
        font.setWeight(50)
        self.queryPriceButton.setFont(font)
        self.queryPriceButton.setStyleSheet("color: white;  background-color: rgb(100,30,40)")
        self.queryPriceButton.setObjectName("queryPriceButton")
        self.queryPriceButton.clicked.connect(lambda: self.query_price(self.coinDisplayLineEdit.text(), 0))
        self.priceQueryGridLayout.addWidget(self.queryPriceButton, 1, 0, 1, 1)

        self.retrievedPriceLabel = QtWidgets.QLabel(self.alarmsTab)
        self.retrievedPriceLabel.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        self.retrievedPriceLabel.setFont(font)
        self.retrievedPriceLabel.setStyleSheet("color: white; border: 1px solid white;")
        self.retrievedPriceLabel.setText("")
        self.retrievedPriceLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.retrievedPriceLabel.setObjectName("retrievedPriceLabel")
        self.priceQueryGridLayout.addWidget(self.retrievedPriceLabel, 1, 1, 1, 1)
        self.priceQueryGridLayout.setColumnStretch(0, 1)
        self.priceQueryGridLayout.setColumnStretch(1, 2)
        self.alarmRightVerticalLayout.addLayout(self.priceQueryGridLayout)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.alarmRightVerticalLayout.addItem(spacerItem)
        self.horizontalLayout_2.addLayout(self.alarmRightVerticalLayout)
        self.horizontalLayout_2.setStretch(0, 1)
        self.tabWidget.addTab(self.alarmsTab, "")
        self.tradingTab = QtWidgets.QWidget()
        self.tradingTab.setObjectName("tradingTab")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.tradingTab)
        self.horizontalLayout_4.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout_4.setSpacing(3)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.tradingLeftVerticalLayout = QtWidgets.QVBoxLayout()
        self.tradingLeftVerticalLayout.setContentsMargins(2, 2, 2, 2)
        self.tradingLeftVerticalLayout.setSpacing(10)
        self.tradingLeftVerticalLayout.setObjectName("tradingLeftVerticalLayout")
        self.walletHorizontal = QtWidgets.QHBoxLayout()
        self.walletHorizontal.setObjectName("walletHorizontal")
        spacerItem1 = QtWidgets.QSpacerItem(25, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.walletHorizontal.addItem(spacerItem1)
        self.walletLabel = QtWidgets.QLabel(self.tradingTab)
        self.walletLabel.setMinimumSize(QtCore.QSize(70, 28))
        self.walletLabel.setMaximumSize(QtCore.QSize(55, 28))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.walletLabel.setFont(font)
        self.walletLabel.setStyleSheet("color: white;")
        self.walletLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.walletLabel.setObjectName("walletLabel")
        self.walletHorizontal.addWidget(self.walletLabel)
        self.refreshWalletButton = QtWidgets.QPushButton(self.tradingTab)
        self.refreshWalletButton.setMaximumSize(QtCore.QSize(20, 20))
        self.refreshWalletButton.setStyleSheet("border: none;")
        self.refreshWalletButton.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("./refresh.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.refreshWalletButton.setIcon(icon)
        self.refreshWalletButton.setIconSize(QtCore.QSize(25, 25))
        self.refreshWalletButton.setObjectName("refreshWalletButton")
        self.refreshWalletButton.clicked.connect(self.query_balances)
        self.walletHorizontal.addWidget(self.refreshWalletButton)

        spacerItem2 = QtWidgets.QSpacerItem(25, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.walletHorizontal.addItem(spacerItem2)
        self.walletHorizontal.setStretch(0, 1)
        self.walletHorizontal.setStretch(1, 1)
        self.walletHorizontal.setStretch(2, 1)
        self.walletHorizontal.setStretch(3, 1)
        self.tradingLeftVerticalLayout.addLayout(self.walletHorizontal)
        self.balancesListWidget = QtWidgets.QListWidget(self.tradingTab)
        self.balancesListWidget.setMaximumSize(QtCore.QSize(1900000, 16777215))
        self.balancesListWidget.setGridSize(QtCore.QSize(0, 30))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.balancesListWidget.setFont(font)
        self.balancesListWidget.setStyleSheet("color: white; border: 1px solid white;")
        self.balancesListWidget.setObjectName("balancesListWidget")
        self.tradingLeftVerticalLayout.addWidget(self.balancesListWidget)
        self.walletGridLayout = QtWidgets.QGridLayout()
        self.walletGridLayout.setSpacing(10)
        self.walletGridLayout.setObjectName("walletGridLayout")

        self.coinLineEdit = QtWidgets.QLineEdit(self.tradingTab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.coinLineEdit.sizePolicy().hasHeightForWidth())
        self.coinLineEdit.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.coinLineEdit.setFont(font)
        self.coinLineEdit.setStyleSheet("border: 1px solid white; height: 25px; color: white;")
        self.coinLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.coinLineEdit.setObjectName("coinLineEdit")
        self.walletGridLayout.addWidget(self.coinLineEdit, 0, 1, 1, 1)

        self.coinLabel = QtWidgets.QLabel(self.tradingTab)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.coinLabel.setFont(font)
        self.coinLabel.setStyleSheet("color: white; background-color: rgb(50,100,130);")
        self.coinLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.coinLabel.setObjectName("coinLabel")
        self.walletGridLayout.addWidget(self.coinLabel, 0, 0, 1, 1)
        self.tradingPriceLineEdit = QtWidgets.QLineEdit(self.tradingTab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tradingPriceLineEdit.sizePolicy().hasHeightForWidth())

        self.tradingPriceLineEdit.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.tradingPriceLineEdit.setFont(font)
        self.tradingPriceLineEdit.setStyleSheet("border: 1px solid white; height: 25px; color: white;")
        self.tradingPriceLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.tradingPriceLineEdit.setObjectName("tradingPriceLineEdit")

        self.walletGridLayout.addWidget(self.tradingPriceLineEdit, 2, 1, 1, 1)
        self.amountLabel = QtWidgets.QLabel(self.tradingTab)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.amountLabel.setFont(font)
        self.amountLabel.setStyleSheet("color: white; background-color: rgb(50,100,130);")
        self.amountLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.amountLabel.setObjectName("amountLabel")
        self.walletGridLayout.addWidget(self.amountLabel, 1, 0, 1, 1)

        self.amountLineEdit = QtWidgets.QLineEdit(self.tradingTab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.amountLineEdit.sizePolicy().hasHeightForWidth())
        self.amountLineEdit.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.amountLineEdit.setFont(font)
        self.amountLineEdit.setStyleSheet("border: 1px solid white; height: 25px; color: white;")
        self.amountLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.amountLineEdit.setObjectName("amountLineEdit")

        self.walletGridLayout.addWidget(self.amountLineEdit, 1, 1, 1, 1)

        self.tradingPriceLabel = QtWidgets.QLabel(self.tradingTab)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.tradingPriceLabel.setFont(font)
        self.tradingPriceLabel.setStyleSheet("color: white; background-color: rgb(50,100,130);")
        self.tradingPriceLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.tradingPriceLabel.setObjectName("tradingPriceLabel")
        self.walletGridLayout.addWidget(self.tradingPriceLabel, 2, 0, 1, 1)
        self.walletGridLayout.setColumnStretch(0, 1)
        self.walletGridLayout.setColumnStretch(1, 2)
        self.tradingLeftVerticalLayout.addLayout(self.walletGridLayout)
        self.tradingGridLayout = QtWidgets.QGridLayout()
        self.tradingGridLayout.setSpacing(10)
        self.tradingGridLayout.setObjectName("tradingGridLayout")

        self.marketBuyButton = QtWidgets.QPushButton(self.tradingTab)
        font = QtGui.QFont()
        font.setPointSize(11)
        self.marketBuyButton.setFont(font)
        self.marketBuyButton.setStyleSheet("color: white;  background-color: rgb(100,30,40)")
        self.marketBuyButton.setObjectName("marketBuyButton")
        self.marketBuyButton.clicked.connect(lambda: self.set_order(self.coinLineEdit.text().upper() + "USDT",
                                                                    "BUY",
                                                                    "MARKET",
                                                                    self.tradingPriceLineEdit.text(),
                                                                    self.amountLineEdit.text()
                                                                    )
                                             )
        self.tradingGridLayout.addWidget(self.marketBuyButton, 1, 0, 1, 1)

        self.limitSellButton = QtWidgets.QPushButton(self.tradingTab)
        font = QtGui.QFont()
        font.setPointSize(11)
        self.limitSellButton.setFont(font)
        self.limitSellButton.setStyleSheet("color: white;  background-color: rgb(100,30,40)")
        self.limitSellButton.setObjectName("limitSellButton")
        self.limitSellButton.clicked.connect(lambda: self.set_order(self.coinLineEdit.text().upper() + "USDT",
                                                                    "SELL",
                                                                    "LIMIT",
                                                                    self.tradingPriceLineEdit.text(),
                                                                    self.amountLineEdit.text()
                                                                    )
                                             )
        self.tradingGridLayout.addWidget(self.limitSellButton, 0, 1, 1, 1)

        self.marketSellButton = QtWidgets.QPushButton(self.tradingTab)
        font = QtGui.QFont()
        font.setPointSize(11)
        self.marketSellButton.setFont(font)
        self.marketSellButton.setStyleSheet("color: white;  background-color: rgb(100,30,40)")
        self.marketSellButton.setObjectName("marketSellButton")
        self.marketSellButton.clicked.connect(lambda: self.set_order(self.coinLineEdit.text().upper() + "USDT",
                                                                     "SELL",
                                                                     "MARKET",
                                                                     self.tradingPriceLineEdit.text(),
                                                                     self.amountLineEdit.text()
                                                                     )
                                              )
        self.tradingGridLayout.addWidget(self.marketSellButton, 1, 1, 1, 1)

        self.limitBuyButton = QtWidgets.QPushButton(self.tradingTab)
        font = QtGui.QFont()
        font.setPointSize(11)
        self.limitBuyButton.setFont(font)
        self.limitBuyButton.setStyleSheet("color: white;  background-color: rgb(100,30,40)")
        self.limitBuyButton.setObjectName("limitBuyButton")
        self.limitBuyButton.clicked.connect(lambda: self.set_order(self.coinLineEdit.text().upper() + "USDT",
                                                                   "BUY",
                                                                   "LIMIT",
                                                                   self.tradingPriceLineEdit.text(),
                                                                   self.amountLineEdit.text()
                                                                   )
                                            )
        self.tradingGridLayout.addWidget(self.limitBuyButton, 0, 0, 1, 1)

        self.queryPriceButton2 = QtWidgets.QPushButton(self.tradingTab)
        font = QtGui.QFont()
        font.setPointSize(11)
        self.queryPriceButton2.setFont(font)
        self.queryPriceButton2.setStyleSheet("color: white;  background-color: rgb(100,30,40)")
        self.queryPriceButton2.setObjectName("queryPriceButton2")
        self.queryPriceButton2.clicked.connect(lambda: self.query_price(self.coinLineEdit.text(), 1))
        self.tradingGridLayout.addWidget(self.queryPriceButton2, 2, 0, 1, 1)

        self.retrievedPriceLabel2 = QtWidgets.QLabel(self.tradingTab)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.retrievedPriceLabel2.setFont(font)
        self.retrievedPriceLabel2.setStyleSheet("color: white; border: 1px solid white;")
        self.retrievedPriceLabel2.setText("")
        self.retrievedPriceLabel2.setObjectName("retrievedPriceLabel2")

        self.tradingGridLayout.addWidget(self.retrievedPriceLabel2, 2, 1, 1, 1)
        self.tradingGridLayout.setColumnStretch(0, 1)
        self.tradingGridLayout.setColumnStretch(1, 1)
        self.tradingLeftVerticalLayout.addLayout(self.tradingGridLayout)
        self.horizontalLayout_4.addLayout(self.tradingLeftVerticalLayout)
        self.tradingVerticalLine = QtWidgets.QFrame(self.tradingTab)
        self.tradingVerticalLine.setStyleSheet("background-color: black;")
        self.tradingVerticalLine.setFrameShape(QtWidgets.QFrame.VLine)
        self.tradingVerticalLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.tradingVerticalLine.setObjectName("tradingVerticalLine")
        self.horizontalLayout_4.addWidget(self.tradingVerticalLine)
        self.tradingRightVerticalLayout = QtWidgets.QVBoxLayout()
        self.tradingRightVerticalLayout.setContentsMargins(2, 2, 2, 2)
        self.tradingRightVerticalLayout.setSpacing(10)
        self.tradingRightVerticalLayout.setObjectName("tradingRightVerticalLayout")
        self.displayOrdersButton = QtWidgets.QPushButton(self.tradingTab)
        self.displayOrdersButton.setMinimumSize(QtCore.QSize(220, 28))
        self.displayOrdersButton.setMaximumSize(QtCore.QSize(16777215, 28))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.displayOrdersButton.setFont(font)
        self.displayOrdersButton.setStyleSheet("color: white;  background-color: rgb(100,30,40)")
        self.displayOrdersButton.setObjectName("displayOrdersButton")
        self.displayOrdersButton.clicked.connect(self.query_orders)
        self.tradingRightVerticalLayout.addWidget(self.displayOrdersButton)

        self.ordersListWidget = QtWidgets.QListWidget(self.tradingTab)
        self.ordersListWidget.setMinimumSize(QtCore.QSize(220, 0))
        self.ordersListWidget.setGridSize(QtCore.QSize(0, 30))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.ordersListWidget.setFont(font)
        self.ordersListWidget.setStyleSheet("color: white; border: 1px solid white;")
        self.ordersListWidget.setObjectName("ordersListWidget")
        self.tradingRightVerticalLayout.addWidget(self.ordersListWidget)

        self.cancelOrderHorizontalLayout = QtWidgets.QHBoxLayout()
        self.cancelOrderHorizontalLayout.setObjectName("cancelOrderHorizontalLayout")
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.cancelOrderHorizontalLayout.addItem(spacerItem3)
        self.cancelOrderButton = QtWidgets.QPushButton(self.tradingTab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cancelOrderButton.sizePolicy().hasHeightForWidth())
        self.cancelOrderButton.setSizePolicy(sizePolicy)
        self.cancelOrderButton.setMinimumSize(QtCore.QSize(120, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.cancelOrderButton.setFont(font)
        self.cancelOrderButton.setStyleSheet("color: white;  background-color: rgb(100,30,40)")
        self.cancelOrderButton.setObjectName("cancelOrderButton")
        self.cancelOrderButton.clicked.connect(self.cancel_order)
        self.cancelOrderHorizontalLayout.addWidget(self.cancelOrderButton)

        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.cancelOrderHorizontalLayout.addItem(spacerItem4)
        self.tradingRightVerticalLayout.addLayout(self.cancelOrderHorizontalLayout)
        self.horizontalLayout_4.addLayout(self.tradingRightVerticalLayout)
        self.tabWidget.addTab(self.tradingTab, "")
        self.mainPageVerticalLayout.addWidget(self.tabWidget)
        self.horizontalLayout_6.addLayout(self.mainPageVerticalLayout)
        self.stackedWidget.addWidget(self.mainPage)
        self.settingsPage = QtWidgets.QWidget()
        self.settingsPage.setObjectName("settingsPage")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.settingsPage)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.settingsVerticalLayout = QtWidgets.QVBoxLayout()
        self.settingsVerticalLayout.setContentsMargins(3, 3, 3, 3)
        self.settingsVerticalLayout.setSpacing(6)
        self.settingsVerticalLayout.setObjectName("settingsVerticalLayout")
        self.settingsLabel = QtWidgets.QLabel(self.settingsPage)
        self.settingsLabel.setMinimumSize(QtCore.QSize(0, 27))
        self.settingsLabel.setMaximumSize(QtCore.QSize(16777215, 27))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.settingsLabel.setFont(font)
        self.settingsLabel.setStyleSheet("color: white;")
        self.settingsLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.settingsLabel.setObjectName("settingsLabel")
        self.settingsVerticalLayout.addWidget(self.settingsLabel)
        self.settingsGridLayout = QtWidgets.QGridLayout()
        self.settingsGridLayout.setSpacing(10)
        self.settingsGridLayout.setObjectName("settingsGridLayout")

        self.alarmDurationLabel = QtWidgets.QLabel(self.settingsPage)
        self.alarmDurationLabel.setMinimumSize(QtCore.QSize(0, 27))
        self.alarmDurationLabel.setMaximumSize(QtCore.QSize(16777215, 27))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.alarmDurationLabel.setFont(font)
        self.alarmDurationLabel.setStyleSheet("color: white; background-color: rgb(50,100,130);")
        self.alarmDurationLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.alarmDurationLabel.setObjectName("alarmDurationLabel")
        self.settingsGridLayout.addWidget(self.alarmDurationLabel, 2, 0, 1, 1)

        self.apiKeyLineEdit = QtWidgets.QLineEdit(self.settingsPage)
        self.apiKeyLineEdit.setMinimumSize(QtCore.QSize(0, 25))
        self.apiKeyLineEdit.setStyleSheet("border: 1px solid white; color: white;")
        self.apiKeyLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.apiKeyLineEdit.setObjectName("apiKeyLineEdit")
        self.settingsGridLayout.addWidget(self.apiKeyLineEdit, 0, 1, 1, 1)

        self.apiSecretLineEdit = QtWidgets.QLineEdit(self.settingsPage)
        self.apiSecretLineEdit.setMinimumSize(QtCore.QSize(0, 25))
        self.apiSecretLineEdit.setStyleSheet("border: 1px solid white; color: white;")
        self.apiSecretLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.apiSecretLineEdit.setObjectName("apiSecretLineEdit")
        self.settingsGridLayout.addWidget(self.apiSecretLineEdit, 1, 1, 1, 1)

        self.apiSecretLabel = QtWidgets.QLabel(self.settingsPage)
        self.apiSecretLabel.setMinimumSize(QtCore.QSize(0, 27))
        self.apiSecretLabel.setMaximumSize(QtCore.QSize(16777215, 27))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.apiSecretLabel.setFont(font)
        self.apiSecretLabel.setStyleSheet("color: white; background-color: rgb(50,100,130);")
        self.apiSecretLabel.setMinimumSize(QtCore.QSize(0, 25))
        self.apiSecretLabel.setObjectName("apiSecretLabel")
        self.apiSecretLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.settingsGridLayout.addWidget(self.apiSecretLabel, 1, 0, 1, 1)

        self.alarmDurationComboBox = QtWidgets.QComboBox(self.settingsPage)
        self.alarmDurationComboBox.setMinimumSize(QtCore.QSize(0, 25))
        self.alarmDurationComboBox.setStyleSheet("border: 1px solid white; color: white;")
        self.alarmDurationComboBox.setObjectName("alarmDurationComboBox")
        self.alarmDurationComboBox.addItem("")
        self.alarmDurationComboBox.addItem("")
        self.alarmDurationComboBox.addItem("")
        self.alarmDurationComboBox.addItem("")
        self.alarmDurationComboBox.addItem("")
        self.alarmDurationComboBox.addItem("")
        self.alarmDurationComboBox.addItem("")
        self.alarmDurationComboBox.addItem("")
        self.alarmDurationComboBox.addItem("")
        self.alarmDurationComboBox.addItem("")
        self.settingsGridLayout.addWidget(self.alarmDurationComboBox, 2, 1, 1, 1)

        self.saveButton = QtWidgets.QPushButton(self.settingsPage)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(False)
        font.setWeight(50)
        self.saveButton.setFont(font)
        self.saveButton.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.saveButton.setStyleSheet("color: white;  background-color: rgb(100,30,40)")
        self.saveButton.setObjectName("saveButton")
        self.saveButton.clicked.connect(self.save_settings)
        self.settingsGridLayout.addWidget(self.saveButton, 6, 0, 1, 2)

        self.alarmSoundSlider = QtWidgets.QSlider(self.settingsPage)
        self.alarmSoundSlider.setOrientation(QtCore.Qt.Horizontal)
        self.alarmSoundSlider.setObjectName("alarmSoundSlider")
        self.settingsGridLayout.addWidget(self.alarmSoundSlider, 3, 1, 1, 1)

        self.alarmSoundLabel = QtWidgets.QLabel(self.settingsPage)
        self.alarmSoundLabel.setMinimumSize(QtCore.QSize(0, 27))
        self.alarmSoundLabel.setMaximumSize(QtCore.QSize(16777215, 27))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.alarmSoundLabel.setFont(font)
        self.alarmSoundLabel.setStyleSheet("color: white; background-color: rgb(50,100,130);")
        self.alarmSoundLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.alarmSoundLabel.setObjectName("alarmSoundLabel")
        self.settingsGridLayout.addWidget(self.alarmSoundLabel, 3, 0, 1, 1)

        self.muteCheckBox = QtWidgets.QCheckBox(self.settingsPage)
        self.muteCheckBox.setMinimumSize(QtCore.QSize(100, 27))
        self.muteCheckBox.setMaximumSize(QtCore.QSize(100, 27))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.muteCheckBox.setFont(font)
        self.muteCheckBox.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.muteCheckBox.setStyleSheet("color: white; \n"
                                        "background-color: rgb(50,100,130);\n"
                                        "padding-left: 2px;")
        self.muteCheckBox.setAutoRepeat(False)
        self.muteCheckBox.setAutoExclusive(False)
        self.muteCheckBox.setObjectName("muteCheckBox")
        self.settingsGridLayout.addWidget(self.muteCheckBox, 4, 0, 1, 2)

        self.apiKeyLabel = QtWidgets.QLabel(self.settingsPage)
        self.apiKeyLabel.setMinimumSize(QtCore.QSize(0, 27))
        self.apiKeyLabel.setMaximumSize(QtCore.QSize(16777215, 27))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.apiKeyLabel.setFont(font)
        self.apiKeyLabel.setStyleSheet("color: white; background-color: rgb(50,100,130);")
        self.apiKeyLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.apiKeyLabel.setObjectName("apiKeyLabel")

        self.settingsGridLayout.addWidget(self.apiKeyLabel, 0, 0, 1, 1)
        self.settingsLine = QtWidgets.QFrame(self.settingsPage)
        self.settingsLine.setFrameShape(QtWidgets.QFrame.HLine)
        self.settingsLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.settingsLine.setObjectName("settingsLine")
        self.settingsGridLayout.addWidget(self.settingsLine, 5, 0, 1, 2)
        self.settingsGridLayout.setColumnStretch(0, 1)
        self.settingsGridLayout.setColumnStretch(1, 2)
        self.settingsVerticalLayout.addLayout(self.settingsGridLayout)

        self.verticalLayout_4.addLayout(self.settingsVerticalLayout)
        spacerItem5 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_4.addItem(spacerItem5)

        self.stackedWidget.addWidget(self.settingsPage)
        self.verticalLayout_5.addWidget(self.stackedWidget)

        self.footerHorizontalLayout = QtWidgets.QHBoxLayout()
        self.footerHorizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.footerHorizontalLayout.setObjectName("footerHorizontalLayout")

        self.settingsButton = QtWidgets.QPushButton(self.centralwidget)
        self.settingsButton.setMaximumSize(QtCore.QSize(25, 25))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.settingsButton.setFont(font)
        self.settingsButton.setStyleSheet("border: none;")
        self.settingsButton.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap("./settings.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.settingsButton.setIcon(icon1)
        self.settingsButton.setIconSize(QtCore.QSize(30, 30))
        self.settingsButton.setObjectName("settingsButton")
        self.settingsButton.clicked.connect(self.open_settings_menu)
        self.footerHorizontalLayout.addWidget(self.settingsButton)

        self.muteButton = QtWidgets.QPushButton(self.centralwidget)
        self.muteButton.setMaximumSize(QtCore.QSize(25, 25))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.muteButton.setFont(font)
        self.muteButton.setStyleSheet("border: none;")
        self.muteButton.setText("")
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap("./mute.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.muteButton.setIcon(icon2)
        self.muteButton.setIconSize(QtCore.QSize(30, 30))
        self.muteButton.setObjectName("muteButton")
        self.muteButton.clicked.connect(self.mute)
        self.footerHorizontalLayout.addWidget(self.muteButton)
        self.footerHorizontalLayout.setStretch(1, 1)
        self.verticalLayout_5.addLayout(self.footerHorizontalLayout)

        self.trackingTab = QtWidgets.QWidget()
        self.trackingTab.setObjectName("trackingTab")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.trackingTab)
        self.horizontalLayout_3.setContentsMargins(3, 3, 3, 3)
        self.horizontalLayout_3.setSpacing(3)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.trackMainHorizontalLayout = QtWidgets.QHBoxLayout()
        self.trackMainHorizontalLayout.setObjectName("trackMainHorizontalLayout")
        self.trackMainVerticalLayout = QtWidgets.QVBoxLayout()
        self.trackMainVerticalLayout.setObjectName("trackMainVerticalLayout")
        self.trackListLabel = QtWidgets.QLabel(self.trackingTab)
        self.trackListLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.trackListLabel.setFont(font)
        self.trackListLabel.setStyleSheet("\n"
                                          "padding: 5px 0px 5px 0px;\n"
                                          "color: white;")
        self.trackListLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.trackListLabel.setObjectName("trackListLabel")
        self.trackMainVerticalLayout.addWidget(self.trackListLabel)
        self.trackListListWidget = QtWidgets.QListWidget(self.trackingTab)
        self.trackListListWidget.setMinimumSize(QtCore.QSize(330, 230))
        self.trackListListWidget.setGridSize(QtCore.QSize(0, 30))
        self.trackListListWidget.setStyleSheet("border: 1px solid white;\n"
                                               "color: white;\n"
                                               "\n"
                                               "QScrollBar {\n"
                                               "    width: 8px;\n"
                                               "    background-color: black;\n"
                                               "}\n"
                                               "\n"
                                               "QScrollBar::sub-page {\n"
                                               "    background-color: black;\n"
                                               "}\n"
                                               "\n"
                                               "QScrollBar::add-page {\n"
                                               "    background-color: black;\n"
                                               "}\n"
                                               "\n"
                                               "QScrollBar::handle {\n"
                                               "    background-color: gray;\n"
                                               "}"
                                               "QListWidgetItem {"
                                               "    height: 30px;"
                                               "}")
        self.trackListListWidget.setObjectName("trackListListWidget")
        self.trackMainVerticalLayout.addWidget(self.trackListListWidget)
        self.trackGridLayout = QtWidgets.QGridLayout()
        self.trackGridLayout.setObjectName("trackGridLayout")
        self.trackDeleteButton = QtWidgets.QPushButton(self.trackingTab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.trackDeleteButton.sizePolicy().hasHeightForWidth())
        self.trackDeleteButton.setSizePolicy(sizePolicy)
        self.trackDeleteButton.setMinimumSize(QtCore.QSize(129, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.trackDeleteButton.setFont(font)
        self.trackDeleteButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.trackDeleteButton.setStyleSheet("color: white;  background-color: rgb(100,30,40)")
        self.trackDeleteButton.setObjectName("trackDeleteButton")
        self.trackDeleteButton.clicked.connect(self.delete_track)
        self.trackGridLayout.addWidget(self.trackDeleteButton, 1, 2, 1, 1)
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.trackGridLayout.addItem(spacerItem5, 1, 4, 1, 1)
        self.trackGridLayout.setSpacing(5)
        self.trackCoinLabel = QtWidgets.QLabel(self.trackingTab)
        self.trackCoinLabel.setMinimumSize(QtCore.QSize(129, 0))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.trackCoinLabel.setFont(font)
        self.trackCoinLabel.setStyleSheet("color: white; background-color: rgb(50,100,130);")
        self.trackCoinLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.trackCoinLabel.setObjectName("trackCoinLabel")
        self.trackGridLayout.addWidget(self.trackCoinLabel, 0, 1, 1, 1)
        self.trackAddButton = QtWidgets.QPushButton(self.trackingTab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.trackAddButton.sizePolicy().hasHeightForWidth())
        self.trackAddButton.setSizePolicy(sizePolicy)
        self.trackAddButton.setMinimumSize(QtCore.QSize(129, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.trackAddButton.setFont(font)
        self.trackAddButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.trackAddButton.setStyleSheet("color: white;  background-color: rgb(100,30,40)")
        self.trackAddButton.setObjectName("trackAddButton")
        self.trackAddButton.clicked.connect(self.add_track)
        self.trackGridLayout.addWidget(self.trackAddButton, 1, 1, 1, 1)
        spacerItem6 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.trackGridLayout.addItem(spacerItem6, 1, 0, 1, 1)
        self.trackCoinLineEdit = QtWidgets.QLineEdit(self.trackingTab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.trackCoinLineEdit.sizePolicy().hasHeightForWidth())
        self.trackCoinLineEdit.setSizePolicy(sizePolicy)
        self.trackCoinLineEdit.setMaximumSize(QtCore.QSize(129, 16777215))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.trackCoinLineEdit.setFont(font)
        self.trackCoinLineEdit.setStyleSheet("border: 1px solid white; height: 25px; color: white;")
        self.trackCoinLineEdit.setText("")
        self.trackCoinLineEdit.setObjectName("trackCoinLineEdit")
        self.trackGridLayout.addWidget(self.trackCoinLineEdit, 0, 2, 1, 1)
        self.trackStartButton = QtWidgets.QPushButton(self.trackingTab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.trackStartButton.sizePolicy().hasHeightForWidth())
        self.trackStartButton.setSizePolicy(sizePolicy)
        self.trackStartButton.setMinimumSize(QtCore.QSize(264, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.trackStartButton.setFont(font)
        self.trackStartButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.trackStartButton.setStyleSheet("color: white;  background-color: rgb(100,30,40)")
        self.trackStartButton.setObjectName("trackStartButton")
        self.trackStartButton.clicked.connect(self.start_stop_tracking)
        self.trackGridLayout.addWidget(self.trackStartButton, 3, 1, 1, 2)
        self.trackMainVerticalLayout.addLayout(self.trackGridLayout)
        self.trackMainHorizontalLayout.addLayout(self.trackMainVerticalLayout)
        self.horizontalLayout_3.addLayout(self.trackMainHorizontalLayout)
        self.tabWidget.addTab(self.trackingTab, "")


        MainWindow.setCentralWidget(self.centralwidget)

        self.tradeAlarmActions = QtWidgets.QListWidget(self.tradeAlarmsListWidget)
        self.tradeAlarmActions.setGeometry(QtCore.QRect(0, 0, 80, 26))
        self.tradeAlarmActions.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tradeAlarmActions.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tradeAlarmActions.setVisible(False)
        self.tradeAlarmActions.mousePressEvent = self.alarmsActionsListWidgetMousePressEvent
        self.tradeAlarmActions.setStyleSheet("""
                                                                                    QListWidget {
                                                                                        border: 1px solid black;
                                                                                        border-bottom: none;
                                                                                    }
    
                                                                                    QListWidget::item { 
                                                                                        background-color: white;
                                                                                        color: black;   
                                                                                        border: none; 
                                                                                        border-bottom: 1px solid black; } 
    
                                                                                    QListWidget::item:hover {
                                                                                        background-color: rgb(137,198,180);
                                                                                    }
                                                                                    """)

        for i in self.alarm_actions:
            self.action = QListWidgetItem(self.tradeAlarmActions)
            self.action.setText(i)

            font = QtGui.QFont()
            font.setPointSize(10)
            self.action.setFont(font)

            size = QtCore.QSize()
            size.setHeight(25)
            size.setWidth(30)
            self.action.setSizeHint(size)

        self.activeAlarmActions = QtWidgets.QListWidget(self.activeAlarmsListWidget)
        self.activeAlarmActions.setGeometry(QtCore.QRect(0, 0, 80, 26))
        self.activeAlarmActions.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.activeAlarmActions.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.activeAlarmActions.setVisible(False)
        self.activeAlarmActions.mousePressEvent = self.alarmsActionsListWidgetMousePressEvent
        self.activeAlarmActions.setStyleSheet("""
                                                                                    QListWidget {
                                                                                        border: 1px solid black;
                                                                                        border-bottom: none;
                                                                                    }
    
                                                                                    QListWidget::item { 
                                                                                        background-color: white;
                                                                                        color: black;   
                                                                                        border: none; 
                                                                                        border-bottom: 1px solid black; } 
    
                                                                                    QListWidget::item:hover {
                                                                                        background-color: rgb(137,198,180);
                                                                                    }
                                                                                    """)

        for i in self.alarm_actions:
            self.action = QListWidgetItem(self.activeAlarmActions)
            self.action.setText(i)

            font = QtGui.QFont()
            font.setPointSize(10)
            self.action.setFont(font)

            size = QtCore.QSize()
            size.setHeight(25)
            size.setWidth(30)
            self.action.setSizeHint(size)

        self.initialize()

        self.retranslateUi(MainWindow)
        self.stackedWidget.setCurrentIndex(0)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.activeAlarmsLabel.setText(_translate("MainWindow", "Active Alarms"))
        self.tradeAlarmsLabel.setText(_translate("MainWindow", "Trade Alarms"))
        self.addAlarmLabel.setText(_translate("MainWindow", "Add Alarm"))
        self.alarmCoinLabel.setText(_translate("MainWindow", "Coin:"))
        self.priceLabel.setText(_translate("MainWindow", "Price:"))
        self.rangeLabel.setText(_translate("MainWindow", "Range:"))
        self.tradeCheckBox.setText(_translate("MainWindow", "Trade?"))
        self.rangeCheckBox.setText(_translate("MainWindow", "Range?"))
        self.alarmComboBox.setItemText(0, _translate("MainWindow", "Rises above"))
        self.alarmComboBox.setItemText(1, _translate("MainWindow", "Drops below"))
        self.addAlarmButton.setText(_translate("MainWindow", "Add"))
        self.coinDisplayLabel.setText(_translate("MainWindow", "Coin:"))
        self.queryPriceButton.setText(_translate("MainWindow", "Get Price"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.alarmsTab), _translate("MainWindow", "Alarms"))
        self.walletLabel.setText(_translate("MainWindow", "Wallet"))
        self.coinLabel.setText(_translate("MainWindow", "Coin:"))
        self.amountLabel.setText(_translate("MainWindow", "Amount:"))
        self.tradingPriceLabel.setText(_translate("MainWindow", "Price:"))
        self.marketBuyButton.setText(_translate("MainWindow", "Market Buy"))
        self.limitSellButton.setText(_translate("MainWindow", "Limit Sell"))
        self.marketSellButton.setText(_translate("MainWindow", "Market Sell"))
        self.limitBuyButton.setText(_translate("MainWindow", "Limit Buy"))
        self.queryPriceButton2.setText(_translate("MainWindow", "Query Price"))
        self.displayOrdersButton.setText(_translate("MainWindow", "Display Orders"))
        self.cancelOrderButton.setText(_translate("MainWindow", "Cancel Order"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tradingTab), _translate("MainWindow", "Trading"))
        self.settingsLabel.setText(_translate("MainWindow", "Settings"))
        self.trackListLabel.setText(_translate("MainWindow", "Track List"))
        self.trackDeleteButton.setText(_translate("MainWindow", "Delete"))
        self.trackCoinLabel.setText(_translate("MainWindow", "Coin:"))
        self.trackAddButton.setText(_translate("MainWindow", "Add"))
        self.trackStartButton.setText(_translate("MainWindow", "Start"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.trackingTab), _translate("MainWindow", "Tracking"))
        self.alarmDurationLabel.setText(_translate("MainWindow", "Alarm duration:"))
        self.alarmDurationComboBox.setItemText(0, _translate("MainWindow", "1"))
        self.alarmDurationComboBox.setItemText(1, _translate("MainWindow", "2"))
        self.alarmDurationComboBox.setItemText(2, _translate("MainWindow", "3"))
        self.alarmDurationComboBox.setItemText(3, _translate("MainWindow", "4"))
        self.alarmDurationComboBox.setItemText(4, _translate("MainWindow", "5"))
        self.alarmDurationComboBox.setItemText(5, _translate("MainWindow", "6"))
        self.alarmDurationComboBox.setItemText(6, _translate("MainWindow", "7"))
        self.alarmDurationComboBox.setItemText(7, _translate("MainWindow", "8"))
        self.alarmDurationComboBox.setItemText(8, _translate("MainWindow", "9"))
        self.alarmDurationComboBox.setItemText(9, _translate("MainWindow", "10"))
        self.saveButton.setText(_translate("MainWindow", "Save"))
        self.alarmSoundLabel.setText(_translate("MainWindow", "Alarm sound:"))
        self.muteCheckBox.setText(_translate("MainWindow", "Mute"))
        self.apiKeyLabel.setText(_translate("MainWindow", "API Key:"))
        self.apiSecretLabel.setText(_translate("MainWindow", "API Secret:"))

    def tradeAlarmsMousePressEvent(self, event):
        self.current_row = (event.pos().y() // 30) + self.tradeAlarmsListWidget.verticalScrollBar().value()

        if (event.button() == 1):
            self.tradeAlarmActions.setVisible(False)

        elif (event.button() == 2):
            self.tradeAlarmActions.move(event.x(), event.y())
            self.tradeAlarmActions.setVisible(True)
            self.latest_right_click = 1

        QtWidgets.QListWidget.mousePressEvent(self.tradeAlarmsListWidget, event)

    def activeAlarmsMousePressEvent(self, event):
        self.current_row = (event.pos().y() // 30) + self.activeAlarmsListWidget.verticalScrollBar().value()

        if (event.button() == 1):
            self.activeAlarmActions.setVisible(False)

        elif (event.button() == 2):
            self.activeAlarmActions.move(event.x(), event.y())
            self.activeAlarmActions.setVisible(True)
            self.latest_right_click = 0

        QtWidgets.QListWidget.mousePressEvent(self.activeAlarmsListWidget, event)

    def alarmsActionsListWidgetMousePressEvent(self, event):
        global active_alarms, trade_alarms

        if (event.button() == 1):
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

            except Exception as e:
                print(e)

            self.tradeAlarmActions.setVisible(False)

        elif (event.button() == 2):
            self.tradeAlarmActions.setVisible(False)

        QtWidgets.QListWidget.mousePressEvent(self.tradeAlarmActions, event)

    def add_alarm(self, type=False):
        global active_alarms, trade_alarms, available_pairs

        try:
            coin = self.alarmCoinLineEdit.text().upper()
            pair = coin + "USDT"

            if pair in available_pairs:
                price = self.priceLineEdit.text()
                range = 0 if self.rangeLineEdit.text() == "" else float(self.rangeLineEdit.text())
                is_range = self.rangeCheckBox.isChecked()
                is_trade = self.tradeCheckBox.isChecked()
                direction = self.alarmComboBox.currentText()
                symbol = "▲" if direction == "Rises above" else "▼"

                if range != 0:
                    current_price = req.get(
                        'https://api.binance.com/api/v3/ticker/price?symbol=' + coin.upper() + "USDT").json()
                    current_price = float(current_price['price'])

                    symbol = "▼"
                    price = current_price * (1 - range / 100)
                    alarm_string = f"{pair} | {price} | {symbol}"
                    alarm_value = {"pair": coin + "USDT", "price": price, "range": range, "is_range": is_range,
                                   "is_trade": is_trade, "direction": "Drops below"}

                    self.activeAlarmsListWidget.addItem(alarm_string)
                    alarm_value["row_id"] = len(active_alarms)
                    active_alarms[str(len(active_alarms))] = alarm_value

                    symbol = "▲"
                    price = current_price * (1 + range / 100)
                    alarm_string = f"{pair} | {price} | {symbol}"
                    alarm_value = {"pair": coin + "USDT", "price": price, "range": range, "is_range": is_range,
                                   "is_trade": is_trade, "direction": "Rises above"}

                    self.activeAlarmsListWidget.addItem(alarm_string)
                    alarm_value["row_id"] = len(active_alarms)
                    active_alarms[str(len(active_alarms))] = alarm_value

                elif type:
                    alarm_string = f"{pair} | {price} | {symbol}"
                    alarm_value = {"row_id": -1, "name": coin, "pair": coin + "USDT", "price": float(price),
                                   "range": range, "is_range": is_range, "is_trade": is_trade, "direction": direction}

                    self.tradeAlarmsListWidget.addItem(alarm_string)
                    alarm_value["row_id"] = len(trade_alarms)
                    trade_alarms[str(len(trade_alarms))] = alarm_value

                else:
                    alarm_string = f"{pair} | {price} | {symbol}"
                    alarm_value = {"row_id": -1, "name": coin, "pair": coin + "USDT", "price": float(price),
                                   "range": range, "is_range": is_range, "is_trade": is_trade, "direction": direction}

                    self.activeAlarmsListWidget.addItem(alarm_string)
                    alarm_value["row_id"] = len(active_alarms)
                    active_alarms[str(len(active_alarms))] = alarm_value
            else:
                self.warn("Pair is not available.")

        except Exception as e: print(e)

    def set_order(self, symbol, side, _type, price, quantity):
        try:
            params = {
                'symbol': symbol,
                'side': side,
                'type': _type,
                'timeInForce': 'GTC',
                'quantity': float(quantity),
                'price': float(price),
                'recvWindow': 5000,
                'timestamp': int(time.time() * 1000)
            }

            if _type=="MARKET":
                params.pop("timeInForce")
                params.pop("recvWindow")
                params.pop("price")

            query_string = '&'.join([f"{key}={params[key]}" for key in params])
            signature = hmac.new(self.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature

            headers = {'X-MBX-APIKEY': self.api_key}

            response = req.post('https://api.binance.com/api/v3/order', params=params, headers=headers).json()

            if 'msg' in response.keys():
                if response['msg'] == "Invalid API-key, IP, or permissions for action.":
                    self.warn("Please provide valid API Key and Secret.")

        except:
            self.warn("Invalid or missing parameters.")

    def cancel_order(self):
        try:
            order_id = self.orders_dict[str(self.ordersListWidget.currentRow()-1)]["order_id"]
            symbol = self.orders_dict[str(self.ordersListWidget.currentRow()-1)]["symbol"]

            params = {
                'symbol': symbol,
                'orderId': order_id,
                'timestamp': int(time.time() * 1000)
            }

            query_string = '&'.join([f"{key}={params[key]}" for key in params])
            signature = hmac.new(self.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature

            headers = {'X-MBX-APIKEY': self.api_key}

            response = req.delete('https://api.binance.com/api/v3/order', params=params, headers=headers)

            time.sleep(1)
            self.query_orders()

        except Exception as e:
            print(e)
            self.warn("An error occured.")

    def query_price(self, pair, id):
        try:
            price = req.get('https://api.binance.com/api/v3/ticker/price?symbol=' + pair.upper() + "USDT").json()

            if id==0:
                self.retrievedPriceLabel.setText(price['price'].strip(" "))
            elif id==1:
                self.retrievedPriceLabel2.setText(price['price'].strip(" "))

        except Exception as e:
            print(e)

    def query_balances(self):
        try:
            params = {
                'timestamp': int(time.time() * 1000)
            }

            query_string = '&'.join([f"{key}={params[key]}" for key in params])
            signature = hmac.new(self.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature

            headers = {
                'X-MBX-APIKEY': self.api_key
            }

            response = req.get('https://api.binance.com/api/v3/account', params=params, headers=headers)

            balances_dict = json.loads(str(response.content)[2:-1])
            balances = dict()

            for balance in balances_dict["balances"]:
                quantity = float(balance["free"]) + float(balance["locked"])

                if balance["asset"] == "USDT":
                    balances["USDTTRY"] = quantity

                if quantity > 0:
                    balances[balance["asset"].upper() + "USDT"] = quantity

            endpoint = 'https://api.binance.com/api/v3/ticker/price'
            response = req.get(endpoint).json()

            new_balances = dict()
            ticker_prices = {item['symbol']: item['price'] for item in response if item['symbol'] in balances.keys()}
            for ticker, price in ticker_prices.items():
                if ticker != "USDTTRY":
                    value = float(balances[ticker]) * float(price)
                    if value > 10:
                        new_balances[ticker.replace("USDT", "")] = value
                else:
                    value = float(balances[ticker])
                    new_balances["USDT"] = value

            self.balancesListWidget.clear()
            for key, value in new_balances.items():
                self.balancesListWidget.addItem(f"{key+':':<8}{str(round(value, 2)):<6}")

        except Exception as e:
            self.warn("An error occurred.")

    def query_orders(self):
        try:
            params = {
                'timestamp': int(time.time() * 1000),
                'recvWindow': 5000
            }

            query_string = '&'.join([f"{key}={params[key]}" for key in params])
            signature = hmac.new(self.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature

            headers = {'X-MBX-APIKEY': self.api_key}

            response = req.get('https://api.binance.com/api/v3/openOrders', params=params, headers=headers)
            content = str(response.content)[2:-1]
            order_list = json.loads(content)

            self.ordersListWidget.clear()
            self.ordersListWidget.addItem(f"{'PAIR':<8} {'PRICE':<8} {'QUANTITY':<8}")
            for idx, order in enumerate(order_list):
                order_id = order["orderId"]
                symbol = str(order['symbol'])
                coin = str(order['symbol']).replace('USDT', '')
                side = str(order["side"])
                price = format(float(order["price"]), 'g')
                quantity = format(float(order["origQty"]), 'g')
                order_string = f"{coin:<8} {price:<8} {quantity:<8}"

                item = QListWidgetItem(order_string)
                item.setForeground(QtGui.QColor("green" if side =="BUY" else "red"))

                self.ordersListWidget.addItem(item)
                self.orders_dict[str(idx)] = {"order_id": order_id, "symbol": symbol, "price": price, "side": side, "quantity": quantity}

        except Exception as e:
            self.warn(str(e))

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
            self.alarmDurationComboBox.setCurrentIndex(self.alarm_duration-1)
            self.alarmSoundSlider.setValue(self.alarm_sound)
            self.muteCheckBox.setChecked(self.is_mute)

            for alarm_id, alarm_info in self.configuration['alarms'].items():
                symbol = "▲" if alarm_info['direction'] == "Rises above" else "▼"
                self.tradeAlarmsListWidget.addItem(f"{alarm_info['pair']} | {alarm_info['price']} | {symbol}")
                trade_alarms[alarm_id] = alarm_info

            for ticker in track_list:
                self.trackListListWidget.addItem(f"{ticker} | ")

        except Exception as e:
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
                self.tradeAlarmsListWidget.currentItem().setText(f"{alarm_value['pair']} | {str(alarm_value['price'])} | {symbol} | {price}")
            else:
                self.activeAlarmsListWidget.setCurrentRow(alarm_value["row_id"])
                self.activeAlarmsListWidget.currentItem().setText(f"{alarm_value['pair']} | {str(alarm_value['price'])} | {symbol} | {price}")

        except Exception as e:
            print(e)

    def track(self, track_dict):
        self.trackListListWidget.clear()
        for ticker, price in track_dict.items():
            self.trackListListWidget.addItem(f"{ticker} | {price.rstrip('0')}")

    def save_settings(self):
        global alarm_parameters, track_list

        try:
            self.configuration['tracks'] = track_list
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
            print(e)

    def	open_settings_menu(self):
        self.stackedWidget.setCurrentIndex(1-(self.stackedWidget.currentIndex()))

    def mute(self):
        global alarm_parameters

        alarm_parameters["is_mute"] = bool(1-int(alarm_parameters["is_mute"]))
        self.is_mute = alarm_parameters["is_mute"]

    def arange_alarm_dict(self, alarm_dict):
        temp_dict = dict()
        for id, (key, value) in enumerate(alarm_dict.items()):
            value["row_id"] = id
            temp_dict[str(id)] = value

        return temp_dict

    def add_track(self):
        global available_pairs, track_list

        if (self.trackCoinLineEdit.text().upper() + "USDT") in available_pairs.keys():
            track_list.append(self.trackCoinLineEdit.text().upper() + "USDT")
            self.trackCoinLineEdit.clear()
        else:
            self.warn("Pair is not available.")

    def delete_track(self):
        global track_list

        track_list.pop(self.trackListListWidget.currentRow())
        self.trackListListWidget.takeItem(self.trackListListWidget.currentRow())
        self.trackListListWidget.setCurrentRow(-1)

    def start_stop_tracking(self):
        self.is_tracking = 1-self.is_tracking

    def get_klines(self):
        global available_pairs, track_list

        response = req.get("https://api.binance.com/api/v3/ticker/price").json()
        for ticker in response:
            available_pairs[ticker['symbol']] = 0

        params = {
            "symbols": str(track_list).replace("'", '"').replace(" ", ""),
            "timeZone": 0
        }

        response = req.get("https://api.binance.com/api/v3/ticker/tradingDay", params=params).json()

        try:
            if response["code"] != -1100:
                for symbol in response:
                    available_pairs[symbol["symbol"]] = float(symbol['openPrice'])
        except:
            pass

    def warn(self, warning):
        msgBox = QMessageBox()
        msgBox.setWindowTitle("Warning")
        msgBox.setText(warning)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.setStyleSheet("""
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
                            """)
        msgBox.exec_()

class MyMainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

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

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet("""
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
