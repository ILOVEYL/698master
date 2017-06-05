'''master app'''
import sys
import os
from master.UI.trans_ui import TransWindow
from master.UI.about_ui import AboutWindow
from master.UI.master_ui import MasterWindow
from PyQt4 import QtGui
from master import config


def main():
    '''main'''
    APP = QtGui.QApplication(sys.argv)
    config.ABOUT_WINDOW = AboutWindow()
    config.TRANS_WINDOW = TransWindow()
    config.MASTER_WINDOW = MasterWindow()
    config.MASTER_WINDOW.show()
    APP.exec_()
    os._exit(0)

if __name__ == "__main__":
    main()