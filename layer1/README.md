# Autonomous Face and Human Tracker

This project uses YOLO models to track faces and humans in real-time using a webcam. It also controls servo motors to adjust the camera's position based on detected objects.

## Features

- Detects and tracks faces using the `yolov8n-face` model.
- Detects and tracks humans using the `yolov8n` model.
- Controls servo motors to follow detected objects.
- Switches between face tracking and human searching modes.
- Performs random idle movements when no objects are detected.

## Requirements

- Python 3.7 or higher
- OpenCV
- NumPy
- Requests
- Ultralytics YOLO

## Installation

1. Clone this repository.
2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure your webcam is connected and accessible.

## Usage

1. Run the script:
   ```bash
   python main.py
   ```
2. Press `q` to quit the application.


## Troubleshooting

- If the webcam feed does not appear, check your webcam connection and permissions.
- If motor commands fail, verify the motor controller's IP address and network connectivity.
