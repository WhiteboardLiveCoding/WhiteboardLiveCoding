import tkinter
import os

from WLC.code_executor import CodeExecutor, DEFAULT_DOCKER_PORT
from WLC.image_processing.preprocessor import Preprocessor
from tkinter import filedialog
from tkinter import *


class Gui(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.master = master
        self.picture = None
        self.docker_ip = None

    # Position the execute button with callback to code execution function
    def init_button(self):
        self.master.title("GUI")
        self.pack(fill=BOTH, expand=1, side=BOTTOM)
        quit_button = Button(self.master, text="Execute", command=lambda: self.execute_code(self.picture))
        quit_button.place(x=560, y=800)

    # Execute code and display text field accordingly
    def execute_code(self, picture):
        code_executor = CodeExecutor(self.docker_ip, DEFAULT_DOCKER_PORT)
        image = Preprocessor().process(picture)
        code = image.get_code().lower()
        value = code_executor.execute_code(code)
        self.display_ocr(code)
        self.display_output(value)

    # Set up text field for OCR output
    def display_ocr(self, code):
        text = Text(self.master, height=14, width=70)
        text.pack(side=LEFT, fill=Y)
        text.insert(INSERT, "CODE READ BY OCR : \n")
        text.insert(END, code)

    # Set up text field for code execution output
    def display_output(self, code):
        text = Text(self.master, height=14, width=70)
        text.pack(side=RIGHT, fill=Y)
        text.insert(INSERT, "CODE EXECUTED : \n")
        text.insert(END, code)

    # Get filename of the picture to be open
    def get_picture(self):
        filename = filedialog.askopenfilename(initialdir="../../"+os.path.dirname(os.path.realpath(__file__)),
                                              title="Select file",
                                              filetypes=(("png files", "*.png"), ("jpg files", "*.jpg"), ("all files", "*.*")))
        return filename

    # Display chosen picture
    def display_picture(self, path):
        photo = PhotoImage(file=path)
        photo_label = Label(image=photo)
        photo_label.pack(side=TOP)
        photo_label.image = photo

    # Save docker ip
    def save_docker_ip(self, ip):
        self.docker_ip = ip

    # Save picture
    def save_picture(self, picture):
        self.picture = picture

