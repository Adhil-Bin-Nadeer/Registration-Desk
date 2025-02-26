import cv2 as cv
import numpy as np

cap = cv.VideoCapture(0)
cap.set(3, 630)  # Or a different resolution
cap.set(4, 530)

# Load the background image
image_background = cv.imread('figma/Desktop Squid Game.png')

# Check if the image was loaded successfully
if image_background is None:
    print("Error: Could not load image. Please check the file path.")
    exit()

# Resize the background image to 1920x1080
image_background = cv.resize(image_background, (1920, 1080))

# --- Define the region of interest (ROI) in the background image ---
roi_x = 645   # X-coordinate of the top-left corner of the ROI (adjust as needed)
roi_y = 130  # Y-coordinate of the top-left corner of the ROI (adjust as needed)
roi_width = 630   # Width of the ROI.  Use the webcam width or a desired merged width
roi_height = 530  # Height of the ROI. Use the webcam height or a desired merged height

while True:
    success, frame = cap.read()
    if not success:
        print("Error: Could not read frame from webcam.")
        break

    # Flip the frame horizontally (mirror effect)
    frame = cv.flip(frame, 1)  # 1 is the flip code for horizontal flip

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
    frame_with_border = cv.copyMakeBorder(frame_resized, border_top, border_bottom, border_left, border_right, cv.BORDER_CONSTANT, value=[0, 0, 0])

    # Calculate the valid region to copy to avoid exceeding image boundaries
    bg_height, bg_width, _ = image_background.shape

    # Copy the valid region of the webcam feed to the background
    image_background[roi_y:roi_y + roi_height, roi_x:roi_x + roi_width] = frame_with_border

    # Create a named window that allows resizing/fullscreen
    cv.namedWindow('Monitoring', cv.WINDOW_NORMAL)
    cv.setWindowProperty('Monitoring', cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)

    # Display the combined image
    cv.imshow('Monitoring', image_background)
   # cv.imshow('Webcam', frame)  # Original web cam

    k = cv.waitKey(1)
    if k == ord('q'):
        break

cap.release()
cv.destroyAllWindows()