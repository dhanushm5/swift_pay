import cv2
import numpy as np
import requests
from ultralytics import YOLO
import time
import random

face_model = YOLO("yolov8n-face.pt")
body_model = YOLO("yolov8n.pt")

cap = cv2.VideoCapture(0)
ws, hs = 640, 480
cap.set(3, ws)
cap.set(4, hs)

motor_url = "http://http://192.168.55.156:8080/motors"
servo_pos = [90, 90]
prev_servo_pos = servo_pos[:]
angle_smoothness = 4
move_threshold = 3
last_motor_update = 0
motor_update_interval = 0.15  

searching = True
search_stage = 0
search_angles = [
    (60, 80), (120, 80),  
    (90, 60), (60, 60), (120, 60),
    (90, 100), (60, 100), (120, 100), 
]
search_pause = 0.5
last_search_move = time.time()
prev_face_position = None 


def send_motor_command(motor1, motor2):
    global last_motor_update
    now = time.time()
    if now - last_motor_update < motor_update_interval:
        return
    url = f"{motor_url}?motor1={int(motor1)}&motor2={int(motor2)}"
    try:
        requests.get(url, timeout=0.2)
        print("Sent:", url)
        last_motor_update = now
    except requests.exceptions.RequestException as e:
        print("Warning: Motor command failed.", e)


def interpolate_servo(fx, fy):
    global servo_pos, prev_servo_pos

    target_x = np.interp(fx, [0, ws], [180, 0])
    target_y = np.interp(fy, [0, hs], [180, 0])
    target_x = np.clip(target_x, 0, 180)
    target_y = np.clip(target_y, 0, 180)

    servo_x = round(servo_pos[0] + (target_x -
                    servo_pos[0]) / angle_smoothness)
    servo_y = round(servo_pos[1] + (target_y -
                    servo_pos[1]) / angle_smoothness)
    servo_pos = [servo_x, servo_y]

    if abs(servo_x - prev_servo_pos[0]) > move_threshold or abs(servo_y - prev_servo_pos[1]) > move_threshold:
        send_motor_command(servo_x, servo_y)
        prev_servo_pos = servo_pos[:]


def random_idle_move():
    if random.random() > 0.95:  
        angle = random.choice(
            [(random.randint(60, 120), random.randint(60, 100))])
        send_motor_command(*angle)
        time.sleep(random.uniform(0.2, 0.5))  


while True:
    ret, frame = cap.read()
    if not ret:
        break

    if not searching:
        results = face_model.predict(frame, conf=0.5, verbose=False)
        boxes = results[0].boxes.xyxy if results and results[0].boxes is not None else [
        ]

        if len(boxes) > 0:
            largest = max(boxes, key=lambda b: (b[2]-b[0]) * (b[3]-b[1]))
            x1, y1, x2, y2 = map(int, largest)
            fx, fy = (x1 + x2) // 2, (y1 + y2) // 2

            if prev_face_position:
                delta_x = fx - prev_face_position[0]
                delta_y = fy - prev_face_position[1]
                servo_pos[0] += delta_x // 3  
                servo_pos[1] += delta_y // 3
            prev_face_position = [fx, fy]

            interpolate_servo(fx, fy)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.circle(frame, (fx, fy), 5, (255, 0, 0), -1)
            cv2.putText(frame, "FACE LOCKED", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            searching = True
            print("Face lost. Switching to search mode.")

    if searching:
        now = time.time()

        if now - last_search_move > search_pause:
            angle = search_angles[search_stage]
            servo_pos[0], servo_pos[1] = angle
            send_motor_command(*angle)
            search_stage = (search_stage + 1) % len(search_angles)
            last_search_move = now

        results = body_model.predict(frame, conf=0.4, verbose=False)
        boxes = results[0].boxes.xyxy if results and results[0].boxes is not None else [
        ]

        person_boxes = [b for i, b in enumerate(boxes)
                        if int(results[0].boxes.cls[i]) == 0]

        if len(person_boxes) > 0:
            largest = max(person_boxes, key=lambda b: (
                b[2]-b[0]) * (b[3]-b[1]))
            x1, y1, x2, y2 = map(int, largest)
            fx, fy = (x1 + x2) // 2, (y1 + y2) // 2
            interpolate_servo(fx, fy)

            searching = False
            print("Human found. Switching to face mode.")
            continue

        cv2.putText(frame, "SEARCHING FOR HUMAN...", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    if searching:
        random_idle_move()

    cv2.imshow("Autonomous Face Tracker", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
