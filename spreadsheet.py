import cv2 as cv
import numpy as np
import random
import string
import time
import pyttsx3
import tkinter as tk
import os
from tkinter import messagebox
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Google Sheets API setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1y56bOATGzEmlZVMfir7WB2QHs32iyKh7fK5g4FuewJI'  # Corrected Spreadsheet ID
RANGE_NAME = 'Sheet1!A:B'  # Corrected range for Name (A) and Token (B)
CREDENTIALS_FILE = 'asthra-participant-list-55acad99e49d.json'  # Ensure this is the latest JSON file

def init_google_sheets():
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        logging.info("Google Sheets API initialized successfully")
        return service
    except Exception as e:
        logging.error(f"Failed to initialize Google Sheets API: {e}")
        return None

sheets_service = init_google_sheets()

# Initialize text-to-speech engine
try:
    engine = pyttsx3.init()
    logging.info("Text-to-speech engine initialized")
except Exception as e:
    logging.error(f"Failed to initialize text-to-speech: {e}")
    exit()

# Load Haar cascade classifiers
try:
    face_cascade = cv.CascadeClassifier(cv.data.haarcascades + 'haarcascade_frontalface_default.xml')
    smile_cascade = cv.CascadeClassifier(cv.data.haarcascades + 'haarcascade_smile.xml')
    if face_cascade.empty() or smile_cascade.empty():
        raise ValueError("Failed to load cascade classifiers")
    logging.info("Haar cascade classifiers loaded")
except Exception as e:
    logging.error(f"Error loading cascades: {e}")
    exit()

# Load background images
try:
    start_image = cv.imread('Background/Desktop Inital.png')
    smile_image = cv.imread('Background/Desktop input.png')
    final_bg = cv.imread('Background/Desktop final.png')
    if start_image is None or smile_image is None or final_bg is None:
        raise FileNotFoundError("One or more background images not found")
    logging.info("Background images loaded")
except Exception as e:
    logging.error(f"Error loading background images: {e}")
    exit()

# Configuration
ROI_X, ROI_Y = 645, 130
ROI_WIDTH, ROI_HEIGHT = 630, 530
FRAME_W, FRAME_H = 666, 887
FRAME_POS = (1920 - FRAME_W - 150, 100)

# State machine constants
START, SMILE_SCREEN, FACE_RECOGNITION, FINAL_DISPLAY = 0, 1, 2, 3

# Global variables
current_state = START
smile_detected = False
participant_name = ""
captured_frame = None
player_token = ""
name_dialog_opened = False
smile_start_time = None
final_display_start_time = None
show_restart_button = False

# Initialize Tkinter
root = tk.Tk()
root.withdraw()
logging.info("Tkinter initialized")

# Configure main window
try:
    cv.namedWindow('Monitoring', cv.WINDOW_NORMAL)
    cv.setWindowProperty('Monitoring', cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)
    cv.setWindowProperty('Monitoring', cv.WND_PROP_TOPMOST, 1)
    logging.info("OpenCV window configured")
except Exception as e:
    logging.error(f"Error configuring OpenCV window: {e}")
    exit()

# Webcam setup
try:
    cap = cv.VideoCapture(0)
    if not cap.isOpened():
        raise ValueError("Could not open webcam")
    cap.set(cv.CAP_PROP_FRAME_WIDTH, ROI_WIDTH)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, ROI_HEIGHT)
    logging.info("Webcam initialized")
except Exception as e:
    logging.error(f"Error initializing webcam: {e}")
    exit()

def generate_token(length=3):
    return ''.join(random.choices(string.digits, k=length))

def append_to_google_sheets(name, token):
    if sheets_service is None:
        logging.error("Google Sheets service not available - skipping append")
        return
    try:
        values = [[name, token]]
        body = {'values': values}
        logging.debug(f"Appending data to Google Sheets: {values}")
        result = sheets_service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption='RAW',
            body=body
        ).execute()
        logging.info(f"Successfully appended {name}, {token} to Google Sheets: {result}")
    except Exception as e:
        logging.error(f"Error appending to Google Sheets: {e}")

