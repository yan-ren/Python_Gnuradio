import sys
import math
import struct
import webbrowser
import numpy
import time
from Queue import Queue
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# The new Stream Object which replaces the default stream associated with sys.stdout
# This object just puts data in a queue
class WriteStream(object):
    def __init__(self, queue):
        self.queue = queue

    def write(self, text):
        # slow down the rate to print in order to protect the queue from crashing
        time.sleep(0.001)
        self.queue.put(text)


# A QObject (to be run in a QThread) which sits waiting for data to come through a Queue.Queue().
# It blocks until data is available, and one it has got something from the queue, it sends
# it to the "MainThread" by emitting a Qt Signal
class Receiver(QObject):
    mysignal = pyqtSignal(str)

    def __init__(self, queue, *args, **kwargs):
        QObject.__init__(self, *args, **kwargs)
        self.queue = queue

    @pyqtSlot()
    def run(self):
        while True:
            text = self.queue.get()
            self.mysignal.emit(text)


# An example QObject (to be run in a QThread) which outputs information with print
class File_Reading_Save(QThread):
    def __init__(self, inputFilePath, outputFilePath, sampel_size, time_interval, l1):
        QThread.__init__(self)
        self.input_file = inputFilePath
        self.output_file = outputFilePath
        self.QUEUE_SIZE = sampel_size
        self.time_interval = time_interval  # unit ms
        self._isRunning = True

        self.analysis_flag = False
        self.starting_index = 0
        self.l1 = l1
        self.storage = []
        self.x_axis = []
        self.y_axis = []

        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(1, 1, 1)
        self.lock = False

        ani = animation.FuncAnimation(self.fig, self.animate, interval=1000)
        plt.show()

    # return a generator of a file
    def file_generator(self, thefile):
        # define file pointer when operating over an open file
        # fp.seek(offset, from_what)
        thefile.seek(0, 2)

        while True:
            # If the file_generator hits EOF before obtaining size bytes, then it reads only available bytes.
            line = thefile.read(4)
            if not line:
                # time.sleep(0.1)
                continue
            yield line

    def run(self):
        # open input binary file
        self.input_file = open(self.input_file, 'r')

        # open output txt file
        self.output_file = open(self.output_file, 'w')
        #
        generator = self.file_generator(self.input_file)
        self.avg_display(generator)
        #
        self.output_file.close()
        print "Stop"

    def avg_display(self, fileGenerator):

        sum = 0.0
        sampleCount = 0
        printerCount = 1
        timmer = 0.0  # unit:s

        for data in fileGenerator:

            if self._isRunning == False:
                break

            data_float = struct.unpack('f', data)


            if sampleCount < self.QUEUE_SIZE:
                sampleCount = sampleCount + 1
                sum = sum + data_float[0]
            else:
                sum = sum + data_float[0]

                text = "%.3f    %.2f\n" % (timmer, sum / self.QUEUE_SIZE)
                self.output_file.write(text)

                #fill the list for plotting
                if(self.lock == False):
                    self.x_axis.append(sum / self.QUEUE_SIZE)

                if printerCount == 1001:
                    #self.analysis(sum)
                    print text
                    printerCount = 1

                timmer = timmer + self.time_interval / 1000
                printerCount = printerCount + 1
                sum = 0.0
                sampleCount = 0

    def stop(self):
        self._isRunning = False

    def animate(self,i):
        total_data = 1000
        while(len(self.x_axis)< total_data):
            pass

        self.lock = True
        power_data = sorted(self.x_axis)  # sorted

        ######
        i = 0
        while (i < len(power_data)):
            self.x_axis.append(power_data[i])
            self.y_axis.append(1)

            j = i + 1
            while (j < len(power_data)):
                if power_data[i] == power_data[j]:
                    self.y_axis[len(self.y_axis) - 1] = self.y_axis[len(self.y_axis) - 1] + 1
                else:
                    break
                j = j + 1

            i = j

        y_axis = [k / len(self.y_axis) for k in self.y_axis]

        self.ax1.clear()
        self.ax1.plot(self.x_axis, self.y_axis)

        self.x_axis = []
        self.y_axis = []
        self.lock = False

    def analysis(self, data):
        # check if tup is empty
        if (len(self.storage) > 0):
            if (self.analysis_flag == True):
                # check if the increase is reaching the stable
                if (abs(self.storage[len(self.storage) - 1] - data) <= 10):
                    # when increasing is stable, check peek belongs to which category
                    if (abs(self.storage[self.starting_index] - data) > 100):
                        self.l1.setText("solv_272_303")
                        self.analysis_flag = False
                    else:
                        self.l1.setText("285-295")
                        self.analysis_flag = False
            # detect the increase
            elif (self.storage[len(self.storage) - 1] - data >= 10):
                self.analysis_flag = True
                self.starting_index = len(self.storage) - 1
            else:
                # self.analysis_flag = False
                self.l1.setText("Sample Type")
        self.storage.append(data)


