import pywhatkit as pwk
import webbrowser

# Set Opera browser as the default browser for pywhatkit
opera_path = "C:/Program Files/Opera/launcher.exe"  # Update this path if Opera is installed elsewhere
webbrowser.register('opera', None, webbrowser.BackgroundBrowser(opera_path))
webbrowser.get('opera').open_new("https://web.whatsapp.com")

phone_number = "+923362343768"  # Replace with the recipient's phone number
message = "Hello, this is a test message from Python!"
time_hour = 13  # Set the hour (24-hour format) to send the message
time_minute = 55  # Set the minute to send the message

# Send the message using pywhatkit
try:
    pwk.sendwhatmsg(phone_number, message, time_hour, time_minute)
    print(f"Message sent to {phone_number} at {time_hour}:{time_minute}.")
except Exception as e:
    print(f"An error occurred: {e}")

# Note: Ensure Opera is installed and the path is correct.

