import cv2 as cv
import numpy as np
import time # Added for timer

import pyttsx3
engine = pyttsx3.init() # Initialize text-to-speech engine


# Load Haar cascade classifiers for face and smile detection
face_cascade = cv.CascadeClassifier(cv.data.haarcascades + 'haarcascade_frontalface_default.xml')
smile_cascade = cv.CascadeClassifier(cv.data.haarcascades + 'haarcascade_smile.xml')


# Load images (Only Start and Smile images are needed initially)
start_image = cv.imread('Background/Desktop Inital.png')  # Replace with your actual file path
smile_image = cv.imread('Background/Desktop Squid Game.png')  # Replace with your actual file path
#recognition_image = cv.imread('White Screen.png')  # Replace with your actual file path (NOT USED directly)


if start_image is None or smile_image is None: # removed recognition_image
    print("Error: Could not load one or more images. Check file paths.")
    exit()


# State machine states
START = 0
SMILE_SCREEN = 1
FACE_RECOGNITION = 2

current_state = START

# Function to detect faces and smiles
def detect_face_and_smile(frame):
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        #cv.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

        roi_gray = gray[y:y+h, x:x+w]
        roi_color = frame[y:y+h, x:x+w]

        smiles = smile_cascade.detectMultiScale(roi_gray, 1.8, 20)

        for (sx, sy, sw, sh) in smiles:
            #cv.rectangle(roi_color, (sx, sy), (sx+sw, sy+sh), (0, 255, 0), 2)
            return True  # Smile detected

    return False  # No smile detected


# Main loop
cap = cv.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open webcam")
    exit()

cap.set(3, 630)  # Or a different resolution
cap.set(4, 530)

# --- Define the region of interest (ROI) in the background image ---
roi_x = 645   # X-coordinate of the top-left corner of the ROI (adjust as needed)
roi_y = 130  # Y-coordinate of the top-left corner of the ROI (adjust as needed)
roi_width = 630   # Width of the ROI.  Use the webcam width or a desired merged width
roi_height = 530  # Height of the ROI. Use the webcam height or a desired merged height


cv.namedWindow('Monitoring', cv.WINDOW_NORMAL)
cv.setWindowProperty('Monitoring', cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)

smile_start_time = None  # Initialize smile start time

while True:
    if current_state == START:
        cv.imshow('Monitoring', start_image)
        key = cv.waitKey(1)
        if key == ord(' '):  # Spacebar to advance
            current_state = SMILE_SCREEN
            smile_start_time = time.time() # start the time when you enter SMILE_SCREEN

    elif current_state == SMILE_SCREEN:
        print("Current state: SMILE_SCREEN")
        cv.imshow('Monitoring', smile_image)
        success, frame = cap.read()  # Capture frame
        if not success:
            print("Error reading from webcam")
            break

        frame = cv.flip(frame, 1)
        if detect_face_and_smile(frame):
            current_state = FACE_RECOGNITION
            print("Smile detected! Transitioning to FACE_RECOGNITION")
            smile_start_time = None # Reset time when smile detected
        else: # Smile not detected
            elapsed_time = time.time() - smile_start_time
            if elapsed_time > 5:  # Speak prompt after 5 seconds
                engine.say("Please smile!")
                engine.runAndWait() # blocking call
                smile_start_time = time.time()  # Reset timer

    elif current_state == FACE_RECOGNITION:
        print("Current state: FACE_RECOGNITION")
        # --- Webcam Overlay Code Starts Here ---

        # Load the background image (load it here, only when needed)
        image_background = cv.imread('Background/Desktop Squid Game.png')
        if image_background is None:
            print("Error: Could not load image. Please check the file path.")
            exit()
        image_background = cv.resize(image_background, (1920, 1080))

        success, frame = cap.read()  # Capture webcam frame HERE! VERY IMPORTANT!
        if not success:
            print("Error: Could not read frame from webcam.")
            break

        frame = cv.flip(frame, 1)

        # Resize the frame to fit the ROI dimensions
        frame_resized = cv.resize(frame, (roi_width, roi_height))

        # Get the frame dimensions
        frame_height, frame_width, _ = frame_resized.shape

        # Calculate the center offset
        x_offset = (roi_width - frame_width) // 2
        y_offset = (roi_height - frame_height) // 2

        # Create a black border on frame_resized to fit the ROI dimensions
        border_top = y_offset
        border_bottom = y_offset
        border_left = x_offset
        border_right = x_offset
        frame_with_border = cv.copyMakeBorder(frame_resized, border_top, border_bottom, border_left, border_right,
                                           cv.BORDER_CONSTANT, value=[0, 0, 0])

        # Calculate the valid region to copy to avoid exceeding image boundaries
        bg_height, bg_width, _ = image_background.shape

        # Copy the valid region of the webcam feed to the background
        image_background[roi_y:roi_y + roi_height, roi_x:roi_x + roi_width] = frame_with_border

        # Display the combined image
        cv.imshow('Monitoring', image_background)

        # --- Webcam Overlay Code Ends Here ---


    key = cv.waitKey(1) # Check for quit

    if key == ord('q'):
        break


cap.release()  # Release webcam
cv.destroyAllWindows()