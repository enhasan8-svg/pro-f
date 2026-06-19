import cv2
import numpy as np
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True)

mp_face_detection = mp.solutions.face_detection
face_detector_close = mp_face_detection.FaceDetection(min_detection_confidence=0.5, model_selection=0)
face_detector_far = mp_face_detection.FaceDetection(min_detection_confidence=0.2, model_selection=1)

def fix_orientation2(image, lm, w, h):
    left_eye = np.array([lm[33].x * w, lm[33].y * h])
    right_eye = np.array([lm[263].x * w, lm[263].y * h])

    eyes_center = (
        (left_eye[0] + right_eye[0]) / 2,
        (left_eye[1] + right_eye[1]) / 2
    )

    dx = right_eye[0] - left_eye[0]
    dy = right_eye[1] - left_eye[1]

    angle = np.degrees(np.arctan2(dy, dx))

    if angle > 0:
        angle = angle - 180
    else:
        angle = angle + 180

    if abs(angle) > 90:
        angle = angle - 180 if angle > 0 else angle + 180

    M = cv2.getRotationMatrix2D(eyes_center, angle, 1.0)

    rotated = cv2.warpAffine(
        image,
        M,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0)
    )

    return rotated


def align_face(img):
    if img is None:
        return None

    h, w = img.shape[:2]

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    res = face_mesh.process(rgb)

    if not res.multi_face_landmarks:
        print("Warning: no face detected for alignment, falling back to unaligned")
        face = cv2.resize(img, (224, 224))
        return face

    lm = res.multi_face_landmarks[0].landmark

    rotated = fix_orientation2(img, lm, w, h)

    rgb2 = cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB)
    det = face_detector_close.process(rgb2)
    if not det.detections:
        det = face_detector_far.process(rgb2)

    if not det.detections:
        print("Warning: no face after rotation, falling back to rotated image")
        face = cv2.resize(rotated, (224, 224))
        return face

    bbox = det.detections[0].location_data.relative_bounding_box

    h2, w2 = rotated.shape[:2]

    x = int(bbox.xmin * w2)
    y = int(bbox.ymin * h2)
    ww = int(bbox.width * w2)
    hh = int(bbox.height * h2)

    pad = 0.35

    x1 = max(0, int(x - ww * pad))
    y1 = max(0, int(y - hh * pad))
    x2 = min(w2, int(x + ww + ww * pad))
    y2 = min(h2, int(y + hh + hh * pad))

    face = rotated[y1:y2, x1:x2]

    face = cv2.resize(face, (224, 224))

    return face
