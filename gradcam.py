# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║               تطبيق تقنية Grad-CAM — Grad-CAM Generator              ║
║         أداة فحص وتفسير قرارات نموذج الذكاء الاصطناعي                 ║
║   الاعتماد: PyTorch · OpenCV · NumPy · Matplotlib                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import cv2
import base64
import numpy as np
import torch
import torch.nn.functional as F
import matplotlib.pyplot as plt
from PIL import Image

class GradCAM:
    """
    Gradient-weighted Class Activation Mapping (Grad-CAM)
    لتفسير وفهم الأماكن التي ركز عليها النموذج لتحديد الفبركة.
    """
    def __init__(self, eff_ext, capnet, target_layer):
        self.eff_ext = eff_ext
        self.capnet = capnet
        self.target_layer = target_layer
        self.activations = None
        self.gradients = None
        
        # تسجيل الـ Hooks لالتقاط الـ Forward Activations والـ Backward Gradients
        self.forward_hook = target_layer.register_forward_hook(self.save_activation)
        
        if hasattr(target_layer, "register_full_backward_hook"):
            self.backward_hook = target_layer.register_full_backward_hook(self.save_gradient)
        else:
            self.backward_hook = target_layer.register_backward_hook(self.save_gradient)

    def save_activation(self, module, input, output):
        self.activations = output

    def save_gradient(self, module, grad_input, grad_output):
        # grad_output عبارة عن tuple، نأخذ العنصر الأول [0]
        self.gradients = grad_output[0]

    def remove_hooks(self):
        """إزالة الـ Hooks لتفادي تراكمها في الذاكرة."""
        self.forward_hook.remove()
        self.backward_hook.remove()

    def generate_heatmap(self, img_tensor, class_idx=None):
        """توليد خريطة الحرارة المقيسة [0, 1]"""
        # التأكد من تمكين تتبع التدرجات لمدخلات الصورة
        img_tensor = img_tensor.clone().detach().requires_grad_(True)
        
        # 1. Forward Pass
        features = self.eff_ext(img_tensor)
        z, _ = self.capnet(features)
        
        # إعادة حساب الاحتمالات بدون عمل detach للسماح بسريان التدرجات
        classes_non_detached = F.softmax(z, dim=-1).mean(dim=1)
        
        # إذا لم يتم تحديد الفئة، نستخدم الفئة ذات أعلى احتمال (المتوقعة)
        if class_idx is None:
            class_idx = torch.argmax(classes_non_detached, dim=1).item()
            
        # 2. الحصول على النتيجة للفئة المستهدفة
        score = classes_non_detached[0][class_idx]
        
        # 3. Backward Pass لحساب التدرجات
        self.eff_ext.zero_grad()
        self.capnet.zero_grad()
        score.backward()
        
        # التأكد من التقاط التنشيطات والتدرجات
        if self.activations is None or self.gradients is None:
            print("⚠️ فشل التقاط التنشيطات أو التدرجات.")
            return None
            
        activations = self.activations.detach().cpu().numpy()[0] # [C, H, W]
        gradients = self.gradients.detach().cpu().numpy()[0]     # [C, H, W]
        
        # 4. حساب أوزان الطبقة عبر متوسط التدرجات (Global Average Pooling)
        weights = np.mean(gradients, axis=(1, 2)) # [C]
        
        # 5. دمج خرائط التنشيط بالأوزان المناسبة
        heatmap = np.zeros(activations.shape[1:], dtype=np.float32) # [H, W]
        for i, w in enumerate(weights):
            heatmap += w * activations[i]
            
        # 6. تطبيق دالة ReLU للاحتفاظ بالتأثيرات الإيجابية فقط
        heatmap = np.maximum(heatmap, 0)
        
        # 7. تسوية خريطة الحرارة لتكون بين 0 و 1
        max_val = np.max(heatmap)
        if max_val > 0:
            heatmap = heatmap / max_val
            
        return heatmap, class_idx

