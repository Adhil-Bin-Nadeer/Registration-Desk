import cv2 as cv
import numpy as np
import random
import string
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
final_bg = cv.imread('Background/Desktop final.png')

if start_image is None or smile_image is None or final_bg is None:
    print("Error: Could not load background images")
    exit()

# Configuration
ROI_X, ROI_Y = 645, 130
ROI_WIDTH, ROI_HEIGHT = 630, 530
FRAME_W, FRAME_H = 666, 887
FRAME_POS = (1920 - FRAME_W - 150, 100)  # Right side position

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

# Configure main window
cv.namedWindow('Monitoring', cv.WINDOW_NORMAL)
cv.setWindowProperty('Monitoring', cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)

# Webcam setup
cap = cv.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam")
    exit()
cap.set(3, ROI_WIDTH)
cap.set(4, ROI_HEIGHT)

def generate_token(length=3):
    return ''.join(random.choices(string.digits, k=length))

def detect_face_and_smile(frame):
    global smile_detected, captured_frame
    smile_detected = False
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) > 0:
        x, y, w, h = faces[0]
        shape_type = random.choice(['square', 'triangle', 'circle'])
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        
        # Draw shape on face
        frame_copy = frame.copy()
        if shape_type == 'square':
            cv.rectangle(frame_copy, (x, y), (x+w, y+h), color, 3)
        elif shape_type == 'triangle':
            pt1 = (x + w//2, y)
            pt2 = (x, y+h)
            pt3 = (x+w, y+h)
            cv.drawContours(frame_copy, [np.array([pt1, pt2, pt3])], 0, color, 3)
        elif shape_type == 'circle':
            cv.circle(frame_copy, (x+w//2, y+h//2), min(w,h)//2, color, 3)
        
        # Capture face with shape
        captured_frame = frame_copy[y:y+h, x:x+w]
        
        # Check for smiles
        if len(smile_cascade.detectMultiScale(gray[y:y+h, x:x+w], 1.8, 20)) > 0:
            smile_detected = True
    return frame_copy

def open_name_dialog():
    global participant_name, player_token, name_dialog_opened
    if name_dialog_opened: return

    name_window = tk.Toplevel(root)
    name_window.title("Player Registration")
    
    # Position dialog below webcam feed
    dialog_width, dialog_height = 400, 150
    x_pos = ROI_WIDTH - 80
    y_pos = ROI_Y + ROI_HEIGHT -70
    
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
        participant_name = name_entry.get()
        player_token = generate_token()
        name_dialog_opened = False
        if captured_frame is not None:
            cv.imwrite(f"captures/{player_token}.png", captured_frame)
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
        # Resize and position captured image
        resized_capture = cv.resize(captured_frame, (FRAME_W, FRAME_H))
        display_frame[FRAME_POS[1]:FRAME_POS[1]+FRAME_H, 
                    FRAME_POS[0]:FRAME_POS[0]+FRAME_W] = resized_capture
        
        # Add text information
        text_y = FRAME_POS[1] + 50
        cv.putText(display_frame, f"NAME: {participant_name.upper()}",
                  (FRAME_POS[0] + 50, text_y), 
                  cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        cv.putText(display_frame, f"TOKEN: {player_token}",
                  (FRAME_POS[0] + 50, text_y + 100), 
                  cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Add restart button after 5 seconds
    if show_restart_button:
        button_text = "RESTART"
        font = cv.FONT_HERSHEY_SIMPLEX
        font_scale = 1.5
        thickness = 2
        (text_width, text_height), _ = cv.getTextSize(button_text, font, font_scale, thickness)
        
        # Center the button
        button_x = (1920 - text_width) // 2  # Assuming 1920 is screen width
        button_y = (1080 - text_height)   # Assuming 1080 is screen height
        
        # Draw button rectangle
        padding = 20
        cv.rectangle(display_frame, 
                    (button_x - padding, button_y - padding - text_height),
                    (button_x + text_width + padding, button_y + padding),
                    (0, 255, 0), -1)  # Green button
        
        # Draw button text
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

def mouse_callback(event, x, y, flags, param):
    global current_state
    if current_state == FINAL_DISPLAY and show_restart_button and event == cv.EVENT_LBUTTONDOWN:
        button_text = "RESTART"
        font = cv.FONT_HERSHEY_SIMPLEX
        font_scale = 1.5
        thickness = 2
        (text_width, text_height), _ = cv.getTextSize(button_text, font, font_scale, thickness)
        
        button_x = (1920 - text_width) // 2
        button_y = (1080 - text_height) 
        padding = 20
        
        if (button_x - padding <= x <= button_x + text_width + padding and 
            button_y - padding - text_height <= y <= button_y + padding):
            reset_to_start()

# Set mouse callback
cv.setMouseCallback('Monitoring', mouse_callback)

# Main loop
while True:
    root.update()
    
    if current_state == START:
        cv.imshow('Monitoring', start_image)
        if cv.waitKey(1) == ord(' '):
            current_state = SMILE_SCREEN
            smile_start_time = time.time()
    
    elif current_state == SMILE_SCREEN:
        cv.imshow('Monitoring', smile_image)
        ret, frame = cap.read()
        
        if ret:
            frame = cv.flip(frame, 1)
            frame = detect_face_and_smile(frame)
            
            # Voice prompt every 3 seconds
            if time.time() - smile_start_time > 3:
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
            frame = detect_face_and_smile(frame)
            
            # Webcam overlay
            frame_resized = cv.resize(frame, (ROI_WIDTH, ROI_HEIGHT))
            bg_image[ROI_Y:ROI_Y+ROI_HEIGHT, ROI_X:ROI_X+ROI_WIDTH] = frame_resized
            
            # Add temporary name display
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
    
    elif current_state == FINAL_DISPLAY:
        if final_display_start_time and time.time() - final_display_start_time > 5:
            show_restart_button = True
        
        display_frame = show_final_display()
        cv.imshow('Monitoring', display_frame)

    key = cv.waitKey(1)
    if key == ord('q'):
        break

# Cleanup
cap.release()
cv.destroyAllWindows()
root.destroy()