class Settings(QtGui.QWidget):
    def __init__(self, parent=None):
        super(Settings, self).__init__(parent)

        settings_layout = QtGui.QFormLayout(self)

        self.btn1 = QPushButton("Choose output file path")
        self.btn1.clicked.connect(self.get_output_file_path)
        self.le1 = QLineEdit()
        settings_layout.addRow(self.btn1, self.le1)

        self.btn2 = QPushButton("Set time interval")
        self.btn2.clicked.connect(self.get_double)
        self.le2 = QLineEdit()
        settings_layout.addRow(self.btn2, self.le2)

        self.setLayout(settings_layout)
        self.setWindowTitle("Settings")

    def get_output_file_path(self):

        output_file_name = QtGui.QFileDialog.getOpenFileName(self, 'Save Output File', "/home")

        if output_file_name:
            print "Set output txt file path %s" % output_file_name
            self.le1.setText(str(output_file_name))

    def get_double(self):

        num, ok = QInputDialog.getDouble(self, "Sampling Time Interval", "Type the sampling time interval \n%s" %
                                         ("Unit: ms, minimum is 0.1ms"),
                                         1.0,
                                         0.1, 10000, 1)
        if ok:
            print "Set data time interval: %0.1f ms" % num
            self.le2.setText(str(num))