def detect_face_and_smile(frame):
    global smile_detected, captured_frame
    smile_detected = False
    try:
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        frame_copy = frame.copy()  # Initialize frame_copy here
        if len(faces) > 0:
            x, y, w, h = faces[0]
            shape_type = random.choice(['square', 'triangle', 'circle'])
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            
            if shape_type == 'square':
                cv.rectangle(frame_copy, (x, y), (x+w, y+h), color, 3)
            elif shape_type == 'triangle':
                pt1 = (x + w//2, y)
                pt2 = (x, y+h)
                pt3 = (x+w, y+h)
                cv.drawContours(frame_copy, [np.array([pt1, pt2, pt3])], 0, color, 3)
            elif shape_type == 'circle':
                cv.circle(frame_copy, (x+w//2, y+h//2), min(w,h)//2, color, 3)
            
            captured_frame = frame_copy[y:y+h, x:x+w]
            if len(smile_cascade.detectMultiScale(gray[y:y+h, x:x+w], 1.8, 20)) > 0:
                smile_detected = True
        return frame_copy
    except Exception as e:
        logging.error(f"Error in detect_face_and_smile: {e}")
        return frame

def open_name_dialog():
    global participant_name, player_token, name_dialog_opened
    if name_dialog_opened: return

    name_window = tk.Toplevel(root)
    name_window.title("Player Registration")
    
    dialog_width, dialog_height = 400, 150
    x_pos = ROI_X + (ROI_WIDTH - dialog_width) // 2
    y_pos = ROI_Y + ROI_HEIGHT + 20
    
    name_window.geometry(f"{dialog_width}x{dialog_height}+{x_pos}+{y_pos}")
    name_window.resizable(False, False)
    name_window.configure(bg='#2c3e50')
    name_window.attributes('-topmost', True)

    tk.Label(name_window, text="ENTER PLAYER NAME:", 
            font=('Arial', 14, 'bold'), bg='#2c3e50', fg='#ecf0f1').pack(pady=10)
    
    name_entry = tk.Entry(name_window, font=('Arial', 14), width=22)
    name_entry.pack(pady=5)
    
    def save_name():
        global participant_name, player_token, name_dialog_opened
        temp_name = name_entry.get().strip()
        if not temp_name:
            messagebox.showwarning("Input Error", "Please enter a name!")
            return
        
        participant_name = temp_name
        player_token = generate_token()
        picture_path = f"captures/{player_token}.png"
        
        if captured_frame is not None:
            if not os.path.exists("captures"):
                os.makedirs("captures")
            cv.imwrite(picture_path, captured_frame)
            logging.info(f"Saved image: {picture_path}")
        
        # Append to Google Sheets
        append_to_google_sheets(participant_name, player_token)
        
        name_dialog_opened = False
        name_window.destroy()
    
    tk.Button(name_window, text="START GAME", command=save_name,
             bg='#27ae60', fg='white', font=('Arial', 12, 'bold'),
             width=12).pack(pady=5)
    
    name_dialog_opened = True
    name_window.focus_force()

def show_final_display():
    global show_restart_button
    display_frame = final_bg.copy()
    
    if captured_frame is not None:
        resized_capture = cv.resize(captured_frame, (FRAME_W, FRAME_H))
        display_frame[FRAME_POS[1]:FRAME_POS[1]+FRAME_H, 
                    FRAME_POS[0]:FRAME_POS[0]+FRAME_W] = resized_capture
        
        text_y = FRAME_POS[1] + 50
        cv.putText(display_frame, f"NAME: {participant_name.upper()}",
                  (FRAME_POS[0] + 50, text_y), 
                  cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        cv.putText(display_frame, f"TOKEN: {player_token}",
                  (FRAME_POS[0] + 50, text_y + 100), 
                  cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    if show_restart_button:
        button_text = "RESTART"
        font = cv.FONT_HERSHEY_SIMPLEX
        font_scale = 1.5
        thickness = 2
        (text_width, text_height), _ = cv.getTextSize(button_text, font, font_scale, thickness)
        
        button_x = (1920 - text_width) // 2
        button_y = (1080 - text_height) // 2
        
        padding = 20
        cv.rectangle(display_frame, 
                    (button_x - padding, button_y - padding - text_height),
                    (button_x + text_width + padding, button_y + padding),
                    (0, 255, 0), -1)
        
        cv.putText(display_frame, button_text, 
                  (button_x, button_y), 
                  font, font_scale, (255, 255, 255), thickness)
    
    return display_frame

def reset_to_start():
    global current_state, smile_detected, participant_name, captured_frame, player_token, name_dialog_opened, final_display_start_time, show_restart_button
    current_state = START
    smile_detected = False
    participant_name = ""
    captured_frame = None
    player_token = ""
    name_dialog_opened = False
    final_display_start_time = None
    show_restart_button = False
    logging.info("Reset to START state")

def mouse_callback(event, x, y, flags, param):
    global current_state
    if current_state == FINAL_DISPLAY and show_restart_button and event == cv.EVENT_LBUTTONDOWN:
        button_text = "RESTART"
        font = cv.FONT_HERSHEY_SIMPLEX
        font_scale = 1.5
        thickness = 2
        (text_width, text_height), _ = cv.getTextSize(button_text, font, font_scale, thickness)
        
        button_x = (1920 - text_width) // 2
        button_y = (1080 - text_height) // 2
        padding = 20
        
        if (button_x - padding <= x <= button_x + text_width + padding and 
            button_y - padding - text_height <= y <= button_y + padding):
            reset_to_start()

cv.setMouseCallback('Monitoring', mouse_callback)

# Main loop
logging.info("Starting main loop")
while True:
    try:
        root.update()
        
        if current_state == START:
            cv.imshow('Monitoring', start_image)
            key = cv.waitKey(1)
            logging.debug(f"Key pressed: {key}")
            if key == ord(' '):
                current_state = SMILE_SCREEN
                smile_start_time = time.time()
                logging.info("Spacebar pressed - Transition to SMILE_SCREEN")
        
        elif current_state == SMILE_SCREEN:
            ret, frame = cap.read()
            if not ret:
                logging.error("Failed to read frame from webcam")
                cv.imshow('Monitoring', smile_image)
                continue
            
            cv.imshow('Monitoring', smile_image)
            frame = cv.flip(frame, 1)
            frame = detect_face_and_smile(frame)
            
            if time.time() - smile_start_time > 3:
                engine.say("Please smile!")
                engine.runAndWait()
                smile_start_time = time.time()
                logging.debug("Voice prompt triggered")
            
            if smile_detected:
                current_state = FACE_RECOGNITION
                open_name_dialog()
                logging.info("Smile detected - Transition to FACE_RECOGNITION")
        
        elif current_state == FACE_RECOGNITION:
            bg_image = cv.imread('Background/new.png')
            if bg_image is None:
                logging.error("Failed to load new.png")
                break
            ret, frame = cap.read()
            
            if not ret:
                logging.error("Failed to read frame from webcam")
                continue
            
            frame = cv.flip(frame, 1)
            frame = detect_face_and_smile(frame)
            
            frame_resized = cv.resize(frame, (ROI_WIDTH, ROI_HEIGHT))
            bg_image[ROI_Y:ROI_Y+ROI_HEIGHT, ROI_X:ROI_X+ROI_WIDTH] = frame_resized
            
            if participant_name:
                text = f"Player: {participant_name}"
                (tw, th), _ = cv.getTextSize(text, cv.FONT_HERSHEY_SIMPLEX, 1.2, 2)
                text_x = ROI_X + (ROI_WIDTH - tw) // 2
                text_y = ROI_Y + ROI_HEIGHT + 50
                cv.putText(bg_image, text, (text_x, text_y),
                          cv.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
            
            cv.imshow('Monitoring', bg_image)
            
            if participant_name and player_token:
                current_state = FINAL_DISPLAY
                final_display_start_time = time.time()
                logging.info("Name and token set - Transition to FINAL_DISPLAY")
        
        elif current_state == FINAL_DISPLAY:
            if final_display_start_time and time.time() - final_display_start_time > 5:
                show_restart_button = True
            
            display_frame = show_final_display()
            cv.imshow('Monitoring', display_frame)

        key = cv.waitKey(1)
        if key == ord('q'):
            logging.info("Quitting program")
            break

    except Exception as e:
        logging.error(f"Error in main loop: {e}")
        break

# Cleanup
cap.release()
cv.destroyAllWindows()
root.destroy()
logging.info("Program terminated")