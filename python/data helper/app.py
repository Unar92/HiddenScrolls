import tkinter as tk
from tkinter import messagebox
import csv
import os

class BrowserDataSaver:
    def __init__(self, root):
        self.root = root
        self.root.title("Browser Data Saver")
        self.root.geometry("300x200")
        
        # Make window always on top
        self.root.attributes('-topmost', True)
        
        # Create input fields
        self.create_widgets()
        
        # CSV file setup
        self.csv_file = "saved_data.csv"
        self.initialize_csv()

    def create_widgets(self):
        # Name field
        tk.Label(self.root, text="Name:").grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = tk.Entry(self.root)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        # Email field
        tk.Label(self.root, text="Email:").grid(row=1, column=0, padx=5, pady=5)
        self.email_entry = tk.Entry(self.root)
        self.email_entry.grid(row=1, column=1, padx=5, pady=5)

        # Website field
        tk.Label(self.root, text="Website URL:").grid(row=2, column=0, padx=5, pady=5)
        self.website_entry = tk.Entry(self.root)
        self.website_entry.grid(row=2, column=1, padx=5, pady=5)

        # Save button
        tk.Button(self.root, text="Save Data", command=self.save_data).grid(row=3, column=0, columnspan=2, pady=10)

        # Clear button
        tk.Button(self.root, text="Clear Fields", command=self.clear_fields).grid(row=4, column=0, columnspan=2, pady=5)

    def initialize_csv(self):
        # Create CSV file with headers if it doesn't exist
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Name", "Email", "Website URL"])

    def save_data(self):
        name = self.name_entry.get()
        email = self.email_entry.get()
        website = self.website_entry.get()

        if not all([name, email, website]):
            messagebox.showwarning("Warning", "Please fill all fields")
            return

        try:
            with open(self.csv_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([name, email, website])
            messagebox.showinfo("Success", "Data saved successfully!")
            self.clear_fields()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data: {str(e)}")

    def clear_fields(self):
        self.name_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)
        self.website_entry.delete(0, tk.END)

def main():
    root = tk.Tk()
    app = BrowserDataSaver(root)
    root.mainloop()

if __name__ == "__main__":
    main()