import os
from face_extractor import extract_faces
from face_aligner import align_face

INPUT_IMAGE = "input/2.jpg"
OUTPUT_FOLDER = "output"

if __name__ == "__main__":
    # إنشاء مجلد المخرجات إذا لم يكن موجوداً
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # الخطوة 1: استخراج الوجوه باستخدام دالة القص من ملف face_extractor
    faces = extract_faces(INPUT_IMAGE, OUTPUT_FOLDER)

    # الخطوة 2: المرور على الوجوه المستخرجة وتدويرها باستخدام ملف face_aligner
    for i, f in enumerate(faces):
        # التدوير الأول (Pass 1)
        out_pass1 = align_face(f, f"{OUTPUT_FOLDER}/aligned_{i}_pass1.jpg")
        
        # التدوير الثاني (Pass 2) للتأكيد والضبط الدقيق
        if out_pass1:
            out_final = align_face(out_pass1, f"{OUTPUT_FOLDER}/aligned_{i}.jpg")
            print("Saved final:", out_final)
