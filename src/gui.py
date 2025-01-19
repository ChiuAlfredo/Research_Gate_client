from tkinter import Button, Entry, IntVar, Label, Radiobutton, StringVar, Tk, messagebox

from utils.research_gate_publication_spider import research_publication,write_history_pub
from utils.research_gate_questions_spider import research_question,write_history_que
import uuid

class MyGUI:
    def __init__(self, master):
        self.master = master
        master.title("輸入資訊")
        # Set window size to 800x600 pixels
        master.geometry("800x600")
        # Allow window resizing
        master.resizable(True, True)

        # Add padding to main window
        master.configure(padx=20, pady=20)

        self.keyword_label = Label(master, text="Keyword:", pady=10)
        self.keyword_label.pack(fill='x')

        self.keyword_var = StringVar()
        self.keyword_entry = Entry(master, textvariable=self.keyword_var, width=150)
        self.keyword_entry.pack(fill='x', padx=20, pady=10)

        self.cf_clearance_label = Label(master, text="CF Clearance:", pady=10)
        self.cf_clearance_label.pack(fill='x')

        self.cf_clearance_var = StringVar()
        self.cf_clearance_entry = Entry(master, textvariable=self.cf_clearance_var, width=150)
        self.cf_clearance_entry.pack(fill='x', padx=20, pady=10)

        self.user_agent_label = Label(master, text="User Agent:", pady=10)
        self.user_agent_label.pack(fill='x')

        self.user_agent_var = StringVar()
        self.user_agent_entry = Entry(master, textvariable=self.user_agent_var, width=150)
        self.user_agent_entry.pack(fill='x', padx=20, pady=10)
        
        self.option_var = IntVar(value=1)
        self.publication_radio = Radiobutton(master, text="Publication", variable=self.option_var, value=1)
        self.publication_radio.pack(pady=10)
        self.question_radio = Radiobutton(master, text="Question", variable=self.option_var, value=2)
        self.question_radio.pack(pady=10)

        self.submit_button = Button(master, text="Submit", command=self.submit)
        self.submit_button.pack(pady=20)

    def show_message(self, message, error=True):
        if error:
            messagebox.showerror("Error", message)
        else:
            messagebox.showinfo("Info", message)

    def submit(self):
        try:
            keywords = self.keyword_var.get().strip()
            cf_clearance = self.cf_clearance_var.get().strip()
            user_agent = self.user_agent_var.get().strip()
            option = self.option_var.get()
            
            # Validate inputs
            if not keywords:
                self.show_message("Please enter keywords")
                return
            if not cf_clearance:
                self.show_message("Please enter CF Clearance")
                return
            if not user_agent:
                self.show_message("Please enter User Agent")
                return

            if option == 1:
                try:
                    trackid = uuid.uuid1().hex
                    research_publication(keywords, cf_clearance, user_agent,trackid)
                    self.show_message("Publication search completed successfully!", False)
                    write_history_pub(keywords,trackid)
                except Exception as e:
                    self.show_message(f"Error in question search: {str(e)}")

            elif option == 2:
                try:
                    trackid = uuid.uuid1().hex
                    research_question(keywords, cf_clearance, user_agent,trackid)
                    self.show_message("Question search completed successfully!", False)
                    write_history_que(keywords,trackid)
                except Exception as e:
                    self.show_message(f"Error in question search: {str(e)}")
            else:
                self.show_message("Please select an option")
                
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            self.show_message(error_message)
            messagebox.showerror("Error", error_message)
