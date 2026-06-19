import os

import cv2

import mediapipe as mp



mp_face_detection = mp.solutions.face_detection

face_detector_close = mp_face_detection.FaceDetection(min_detection_confidence=0.8, model_selection=0)
face_detector_far = mp_face_detection.FaceDetection(min_detection_confidence=0.7, model_selection=1)



def extract_faces(image):

    if image is None:

        print("Error: image is None")

        return []



    height, width = image.shape[:2]

    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    

    boxes = []

    

    crops = [(0, 0, width, height)]

    

    if width > 600 and height > 600:
        # We removed the slicing because cutting images into pieces causes MediaPipe 
        # to hallucinate faces in calligraphy and shapes. We rely on face_detector_far instead.
        pass
    

    for qx, qy, qw, qh in crops:

        crop_img = rgb_image[qy:qh, qx:qw]

        res_close = face_detector_close.process(crop_img)

        res_far = face_detector_far.process(crop_img)

        

        all_detections = []

        if res_close.detections: all_detections.extend(res_close.detections)

        if res_far.detections: all_detections.extend(res_far.detections)

        

        if all_detections:

            for detection in all_detections:

                bbox = detection.location_data.relative_bounding_box

                

                c_w = int(bbox.width * (qw - qx))

                c_h = int(bbox.height * (qh - qy))

                c_x = int(bbox.xmin * (qw - qx))

                c_y = int(bbox.ymin * (qh - qy))

                

                x = c_x + qx

                y = c_y + qy

                

                if c_w > 0 and c_h > 0:

                    boxes.append([x, y, c_w, c_h])

    

    if not boxes:
        print("MediaPipe failed. Trying MTCNN for difficult faces...")
        try:
            from mtcnn import MTCNN
            import logging
            logging.getLogger('tensorflow').setLevel(logging.ERROR)
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
            
            mtcnn_detector = MTCNN()
            results = mtcnn_detector.detect_faces(rgb_image)
            for res in results:
                if res['confidence'] > 0.95:
                    x, y, w, h = res['box']
                    boxes.append([max(0, x), max(0, y), w, h])
        except Exception as e:
            print("MTCNN error:", e)

    if not boxes:
        print("Error: no face detected even after fallbacks")
        return []

    

    faces_images = []

    

    scores = [1.0] * len(boxes)

    indices = cv2.dnn.NMSBoxes(boxes, scores, score_threshold=0.3, nms_threshold=0.3)

    

    if len(indices) > 0:

        num_faces = len(indices)

        if num_faces > 1:

            print(f"Group photo detected! Found {num_faces} faces.")

        else:

            print("Single face detected.")



        for idx, i in enumerate(indices.flatten()):

            x, y, w, h = boxes[i]

            

            pad = 0.25

            x1 = int(x - w * pad)

            y1 = int(y - h * pad)

            x2 = int(x + w + w * pad)

            y2 = int(y + h + h * pad)

            

            x1 = max(0, x1)

            y1 = max(0, y1)

            x2 = min(width, x2)

            y2 = min(height, y2)

            

            face = image[y1:y2, x1:x2]

            

            if face.shape[0] > 0 and face.shape[1] > 0:
                faces_images.append(face)

    print(f"Success: extracted {len(faces_images)} faces")

    return faces_images

