import tkinter as tk
from os.path import dirname
from tkinter import filedialog
from WLC.code_executor.executor import CodeExecutor, DEFAULT_DOCKER_PORT


class Gui(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.master = master
        self.picture = None
        self.docker_ip = None

    # Position the execute button with callback to code execution function
    def init_button(self):
        self.master.title("GUI")
        self.pack(fill=tk.BOTH, expand=1, side=tk.BOTTOM)
        quit_button = tk.Button(self.master, text="Execute", command=lambda: self.execute_code(self.picture))
        quit_button.pack(side=tk.TOP)

    # Execute code and display text field accordingly
    def execute_code(self, picture):
        unfixed_code, fixed_code, result, error = CodeExecutor(self.docker_ip, DEFAULT_DOCKER_PORT).execute_code_img(picture)
        self.display_ocr(unfixed_code, fixed_code)
        self.display_output(result, error)

    # Set up text field for OCR output
    def display_ocr(self, unfixed_code, fixed_code):
        text = tk.Text(self.master, height=14, width=70)
        text.pack(side=tk.LEFT, fill=tk.Y)
        text.insert(tk.INSERT, "UNFIXED CODE READ BY OCR: \n")
        text.insert(tk.END, unfixed_code)

        text.insert(tk.INSERT, "\nCODE AFTER FIXING: \n")
        text.insert(tk.END, fixed_code)

    # Set up text field for code execution output
    def display_output(self, result, error):
        text = tk.Text(self.master, height=14, width=70)
        text.pack(side=tk.RIGHT, fill=tk.Y)

        if error:
            text.insert(tk.INSERT, "PROGRAM ERROR: \n")
            text.insert(tk.END, result)
        else:
            text.insert(tk.INSERT, "PROGRAM OUTPUT: \n")
            text.insert(tk.END, result)

    # Get filename of the picture to be open
    def get_picture(self):
        filename = filedialog.askopenfilename(initialdir=dirname(dirname(dirname(__file__))),
                                              title="Select file",
                                              filetypes=(("png files", "*.png"),
                                                         ("jpg files", "*.jpg"),
                                                         ("all files", "*.*")))
        return filename

    # Display chosen picture
    def display_picture(self, path):
        photo = tk.PhotoImage(file=path)
        photo_label = tk.Label(image=photo)
        photo_label.pack(side=tk.TOP)
        photo_label.image = photo

    # Save docker ip
    def save_docker_ip(self, ip):
        self.docker_ip = ip

    # Save picture
    def save_picture(self, picture):
        self.picture = picture

