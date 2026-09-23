import cv2
import os

video_path = r"C:\Users\prana\Downloads\Honeybee_AI_Demo\videos\sample.mp4"

print("Looking for:", os.path.abspath(video_path))
print("File exists:", os.path.exists(video_path))

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("ERROR: Could not open the video.")
    print("Check the video path and filename.")
    exit()

fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

if fps <= 0:
    print("ERROR: OpenCV could not read the video FPS.")
    cap.release()
    exit()

duration = total_frames / fps

print("FPS:", fps)
print("Total frames:", total_frames)
print("Resolution:", width, "x", height)
print("Duration:", duration, "seconds")

cap.release()