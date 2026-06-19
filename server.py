import os
import cv2
import base64
import glob
import io
import uuid
import torch
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
from face_extractor import extract_faces
from face_aligner import align_face
from capsule_model import load_deepfake_model
import ela_smart_detector as ela
from image_metadata_extractor_1 import ImageMetadataExtractor
from gradcam import run_gradcam


app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for the Vue app

# Setup device and load CapsuleNet model for predictions
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Loading Capsule-Forensics deepfake detection model on device: {device}...")
try:
    eff_ext, capnet = load_deepfake_model("final_model_99.pt", device)
    print("Prediction model loaded successfully!")
except Exception as e:
    print(f"Error loading prediction model final_model_99.pt: {e}")
    eff_ext, capnet = None, None

# Load a completely separate copy of the model for Grad-CAM to isolate states
try:
    eff_ext_gc, capnet_gc = load_deepfake_model("final_model_99.pt", device)
    print("Grad-CAM model loaded successfully!")
except Exception as e:
    print(f"Error loading Grad-CAM model final_model_99.pt: {e}")
    eff_ext_gc, capnet_gc = None, None

def predict_deepfake(img):
    if eff_ext is None or capnet is None:
        return 0.0, 1.0
    try:
        if img is None:
            return 0.0, 1.0
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # Normalize and convert to tensor
        img_tensor = torch.tensor(img_rgb, dtype=torch.float32).permute(2, 0, 1) / 255.0
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        img_tensor = (img_tensor - mean) / std
        img_tensor = img_tensor.unsqueeze(0).to(device)
        
        with torch.no_grad():
            features = eff_ext(img_tensor)
            _, classes_pred = capnet(features)
            # classes_pred: [1, 2] -> index 0: fake, index 1: real
            prob_fake = classes_pred[0][0].item()
            prob_real = classes_pred[0][1].item()
            return prob_fake, prob_real
    except Exception as e:
        print(f"Prediction error: {e}")
        return 0.0, 1.0

import numpy as np

def get_base64_from_cv2(img_array):
    """Encodes a cv2 numpy array into a base64 Data URL."""
    if img_array is None:
        return None
    try:
        _, buffer = cv2.imencode('.jpg', img_array)
        encoded = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded}"
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None