class Window(QtGui.QMainWindow):
    def __init__(self):
        # return parent object QMainWindow
        super(Window, self).__init__()
        self.setGeometry(0, 0, 1000, 600)
        self.setWindowTitle("Monitor-Biomindr")
        # set window icon, not work in ubuntu, may work in windows
        # self.setWindowIcon(QtGui.QIcon("biomindr_logo.png"))

        ####
        #### about tab
        about_m = QtGui.QAction("&About", self)
        about_m.setShortcut("Ctrl+A")
        # about_m.triggered.connect()
        #### exit tab
        exit_m = QtGui.QAction("&Exit", self)
        exit_m.setShortcut("Ctrl+Q")
        exit_m.setStatusTip("Close the App")
        exit_m.triggered.connect(self.close_application)

        ######main menu
        self.statusBar()

        main_menu = self.menuBar()

        file_menu = main_menu.addMenu('&File')
        file_menu.addAction("&Display")
        file_menu.addAction(exit_m)

        file_menu = main_menu.addMenu('&About')
        file_menu.addAction(about_m)
        ######

        ######Text window
        self.text_window = QtGui.QTextEdit()
        self.setCentralWidget(self.text_window)
        ######

        self.setting_dialog_window = Settings()

        self.home()

    def closeEvent(self, event):
        event.ignore()
        self.close_application()

    def home(self):
        ###push buttun
        # btn = QtGui.QPushButton("Quit", self)
        # btn.clicked.connect(self.close_application)
        # btn.resize(btn.sizeHint())
        # btn.move(410, 270)

        #### label
        self.l1 = QtGui.QLabel("", self)
        # self.l1.setAlignment(QtCore.Qt.AlignBottom)
        self.l1.setText("Sample Type")
        self.l1.move(900, 575)

        ######tool bar
        ##logo
        comp_logo = QtGui.QAction(QtGui.QIcon('biomindr_logo.png'), 'Company Info', self)
        comp_logo.triggered.connect(self.tb_logo_event)
        ##run
        run_icon = QtGui.QAction(QtGui.QIcon('Go.png'), 'Run', self)
        run_icon.triggered.connect(self.run_event)
        ##stop
        stop_icon = QtGui.QAction(QtGui.QIcon('Stop.png'), 'Stop', self)
        stop_icon.triggered.connect(self.run_event_terminated)
        ##clear screen
        clear_icon = QtGui.QAction(QtGui.QIcon('Clear.png'), 'Clear Screen', self)
        clear_icon.triggered.connect(self.clear_text_window_event)
        ##generate txt file
        generate_txt_icon = QtGui.QAction(QtGui.QIcon('Generate_txt.png'), 'Generate txt', self)
        generate_txt_icon.triggered.connect(self.generate_txt_event)
        ##open file
        open_file_icon = QtGui.QAction(QtGui.QIcon('Open.png'), 'Open File', self)
        open_file_icon.triggered.connect(self.file_open)
        ##save file
        save_file_icon = QtGui.QAction(QtGui.QIcon('Save.png'), 'Save File', self)
        save_file_icon.triggered.connect(self.file_save_event)
        ##setting
        setting_icon = QtGui.QAction(QtGui.QIcon('Settings.ico'), 'Settings', self)
        setting_icon.triggered.connect(self.setting_dialog_event)
        ##
        self.toolBar = self.addToolBar("Tools")
        self.toolBar.addAction(run_icon)
        self.toolBar.addAction(stop_icon)
        self.toolBar.addAction(save_file_icon)
        self.toolBar.addAction(clear_icon)
        self.toolBar.addAction(generate_txt_icon)
        self.toolBar.addAction(open_file_icon)
        self.toolBar.addAction(setting_icon)
        self.toolBar.addAction(comp_logo)
        ######
        self.show()

    def setting_dialog_event(self):
        # print "in function"
        self.setting_dialog_window.move(0, 0)
        self.setting_dialog_window.show()

    @pyqtSlot(str)
    def append_text(self, text):
        self.text_window.moveCursor(QTextCursor.End)
        self.text_window.insertPlainText(text)

    @pyqtSlot()
    def run_event(self):

        # (time, truth) = QInputDialog.getDouble(self, "Sampling Time Interval", "Type the sampling time interval \n%s" %
        #                                              ("Unit: ms, minimum is 0.1ms"),
        #                                                 1.0,
        #                                              0.1, 10000, 0.1)

        # (sample_number, truth) = QInputDialog.getInt(self, "Sample Rate",
        #                                              "Type the sample rate (default is 2^16) \n%s" %
        #                                              ("Range is from 100 to 2147483647"),
        #                                              int(math.pow(2, 16)),
        #                                              10, 2147483647, 1000)

        # choose input binary file path
        # input_file_name = QtGui.QFileDialog.getOpenFileName(self, 'Open File')
        input_file_name = "/home/moez/Desktop/gnu_binary_data/wRx_A_1"

        if not self.setting_dialog_window.le1.text():
            print "Cannot start. Empty output file path, please check settings"
        elif not self.setting_dialog_window.le2.text():
            print "Cannot start. No sample time interval selected, please check settings"
        else:
            time_interval = float(self.setting_dialog_window.le2.text())
            sample_number = numpy.ceil(self.sample_number_cal(time_interval))

            # print ("Selected sampling time interval is %0.1f ms") % time_interval
            # print ("Calculated sampling rate is %i") % sample_number

            self.file_reading_thread = QThread()
            self.read = File_Reading_Save(input_file_name, self.setting_dialog_window.le1.text(), sample_number,
                                          time_interval, self.l1)
            self.read.moveToThread(self.file_reading_thread)
            self.file_reading_thread.started.connect(self.read.run)
            self.file_reading_thread.finished.connect(self.read.stop)
            self.file_reading_thread.start()

    def sample_number_cal(self, desire_time_interval):

        GNURADIO_SAMPLE_RATE = 100000  # unit: samples/s

        raw_data_time_interval = (1 / float(GNURADIO_SAMPLE_RATE)) * 1000  # unit: ms
        return int(desire_time_interval / raw_data_time_interval)

    # close the reading file thread
    def run_event_terminated(self):
        try:
            self.read.stop()
            del self.read
        except AttributeError:
            print "Nothing to stop"

    # open a file in the disk and display in the text window
    def file_open(self):
        name = QtGui.QFileDialog.getOpenFileName(self, 'Open File')
        # 'r' intention to file_generator
        # print name
        if name:
            file = open(name, 'r')

            with file:
                context = file.read()
                self.text_window.setText(context)
        else:
            pass

    def tb_logo_event(self):
        webbrowser.open('http://www.biomindr.com/')

    # clear the text window
    def clear_text_window_event(self):
        self.text_window.clear()

    # convert a binary file to a txt file, can choose the txt file location and name
    def generate_txt_event(self):
        # choice = QtGui.QMessageBox.warning(self, 'Generate Txt Files',
        #                                    "Before process the following procedure, please close the Gnuradio.",
        #                                    QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Yes)
        input_file_name = QtGui.QFileDialog.getOpenFileName(self, 'Choose input binary file')
        if input_file_name:

            # 'r' intention to file_generator
            input_file = open(input_file_name, 'r')

            f = numpy.fromfile(input_file, dtype=numpy.float32)

            info = QtGui.QMessageBox.information(self, 'Info',
                                                 "Convert completed! \nNumber of data converted from raw binary file: %d" % len(
                                                     f),
                                                 QtGui.QMessageBox.Yes)

            output_file_name = QtGui.QFileDialog.getSaveFileName(self, 'Save File')
            print "Generate %s." % output_file_name
            numpy.savetxt(str(output_file_name), f, delimiter=' ', newline='\n', header='', footer='', comments='# ')
        else:
            pass

    ####save the text in text window to a file
    def file_save_event(self):
        name = QtGui.QFileDialog.getSaveFileName(self, 'Save File')
        if name:
            file = open(name, 'w')
            text = self.text_window.toPlainText()
            file.write(text)
            file.close()
        else:
            pass

    ####function to close the application
    def close_application(self):
        choice = QtGui.QMessageBox.question(self, 'Quit',
                                            "Close the application? Remember to close the Gnuradio as well.",
                                            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)
        if choice == QtGui.QMessageBox.Yes:
            sys.exit()
        else:
            pass


def main():
    queue = Queue()
    sys.stdout = WriteStream(queue)

    app = QtGui.QApplication(sys.argv)
    GUI = Window()

    # Create file_reading_thread that will listen on the other end of the queue, and send the text to the textedit in our application
    thread = QThread()
    my_receiver = Receiver(queue)
    my_receiver.mysignal.connect(GUI.append_text)
    my_receiver.moveToThread(thread)
    thread.started.connect(my_receiver.run)
    thread.start()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()