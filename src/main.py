from gui import MyGUI
from tkinter import Tk, Label, Entry, Button, StringVar, Radiobutton, IntVar

def main():
    root = Tk()
    my_gui = MyGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()