from tkinter import Tk, Label, Entry, Button, StringVar, Radiobutton, IntVar
from utils.research_gate_publication_spider import research_publication
from utils.research_gate_questions_spider import research_question

class MyGUI:
    def __init__(self, master):
        self.master = master
        master.title("輸入資訊")

        self.keyword_label = Label(master, text="Keyword:")
        self.keyword_label.pack()

        self.keyword_var = StringVar()
        self.keyword_entry = Entry(master, textvariable=self.keyword_var)
        self.keyword_entry.pack()

        self.cf_clearance_label = Label(master, text="CF Clearance:")
        self.cf_clearance_label.pack()

        self.cf_clearance_var = StringVar()
        self.cf_clearance_entry = Entry(master, textvariable=self.cf_clearance_var)
        self.cf_clearance_entry.pack()

        self.user_agent_label = Label(master, text="User Agent:")
        self.user_agent_label.pack()

        self.user_agent_var = StringVar()
        self.user_agent_entry = Entry(master, textvariable=self.user_agent_var)
        self.user_agent_entry.pack()
        
        self.option_var = IntVar()
        self.publication_radio = Radiobutton(master, text="Publication", variable=self.option_var, value=1)
        self.publication_radio.pack()
        self.question_radio = Radiobutton(master, text="Question", variable=self.option_var, value=2)
        self.question_radio.pack()

        self.submit_button = Button(master, text="Submit", command=self.submit)
        self.submit_button.pack()

    def submit(self):
        keywords = self.keyword_var.get()
        cf_clearance = self.cf_clearance_var.get()
        user_agent = self.user_agent_var.get()
        option = self.option_var.get()


        if option == 1:
            research_publication(keywords,cf_clearance, user_agent)
        elif option == 2:
            research_question(keywords,cf_clearance, user_agent)
        else:
            results = "Please select an option."

        print('已經完成')
        
