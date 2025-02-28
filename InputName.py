import cv2 as cv
import numpy as np
import random
import time
import pyttsx3
import tkinter as tk

# Initialize text-to-speech engine
engine = pyttsx3.init()

# Load Haar cascade classifiers
face_cascade = cv.CascadeClassifier(cv.data.haarcascades + 'haarcascade_frontalface_default.xml')
smile_cascade = cv.CascadeClassifier(cv.data.haarcascades + 'haarcascade_smile.xml')

# Load background images
start_image = cv.imread('Background/Desktop Inital.png')
smile_image = cv.imread('Background/Desktop input.png')

if start_image is None or smile_image is None:
    print("Error: Could not load background images")
    exit()

# State machine constants
START = 0
SMILE_SCREEN = 1
FACE_RECOGNITION = 2

# Global variables
current_state = START
smile_detected = False
participant_name = ""
name_dialog_opened = False
smile_start_time = None

# ROI dimensions for webcam overlay
roi_x = 645
roi_y = 130
roi_width = 630
roi_height = 530

# Initialize Tkinter
root = tk.Tk()
root.withdraw()

# Create main window
cv.namedWindow('Monitoring', cv.WINDOW_NORMAL)
cv.setWindowProperty('Monitoring', cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)

# Webcam initialization
cap = cv.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam")
    exit()

cap.set(3, 630)
cap.set(4, 530)

def detect_face_and_smile(frame):
    global smile_detected
    smile_detected = False
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) > 0:
        (x, y, w, h) = faces[0]
        shape_type = random.choice(['square', 'triangle', 'circle'])
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        
        if shape_type == 'square':
            cv.rectangle(frame, (x, y), (x + w, y + h), color, 3)
        elif shape_type == 'triangle':
            pt1 = (x + w // 2, y)
            pt2 = (x, y + h)
            pt3 = (x + w, y + h)
            cv.drawContours(frame, [np.array([pt1, pt2, pt3])], 0, color, 3)
        elif shape_type == 'circle':
            cv.circle(frame, (x + w//2, y + h//2), min(w, h)//2, color, 3)

        roi_gray = gray[y:y+h, x:x+w]
        smiles = smile_cascade.detectMultiScale(roi_gray, 1.8, 20)
        if len(smiles) > 0:
            smile_detected = True

def open_name_dialog():
    global participant_name, name_dialog_opened
    
    if not name_dialog_opened:
        name_window = tk.Toplevel(root)
        name_window.title("Participant Registration")
        
        # Position dialog below webcam feed
        dialog_width = 400
        dialog_height = 150
        x_pos = roi_x + (roi_width - dialog_width) // 2
        y_pos = roi_y + roi_height + 20
        
        name_window.geometry(f"{dialog_width}x{dialog_height}+{x_pos}+{y_pos}")
        name_window.resizable(False, False)
        name_window.attributes('-topmost', True)
        name_window.configure(bg='#2c3e50')
        
        def on_closing():
            global name_dialog_opened
            name_dialog_opened = False
            name_window.destroy()
            
        name_window.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Custom styling
        tk.Label(name_window, text="Enter Player Name:", 
                font=('Arial', 14, 'bold'), bg='#2c3e50', fg='#ecf0f1').pack(pady=10)
        
        name_entry = tk.Entry(name_window, font=('Arial', 14), width=22)
        name_entry.pack(pady=5)
        
        def save_name():
            global participant_name, name_dialog_opened
            participant_name = name_entry.get()
            name_dialog_opened = False
            name_window.destroy()
            
        tk.Button(name_window, text="START GAME", command=save_name, 
                 bg='#27ae60', fg='white', font=('Arial', 12, 'bold'),
                 width=12).pack(pady=5)
        
        name_dialog_opened = True
        name_window.focus_force()

# Main loop
while True:
    root.update()
    
    if current_state == START:
        cv.imshow('Monitoring', start_image)
        key = cv.waitKey(1)
        if key == ord(' '):
            current_state = SMILE_SCREEN
            smile_start_time = time.time()
            
    elif current_state == SMILE_SCREEN:
        cv.imshow('Monitoring', smile_image)
        ret, frame = cap.read()
        if ret:
            frame = cv.flip(frame, 1)
            detect_face_and_smile(frame)
            
            if time.time() - smile_start_time > 5:
                engine.say("Please smile!")
                engine.runAndWait()
                smile_start_time = time.time()
                
            if smile_detected:
                current_state = FACE_RECOGNITION
                open_name_dialog()
                
    elif current_state == FACE_RECOGNITION:
        bg_image = cv.imread('Background/new.png')
        ret, frame = cap.read()
        
        if ret:
            frame = cv.flip(frame, 1)
            detect_face_and_smile(frame)
            
            # Webcam overlay
            frame_resized = cv.resize(frame, (roi_width, roi_height))
            bg_image[roi_y:roi_y+roi_height, roi_x:roi_x+roi_width] = frame_resized
            
            # Add participant name below video frame
            if participant_name:
                text = f"Player: {participant_name}"
                font = cv.FONT_HERSHEY_SIMPLEX
                font_scale = 1.2
                thickness = 2
                
                # Calculate text position
                (text_width, text_height), _ = cv.getTextSize(text, font, font_scale, thickness)
                text_x = roi_x + (roi_width - text_width) // 2
                text_y = roi_y + roi_height + 50
                
                cv.putText(bg_image, text, (text_x, text_y),
                          font, font_scale, (255, 255, 255), thickness, cv.LINE_AA)
            
            cv.imshow('Monitoring', bg_image)
            
            if not name_dialog_opened and not participant_name:
                open_name_dialog()

    key = cv.waitKey(1)
    if key == ord('q'):
        break

# Cleanup
cap.release()
cv.destroyAllWindows()
root.destroy()