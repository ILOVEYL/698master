"""master ui"""
import sys
import os
from master import config
import traceback
import time
import threading
from master.UI.ui_setup import MasterWindowUi
from master.trans import common
from master.trans import linklayer
from master.trans.translate import Translate
from master.UI import dialog_ui
from master.UI import param_ui
from master.reply import reply
from master.datas import k_data
from master.others import msg_log
from master.others import master_config
if config.IS_USE_PYSIDE:
    from PySide import QtGui, QtCore
else:
    from PyQt4 import QtGui, QtCore


class MasterWindow(QtGui.QMainWindow, MasterWindowUi):
    """serial window"""
    receive_signal = QtCore.Signal(str, int) if config.IS_USE_PYSIDE else QtCore.pyqtSignal(str, int)
    send_signal = QtCore.Signal(str, int) if config.IS_USE_PYSIDE else QtCore.pyqtSignal(str, int)
    se_apdu_signal = QtCore.Signal(str) if config.IS_USE_PYSIDE else QtCore.pyqtSignal(str)

    def __init__(self):
        super(MasterWindow, self).__init__()
        self.setup_ui()
        self.plaintext_rn.setChecked(False)
        self.reply_rpt_cb.setChecked(True)
        self.reply_link_cb.setChecked(True)
        self.show_level_cb.setChecked(True)
        self.is_reply_link = True if self.reply_link_cb.isChecked() else False
        self.is_reply_rpt = True if self.reply_rpt_cb.isChecked() else False
        self.is_plaintext_rn = True if self.plaintext_rn.isChecked() else False
        self.cnt_box_w.setVisible(True if self.oad_auto_r_cb.isChecked() else False)
        # self.tmn_table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)

        self.apply_config()

        self.setAcceptDrops(True)

        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint\
                if self.always_top_cb.isChecked() else QtCore.Qt.Widget)
        self.receive_signal.connect(self.re_msg_do)
        self.send_signal.connect(self.se_msg_do)
        self.se_apdu_signal.connect(self.send_apdu)

        self.tmn_table_scan_b.clicked.connect(self.tmn_scan)
        self.clr_b.clicked.connect(lambda: self.clr_table(self.msg_table))
        self.msg_table.currentCellChanged.connect(self.trans_row)
        self.msg_table.cellClicked.connect(self.trans_row)
        self.msg_table.cellDoubleClicked.connect(self.trans_msg)
        self.se_clr_b.clicked.connect(lambda: self.se_msg_box.clear() or self.se_msg_box.setFocus())
        self.se_send_b.clicked.connect(self.send_se_msg)
        self.se_msg_box.textChanged.connect(self.trans_msg_box)
        self.se_msg_box.installEventFilter(self)
        self.show_linklayer_cb.stateChanged.connect(self.trans_se_msg)
        self.show_level_cb.stateChanged.connect(self.trans_se_msg)
        self.show_dtype_cb.stateChanged.connect(self.trans_se_msg)
        self.copy_b.clicked.connect(self.copy_to_clipboard)
        self.always_top_cb.clicked.connect(self.set_always_top)
        self.reply_link_cb.clicked.connect(self.set_reply_link)
        self.reply_rpt_cb.clicked.connect(self.set_reply_rpt)
        self.plaintext_rn.clicked.connect(self.set_plaintext_rn)
        self.read_oad_b.clicked.connect(self.send_read_oad)
        self.oad_auto_r_cb.clicked.connect(lambda: self.cnt_box_w.setVisible(True if self.oad_auto_r_cb.isChecked() else False))
        self.cnt_clr_b.clicked.connect(self.cnt_reset)
        self.oad_box.returnPressed.connect(self.send_read_oad)
        self.oad_box.textChanged.connect(self.explain_oad)

        self.about_action.triggered.connect(lambda: config.ABOUT_WINDOW.show() or config.ABOUT_WINDOW.showNormal() or config.ABOUT_WINDOW.activateWindow())
        self.link_action.triggered.connect(self.show_commu_window)
        self.general_cmd_action.triggered.connect(lambda: self.general_cmd_dialog.show() or self.general_cmd_dialog.showNormal() or self.general_cmd_dialog.activateWindow())
        self.get_set_service_action.triggered.connect(self.show_get_service_window)
        self.apdu_diy_action.triggered.connect(lambda: self.apdu_diy_dialog.show() or self.apdu_diy_dialog.showNormal() or self.apdu_diy_dialog.activateWindow())
        self.msg_diy_action.triggered.connect(lambda: self.msg_diy_dialog.show() or self.msg_diy_dialog.showNormal() or self.msg_diy_dialog.activateWindow())
        self.remote_update_action.triggered.connect(lambda: self.remote_update_dialog.show() or self.remote_update_dialog.showNormal() or self.remote_update_dialog.activateWindow())
        self.trans_log_action.triggered.connect(lambda: self.trans_file(config.LOG_PATH))
        self.open_log_action.triggered.connect(lambda: os.system('start "" "{dir}"'.format(dir=config.MSG_LOG_DIR)))
        self.open_trans_action.triggered.connect(self.trans_file)

        self.tmn_table_add_b.clicked.connect(lambda:\
                            self.add_tmn_table_row('000000000001', 0, 1, is_checked=True))
        self.tmn_table_clr_b.clicked.connect(lambda: self.clr_table(self.tmn_table))

        self.pop_dialog = dialog_ui.TransPopDialog()
        self.commu_dialog = dialog_ui.CommuDialog()
        self.get_set_service_dialog = dialog_ui.GetSetServiceDialog()
        self.apdu_diy_dialog = dialog_ui.ApduDiyDialog()
        self.msg_diy_dialog = dialog_ui.MsgDiyDialog()
        self.remote_update_dialog = dialog_ui.RemoteUpdateDialog()
        self.general_cmd_dialog = param_ui.ParamWindow()

        self.msg_log = msg_log.MsgLog()

        self.apdu_text = ''
        self.is_auto_r = False
        self.msg_now = ''

        self.send_cnt = 0
        self.receive_cnt = 0


    def dragEnterEvent(self, event):
        """drag"""
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()


    def dropEvent(self, event):
        """drop file"""
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            print('url:', links[0])
            self.trans_file(links[0])
        else:
            event.ignore()


    def apply_config(self):
        """apply config"""
        apply_config = master_config.MasterConfig()
        tmn_list = eval(apply_config.get_tmn_list())
        for tmn in tmn_list:
            self.add_tmn_table_row(is_checked=tmn[0], tmn_addr=tmn[1],\
                                    logic_addr=tmn[2], chan_index=tmn[3])
        self.always_top_cb.setChecked(apply_config.get_windows_top())
        self.oad_box.setText(apply_config.get_oad_r())


    def eventFilter(self, widget, event):
        """test"""
        if event.type() == QtCore.QEvent.FocusIn:
            self.msg_now = self.se_msg_box.toPlainText()
            self.trans_se_msg()
        return QtGui.QMainWindow.eventFilter(self, widget, event)


    def update_info_l(self, serial_status='', frontend_status='', server_status=''):
        """update info"""
        info_text = '<p><b>请按F2建立连接</b></p>'
        if serial_status or frontend_status or server_status:
            info_text = ''
            if serial_status:
                info_text += '<span style="color: {color}">串口{status}</span>'\
                                .format(color='red' if serial_status in ['故障'] else 'black', status=serial_status)
            if frontend_status:
                info_text += '<span style="color: {color}"> 前置机{status}</span>'\
                                .format(color='red' if frontend_status in ['故障'] else 'black', status=frontend_status)
            if server_status:
                info_text += '<span style="color: {color}"> 服务器{status}</span>'\
                                .format(color='red' if server_status in ['故障'] else 'black', status=server_status)
        self.info_l.setText(info_text)


    # @QtCore.Slot(str, int)
    def re_msg_do(self, re_text, chan_index):
        """recieve text"""
        self.add_msg_table_row(re_text, chan_index, '←')
        if self.oad_auto_r_cb.isChecked():
            self.receive_cnt += 1
            self.receive_cnt_l.setText('收%d'%self.receive_cnt)


    # @QtCore.Slot(str, int)
    def se_msg_do(self, re_text, chan_index):
        """recieve text"""
        self.add_msg_table_row(re_text, chan_index, '→')
        if self.oad_auto_r_cb.isChecked():
            self.send_cnt += 1
            self.send_cnt_l.setText('发%d'%self.send_cnt)


    def add_tmn_table_row(self, tmn_addr='000000000001', logic_addr=0, chan_index=1, is_checked=False):
        """add message row"""
        row_pos = self.tmn_table.rowCount()
        self.tmn_table.insertRow(row_pos)

        tmn_enable_cb = QtGui.QCheckBox()
        tmn_enable_cb.setChecked(is_checked)
        self.tmn_table.setCellWidget(row_pos, 0, tmn_enable_cb)

        item = QtGui.QTableWidgetItem(tmn_addr)
        self.tmn_table.setItem(row_pos, 1, item)

        logic_addr_box = QtGui.QSpinBox()
        logic_addr_box.setRange(0, 3)
        logic_addr_box.setValue(logic_addr)
        self.tmn_table.setCellWidget(row_pos, 2, logic_addr_box)

        channel_cb = QtGui.QComboBox()
        channel_cb.addItems(('串口', '前置机', '服务器'))
        channel_cb.setCurrentIndex(chan_index)
        self.tmn_table.setCellWidget(row_pos, 3, channel_cb)

        self.tmn_remove_cb = QtGui.QPushButton()
        self.tmn_remove_cb.setText('删')
        self.tmn_table.setCellWidget(row_pos, 4, self.tmn_remove_cb)
        self.tmn_remove_cb.clicked.connect(self.tmn_table_remove)

        self.tmn_table.scrollToBottom()


    def tmn_table_remove(self):
        """remove row in tmn table"""
        button = self.sender()
        index = self.tmn_table.indexAt(button.pos())
        self.tmn_table.removeRow(index.row())


    def add_msg_table_row(self, m_text, chan_index, direction):
        """add message row"""
        trans = Translate(m_text)
        brief = trans.get_brief()
        # direction = trans.get_direction()
        client_addr = trans.get_CA()
        if config.IS_FILETER_CA and client_addr != '00' and client_addr != config.COMMU.master_addr:
            print('过滤报文：CA不匹配')
            return
        server_addr = trans.get_SA()
        logic_addr = trans.get_logic_addr()
        chan_text = {0: '串口', 1: '前置机', 2: '服务器'}.get(chan_index)

        # chk to add tmn addr to table
        if direction == '←':
            for row_num in range(self.tmn_table.rowCount()):
                if server_addr == self.tmn_table.item(row_num, 1).text()\
                and logic_addr == self.tmn_table.cellWidget(row_num, 2).value()\
                and chan_index == self.tmn_table.cellWidget(row_num, 3).currentIndex():
                    break
            else:
                is_cb_checked = False if chan_index == 1 else True
                self.add_tmn_table_row(tmn_addr=server_addr, logic_addr=logic_addr,\
                                        chan_index=chan_index, is_checked=is_cb_checked)

        text_color = QtGui.QColor(220, 226, 241) if direction == '→' else\
                    QtGui.QColor(227, 237, 205) if direction == '←' else QtGui.QColor(255, 255, 255)
        row_pos = self.msg_table.rowCount()
        self.msg_table.insertRow(row_pos)

        item = QtGui.QTableWidgetItem(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        # item.setBackground(text_color)
        self.msg_table.setItem(row_pos, 0, item)

        addr_text = '{SA}:{logic}'.format(SA=server_addr, logic=logic_addr)
        item = QtGui.QTableWidgetItem(addr_text)
        # item.setBackground(text_color)
        self.msg_table.setItem(row_pos, 1, item)

        item = QtGui.QTableWidgetItem(chan_text + direction)
        item.setBackground(text_color)
        self.msg_table.setItem(row_pos, 2, item)

        item = QtGui.QTableWidgetItem(brief)
        if brief == '无效报文':
            item.setTextColor(QtCore.Qt.red)
        if brief.find('(访问失败)') == 0:
            item.setTextColor(QtGui.QColor(255, 140, 0))
        self.msg_table.setItem(row_pos, 3, item)

        msg_text = common.format_text(m_text)
        item = QtGui.QTableWidgetItem(msg_text)
        # item.setBackground(text_color)
        self.msg_table.setItem(row_pos, 4, item)

        if row_pos > config.MSG_TABLE_ROW_MAX:
            self.msg_table.removeRow(0)

        self.msg_table.scrollToBottom()

        # log
        self.msg_log.add_log(addr_text, chan_text, direction, brief, msg_text)

        service = trans.get_service()
        if service == '01' and self.is_reply_link:
            reply_apdu_text = reply.get_link_replay_apdu(trans)
            self.send_apdu(reply_apdu_text, tmn_addr=server_addr,\
                            logic_addr=logic_addr, chan_index=chan_index, C_text='01')
        if service[:2] == '88' and self.is_reply_rpt:
            reply_apdu_text = reply.get_rpt_replay_apdu(trans)
            self.send_apdu(reply_apdu_text, tmn_addr=server_addr,\
                            logic_addr=logic_addr, chan_index=chan_index, C_text='03')


    def trans_msg_box(self):
        """trans_msg_box"""
        self.msg_now = self.se_msg_box.toPlainText()
        self.trans_se_msg()


    def trans_se_msg(self):
        """translate"""
        if len(self.msg_now) < 5:
            return
        trans = Translate(self.msg_now)
        full = trans.get_full(self.show_level_cb.isChecked(), self.show_dtype_cb.isChecked(), has_linklayer=self.show_linklayer_cb.isChecked())
        self.explain_box.setText(r'%s'%full)
        self.se_send_b.setEnabled(True if trans.is_success else False)
        if self.se_send_b.isEnabled():
            self.apdu_text = trans.get_apdu_text()


    def send_se_msg(self):
        """send sendbox msg"""
        msg = self.se_msg_box.toPlainText()
        if len(msg) < 5:
            return
        trans = Translate(msg)
        apdu_text = trans.get_apdu_text()
        self.se_apdu_signal.emit(apdu_text)


    # @QtCore.Slot(str)
    def send_apdu(self, apdu_text, tmn_addr='', logic_addr=-1, chan_index=-1, C_text='43'):
        """apdu to compelete msg to send"""
        if self.is_plaintext_rn:
            if apdu_text.startswith('0501') or apdu_text.startswith('0502'):
                # 10 + 00 + len + apdu + 0110 5FE30D32D6A20288F9112B5C6052CFDB(fixme: 先固定一个随机数)
                apdu_len = len(common.text2list(apdu_text))
                apdu_head = '1000' #安全请求+明文应用数据单元

                if apdu_len < 128:
                    apdu_head += "%02X"%apdu_len
                elif apdu_len < 256:
                    apdu_head += "81%02X"%apdu_len
                else:
                    apdu_head += "82%04X"%apdu_len

                apdu_text = apdu_head + apdu_text + '0110 5FE30D32D6A20288F9112B5C6052CFDB'
                # print('读取明文+随机{}:{}'.format(len(common.text2list(apdu_text)), apdu_text))

        for row in [x for x in range(self.tmn_table.rowCount())\
                        if self.tmn_table.cellWidget(x, 0).isChecked()]:
            if tmn_addr and tmn_addr != self.tmn_table.item(row, 1).text():
                continue
            if logic_addr != -1 and logic_addr != self.tmn_table.cellWidget(row, 2).value():
                continue
            if chan_index != -1 and chan_index != self.tmn_table.cellWidget(row, 3).currentIndex():
                continue

            compelete_msg = linklayer.add_linkLayer(common.text2list(apdu_text),\
                                logic_addr=self.tmn_table.cellWidget(row, 2).value(),\
                                SA_text=self.tmn_table.item(row, 1).text(),\
                                CA_text=config.COMMU.master_addr, C_text=C_text)
            config.COMMU.send_msg(compelete_msg, self.tmn_table.cellWidget(row, 3).currentIndex())


    def send_msg(self, msg_text, chan_index):
        """msg to send"""
        config.COMMU.send_msg(msg_text, chan_index)


    def tmn_scan(self):
        """scan terminal"""
        wild_apdu = '0501014000020000'
        compelete_msg = linklayer.add_linkLayer(common.text2list(wild_apdu),\
                                SA_text='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',\
                                SA_type=1,\
                                CA_text=config.COMMU.master_addr,\
                                C_text='43')
        config.COMMU.send_msg(compelete_msg, -1)


    def trans_msg(self, row):
        """translate massage"""
        self.pop_dialog.msg_box.setPlainText(self.msg_table.item(row, 4).text())
        self.pop_dialog.show()
        self.pop_dialog.showNormal()
        self.pop_dialog.activateWindow()


    def trans_row(self, row):
         """translate row massage"""
         self.msg_now = self.msg_table.item(row, 4).text()
         self.trans_se_msg()

    def clr_table(self, table):
        """clear table widget"""
        for _ in range(table.rowCount()):
            table.removeRow(0)
        # table.setRowCount(0)


    def set_always_top(self):
        """set_always_top"""
        window_pos = self.pos()
        if self.always_top_cb.isChecked() is True:
            self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            self.show()
        else:
            self.setWindowFlags(QtCore.Qt.Widget)
            self.show()
        self.move(window_pos)


    def set_reply_link(self):
        """set_reply_link"""
        self.is_reply_link = self.reply_link_cb.isChecked()


    def set_reply_rpt(self):
        """set_reply_rpt"""
        self.is_reply_rpt = self.reply_rpt_cb.isChecked()


    def set_plaintext_rn(self):
        """set_plaintext_rn"""
        self.is_plaintext_rn = self.plaintext_rn.isChecked()


    def show_get_service_window(self):
        """show_get_service_window"""
        self.get_set_service_dialog.show()
        self.get_set_service_dialog.activateWindow()


    def show_commu_window(self):
        """show commu window"""
        self.commu_dialog.show()
        self.commu_dialog.showNormal()
        self.commu_dialog.activateWindow()

    def send_read_oad(self):
        """send message"""
        if self.is_auto_r:
            self.is_auto_r = False
            self.read_oad_b.setText('读取')
            self.oad_auto_r_cb.setEnabled(True)
            self.oad_auto_r_spin.setEnabled(True)
            self.oad_auto_unit_l.setEnabled(True)
            return
        oad_text = self.oad_box.text().replace(' ', '')
        if len(oad_text) == 8:
            apdu_text = '050100 %s 00'%oad_text
            if self.oad_auto_r_cb.isChecked():
                self.is_auto_r = True
                self.read_oad_b.setText('停止')
                self.oad_auto_r_cb.setEnabled(False)
                self.oad_auto_r_spin.setEnabled(False)
                self.oad_auto_unit_l.setEnabled(False)
                threading.Thread(target=self.auto_r_oad,\
                    args=(apdu_text,)).start()
            else:
                self.se_apdu_signal.emit(apdu_text)
        else:
            self.oad_explain_l.setTextFormat(QtCore.Qt.RichText)
            self.oad_explain_l.setText('<p style="color: red">请输入正确的OAD</p>')

    
    def auto_r_oad(self, apdu_text):
        """auto read oad thread"""
        delay_s = max(self.oad_auto_r_spin.value(), 0.05)
        if delay_s == 0:
            delay_s = 0.2
        while self.is_auto_r:
            self.se_apdu_signal.emit(apdu_text)
            time.sleep(delay_s)


    def cnt_reset(self):
        """reset cnt"""
        self.send_cnt = 0
        self.receive_cnt = 0
        self.send_cnt_l.setText('发0')
        self.receive_cnt_l.setText('收0')


    def explain_oad(self):
        """explain_oad"""
        oad_text = self.oad_box.text().replace(' ', '')
        if len(oad_text) == 8:
            explain = config.K_DATA.get_oad_explain(oad_text)
            self.oad_explain_l.setText(explain)
        else:
            self.oad_explain_l.setText('')


    def trans_file(self, file_path='1'):
        """file analysis"""
        cmd = 'start "" "{exe}" "{log}"'.format(exe=config.RUN_EXE_PATH, log=file_path)
        print(cmd)
        os.system(cmd)


    def copy_to_clipboard(self):
        """copy_to_clipboard"""
        trans = Translate(self.msg_now)
        text = trans.get_clipboard_text(self.show_level_cb.isChecked(), self.show_dtype_cb.isChecked())
        clipboard = QtGui.QApplication.clipboard()
        clipboard.clear()
        clipboard.setText(text)


    def closeEvent(self, event):
        """close event"""
        # save config
        save_config = master_config.MasterConfig()
        tmn_list = []
        for row_num in range(self.tmn_table.rowCount()):
            tmn_list.append([self.tmn_table.cellWidget(row_num, 0).isChecked(),\
                                self.tmn_table.item(row_num, 1).text(),\
                                self.tmn_table.cellWidget(row_num, 2).value(),\
                                self.tmn_table.cellWidget(row_num, 3).currentIndex()])
        save_config.set_tmn_list(tmn_list)
        save_config.set_windows_top(self.always_top_cb.isChecked())
        save_config.set_oad_r(self.oad_box.text().replace(' ', ''))
        save_config.commit()

        # quit
        config.COMMU.quit()
        event.accept()
        os._exit(0)

        # ask to quit
        # window_pos = self.pos()
        # self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        # self.show()
        # self.move(window_pos)
        # quit_box = QtGui.QMessageBox()
        # reply = quit_box.question(self, '698后台', '确定退出吗？'
        #                           , QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        # if reply == QtGui.QMessageBox.Yes:
        #     config.COMMU.quit()
        #     event.accept()
        #     os._exit(0)
        # else:
        #     self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint\
        #             if self.always_top_cb.isChecked() else QtCore.Qt.Widget)
        #     self.show()
        #     self.move(window_pos)
        #     event.ignore()


if __name__ == '__main__':
    APP = QtGui.QApplication(sys.argv)
    dialog = MasterWindow()
    dialog.show()
    APP.exec_()
    os._exit(0)
