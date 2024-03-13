from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
from pytz import timezone
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os

# URL of your Grafana server
grafana_url = 'http://localhost:3000/connections/datasources/edit/b8a07867-b5e8-48bd-9d57-75068bbe5ba1'

# Function to perform the required actions
def update_data_source():
    # Create the Firefox WebDriver instance
    driver = webdriver.Firefox()

    # Open Grafana URL
    driver.get(grafana_url)

    try:
        # Wait for the username input field to be present
        username_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'user')))
        # Input username
        username_input.send_keys('winteradmin')

        # Find the password input field
        password_input = driver.find_element(By.XPATH,'//*[@id=":r1:"]')
        # Input password
        password_input.send_keys('#SmallHands1')

        # Find the login button and press Enter
        password_input.send_keys(Keys.ENTER)

        #Wait for page to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[1]/div/main/div/div[2]/div[3]/div/div[1]/div/div[3]/form/div[3]/button[2]/span')))
        Save_Test_Button = driver.find_element(By.XPATH, '/html/body/div[1]/div[1]/div/main/div/div[2]/div[3]/div/div[1]/div/div[3]/form/div[3]/button[2]/span')

        # Click on the data source
        Save_Test_Button.click()


        print("New Folder Added, data source updated successfully!")

    finally:
        # Close the browser window
        driver.quit()


class NewFolderHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            update_data_source()

            # Perform your desired action here
            # For example, you can call a function or execute a script
            # Example: process_new_folder(event.src_path)

if __name__ == "__main__":
    # Specify the directory to monitor
    directory_to_watch = "/home/winter/data/rawdir"

    # Create the Observer and set up the event handler
    event_handler = NewFolderHandler()
    observer = Observer()
    observer.schedule(event_handler, path=directory_to_watch, recursive=False)

    # Start the observer
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