@app.route("/api/analyze", methods=["POST"])
def analyze_image():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400

    file_bytes = file.read()

    # 1. Get original image metadata
    try:
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({"success": False, "error": "Could not read image file"}), 400
        height, width, channels = img.shape
        file_size_kb = round(len(file_bytes) / 1024, 2)
        file_ext = os.path.splitext(file.filename)[1].upper().replace(".", "")
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed reading image metadata: {str(e)}"}), 500

    # 2. Execute Face Extraction (Step 1)
    try:
        extracted_faces = extract_faces(img)
    except Exception as e:
        return jsonify({"success": False, "error": f"Face extraction failed: {str(e)}"}), 500

    faces_data = []

    # 3. Execute Face Alignment and Deepfake Detection (Step 2)
    for i, face_img in enumerate(extracted_faces):
        try:
            # Pass 1 Alignment
            pass1_img = align_face(face_img)
            
            if pass1_img is None:
                print(f"Skipping face {i}: Alignment failed (no face detected).")
                continue

            # Pass 2 Alignment for fine-tuning
            final_img = align_face(pass1_img)
            
            if final_img is None:
                print(f"Skipping face {i}: Fine-tuning alignment failed (no face detected).")
                continue

            # Get the aligned face image
            aligned_face_img = final_img
            
            # Predict using CapsuleNet model
            prob_fake, prob_real = predict_deepfake(aligned_face_img)

            # Generate Grad-CAM heatmap overlay for this face using the isolated Grad-CAM model copy
            gradcam_b64 = None
            if eff_ext_gc is not None and capnet_gc is not None:
                try:
                    superimposed, pred_class = run_gradcam(eff_ext_gc, capnet_gc, aligned_face_img, device)
                    if superimposed is not None:
                        # Convert RGB to BGR for cv2 encoding
                        superimposed_bgr = cv2.cvtColor(superimposed, cv2.COLOR_RGB2BGR)
                        _, buffer = cv2.imencode('.jpg', superimposed_bgr)
                        gradcam_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')
                except Exception as gc_e:
                    print(f"Error generating Grad-CAM for face {i}: {gc_e}")

            # Gather base64 images to send to front-end
            face_b64 = get_base64_from_cv2(face_img)
            aligned_b64 = get_base64_from_cv2(aligned_face_img)

            faces_data.append({
                "index": i,
                "original_crop": face_b64,
                "aligned": aligned_b64,
                "gradcam_image": gradcam_b64,
                "fake_probability": round(prob_fake * 100, 2),
                "real_probability": round(prob_real * 100, 2)
            })
        except Exception as e:
            print(f"Error aligning/predicting face {i}: {e}")
            # Do not append fallback if prediction or processing fails completely
            continue

    # 4. Generate Verdict (Step 3)
    # We will simulate a realistic classification score based on simple image characteristics
    # and deterministic checks (e.g. check filename or size hash to keep it deterministic for tests)
    # A true deepfake verification model would run inference here.
    has_faces = len(faces_data) > 0
    
    if not has_faces:
        is_fake = False
        verdict_score = 0.0
        desc_ar = "لم يتم الكشف عن أي وجه في الصورة للفحص الجنائي الرقمي."
        desc_en = "No faces detected in the image for digital forensic analysis."
    else:
        # Determine verdict based on the maximum fake probability among all detected faces
        verdict_score = max(face["fake_probability"] for face in faces_data)
        is_fake = verdict_score > 50.0  # Threshold of 50%
        
        if is_fake:
            desc_ar = f"⚠ تحذير: تم كشف معالم غير طبيعية. مؤشرات قوية على فبركة الوجه أو تعديله بنسبة {verdict_score}%."
            desc_en = f"⚠ Warning: Anomalous facial pattern detected. Strong indicators of deepfake manipulation at {verdict_score}%."
        else:
            desc_ar = f"✓ تم التحقق: الوجوه طبيعية بنسبة {round(100.0 - verdict_score, 2)}%. لا توجد أدلة كافية على فبركة رقمية عميقة."
            desc_en = f"✓ Verified: Faces appear natural at {round(100.0 - verdict_score, 2)}%. Insufficient evidence of digital manipulation."

    metadata = {
        "filename": file.filename,
        "width": width,
        "height": height,
        "size_kb": file_size_kb,
        "format": file_ext,
        "faces_detected": len(faces_data)
    }

    file_ext_upper = file_ext.upper()
    warning_ar = None
    warning_en = None
    if file_ext_upper not in ["JPG", "JPEG", "PNG"]:
        warning_ar = f"⚠️ تنبيه: هذه الصورة امتدادها ({file_ext_upper})، النموذج ليس ذكياً في الإجابة بدقة في نتيجتها، ولكن سيعطيك نتيجة أيضاً."
        warning_en = f"⚠️ Warning: This image has a ({file_ext_upper}) extension. The model is not highly accurate at predicting results for this format, but it will still provide a result anyway."

    verdict = {
        "is_deepfake": is_fake,
        "score": verdict_score,
        "description_ar": desc_ar,
        "description_en": desc_en,
        "warning_ar": warning_ar,
        "warning_en": warning_en
    }

    # Run Error Level Analysis (ELA)
    ela_data = {"success": False, "error": "Not executed"}
    try:
        ela_quality = int(request.form.get("ela_quality", 90))
        pil_img = Image.open(io.BytesIO(file_bytes))
        
        raw_diff, ela_display, max_diff = ela.extract_ela(pil_img, quality=ela_quality)
        stats = ela.compute_statistics(pil_img, raw_diff, max_diff)
        verdict_key, score, triggered, low_evidence = ela.rule_engine(stats)
        report = ela.build_report(stats, verdict_key, score, triggered, low_evidence, ela_quality)
        
        # Encode ELA image to base64
        buffered = io.BytesIO()
        ela_display.save(buffered, format="JPEG")
        ela_b64 = "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        ela_data = {
            "success": True,
            "ela_image": ela_b64,
            "verdict": verdict_key,
            "score": float(score),
            "low_evidence": low_evidence,
            "stats": stats,
            "report": report
        }
    except Exception as e:
        print(f"Error in ELA execution: {e}")
        ela_data = {
            "success": False,
            "error": str(e)
        }

    # Run Detailed Metadata Extraction
    detailed_metadata = {"success": False, "error": "Not executed"}
    try:
        extractor = ImageMetadataExtractor(file_bytes=file_bytes, filename=file.filename)
        metadata_payload = extractor.extract_all()
        if "exif" in metadata_payload and "raw_tags" in metadata_payload["exif"]:
            del metadata_payload["exif"]["raw_tags"]
        detailed_metadata = {
            "success": True,
            "data": metadata_payload
        }
    except Exception as e:
        print(f"Error in Metadata extraction: {e}")
        detailed_metadata = {
            "success": False,
            "error": str(e)
        }

    return jsonify({
        "success": True,
        "metadata": metadata,
        "faces": faces_data,
        "verdict": verdict,
        "ela": ela_data,
        "detailed_metadata": detailed_metadata
    })

if __name__ == "__main__":
    print("Starting MATAY AI backend server on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