def run_gradcam(eff_ext, capnet, img, device="cpu", class_idx=None):
    """
    تشغيل عملية Grad-CAM كاملة على صورة معينة وإرجاع الصورة المدمجة.
    
    المعاملات:
        - eff_ext: نموذج استخراج الميزات
        - capnet: نموذج الكبسولات
        - img: مصفوفة numpy للوجه
        - device: الجهاز المستخدم (cpu أو cuda)
        - class_idx: الفئة المستهدفة (0: مزيف، 1: حقيقي، None: الفئة ذات الاحتمال الأعلى)
    """
    try:
        # 1. قراءة وتجهيز الصورة
        if img is None:
            raise ValueError("صورة الوجه غير صالحة")
            
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 2. تسوية الصورة وتحويلها إلى Tensor بنفس معايير الخادم
        img_tensor = torch.tensor(img_rgb, dtype=torch.float32).permute(2, 0, 1) / 255.0
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        img_tensor = (img_tensor - mean) / std
        img_tensor = img_tensor.unsqueeze(0).to(device)
        
        # 3. تحديد آخر طبقة تلافيفية Conv2d في مستخرج الميزات
        target_layer = eff_ext.features[-1][-1].block[3][0]
        
        # 4. تشغيل Grad-CAM
        cam = GradCAM(eff_ext, capnet, target_layer)
        res = cam.generate_heatmap(img_tensor, class_idx)
        cam.remove_hooks()
        
        if res is None:
            return None, None
            
        heatmap, pred_class = res
        
        # 5. دمج خريطة الحرارة مع الصورة الأصلية
        h, w, _ = img.shape
        heatmap_resized = cv2.resize(heatmap, (w, h))
        heatmap_255 = np.uint8(255 * heatmap_resized)
        
        # تطبيق التلوين الحراري (Jet Colormap)
        heatmap_color = cv2.applyColorMap(heatmap_255, cv2.COLORMAP_JET)
        
        # دمج الصورة الأصلية مع خريطة الحرارة بنسبة (60% للأصل و 40% للخريطة)
        superimposed = cv2.addWeighted(img_rgb, 0.6, heatmap_color, 0.4, 0)
        
        return superimposed, pred_class
        
    except Exception as e:
        print(f"Error executing Grad-CAM: {e}")
        return None, None

def show_matplotlib_comparison(original_path, superimposed_img, pred_class):
    """عرض الصورة الأصلية بجانب صورة Grad-CAM باستخدام Matplotlib."""
    orig = cv2.imread(original_path)
    orig_rgb = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)
    
    class_label = "Fake (مزيف)" if pred_class == 0 else "Real (حقيقي)"
    
    plt.figure(figsize=(10, 5))
    
    # الصورة الأصلية
    plt.subplot(1, 2, 1)
    plt.title("Original Face Crop (الوجه الأصلي)")
    plt.imshow(orig_rgb)
    plt.axis("off")
    
    # صورة Grad-CAM
    plt.subplot(1, 2, 2)
    plt.title(f"Grad-CAM Heatmap (تركيز النموذج: {class_label})")
    plt.imshow(superimposed_img)
    plt.axis("off")
    
    plt.tight_layout()
    output_filename = "gradcam_comparison.png"
    plt.savefig(output_filename, dpi=150)
    print(f"🖼️ تم حفظ صورة مقارنة Matplotlib في: {os.path.abspath(output_filename)}")
    plt.show()

# ══════════════════════════════════════════════════════════════════════════
# تشغيل مباشر من سطر الأوامر للاختبار والمعاينة
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    from capsule_model import load_deepfake_model
    
    # التحقق من المدخلات
    if len(sys.argv) > 1:
        test_img_path = sys.argv[1]
    else:
        # البحث عن أي وجه مستخلص في مجلد المخرجات للتجربة
        import glob
        faces = glob.glob("output/face_*")
        if faces:
            test_img_path = faces[0]
            print(f"🔎 لم يُحدَّد مسار صورة، جاري استخدام وجه مستخلص تلقائياً: {test_img_path}")
        else:
            print("❌ يرجى توفير مسار للوجه المستخلص لتشغيل الاختبار.")
            print("الاستخدام: python gradcam.py <مسار_صورة_الوجه>")
            sys.exit(1)
            
    print("⏳ جاري تحميل النموذج لتوليد Grad-CAM...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        eff, cap = load_deepfake_model("final_model_99.pt", device)
        print("✓ تم تحميل النموذج بنجاح.")
        
        print(f"⏳ جاري تشغيل Grad-CAM على الصورة: {test_img_path}...")
        superimposed, pred_class = run_gradcam(eff, cap, test_img_path, device)
        
        if superimposed is not None:
            show_matplotlib_comparison(test_img_path, superimposed, pred_class)
        else:
            print("❌ فشل تشغيل Grad-CAM.")
    except Exception as e:
        print(f"❌ خطأ أثناء تشغيل الاختبار: {e}")
