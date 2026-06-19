# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║         تحليل مستوى الخطأ الذكي — Smart ELA Detector              ║
║   أداة جنائية رقمية | Rule-Based Statistical Analysis              ║
║   الاعتماد: PIL · NumPy · Gradio — بدون أي نموذج ذكاء اصطناعي    ║
╚══════════════════════════════════════════════════════════════════════╝

الفكرة الجوهرية لـ ELA:
  عند ضغط صورة JPEG مرة ثانية بنفس الجودة، يجب أن يكون الفارق بين
  النسختين متجانساً عبر كامل الصورة. إذا وُجدت مناطق ذات فارق مختلف
  جذرياً عن المحيط → دليل على أن تلك المناطق أُضيفت/عُدِّلت بتاريخ
  ضغط مختلف (أي مصدر مختلف).
"""

import io
import numpy as np
from PIL import Image, ImageChops, ImageEnhance


# ══════════════════════════════════════════════════════════════════
# الوحدة 1 ─ استخراج خريطة ELA
# ══════════════════════════════════════════════════════════════════

def extract_ela(image: Image.Image, quality: int = 90):
    img_rgb = image.convert("RGB")

    # ضغط JPEG في الذاكرة
    buf = io.BytesIO()
    img_rgb.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    compressed = Image.open(buf).convert("RGB")

    # الفارق المطلق الخام
    raw_diff = ImageChops.difference(img_rgb, compressed)

    # أقصى فارق
    max_diff = max(ch[1] for ch in raw_diff.getextrema())

    # نسخة مُضخَّمة للعرض البصري
    scale       = (255.0 / max_diff) if max_diff > 0 else 1.0
    ela_display = ImageEnhance.Brightness(raw_diff).enhance(scale)

    return raw_diff, ela_display, max_diff


# ══════════════════════════════════════════════════════════════════
# الوحدة 2 ─ حساب المقاييس الإحصائية
# ══════════════════════════════════════════════════════════════════

BLOCK_SIZE = 16   # حجم الكتلة بالبكسل لتحليل التباين المحلي


def compute_statistics(original_img: Image.Image, raw_diff: Image.Image, max_diff: int) -> dict:
    orig_gray = np.array(original_img.convert("L"), dtype=np.float32)
    diff_gray = np.array(raw_diff.convert("L"), dtype=np.float32)

    h, w = orig_gray.shape
    B    = BLOCK_SIZE

    ratios = []
    block_means = []

    for y in range(0, h - B + 1, B):
        for x in range(0, w - B + 1, B):
            orig_block = orig_gray[y:y + B, x:x + B]
            diff_block = diff_gray[y:y + B, x:x + B]

            diff_mean = np.mean(diff_block)
            block_means.append(diff_mean)

            orig_std = np.std(orig_block)

            # فلترة الكتل الملساء جداً (أقل من 2.0 انحراف معيارى) لأنها تحتوى على ضوضاء ELA مسطحة
            if orig_std > 2.0:
                ratio = diff_mean / (orig_std + 1.0)
                ratios.append(ratio)

    if len(ratios) == 0:
        normalized_cv = 0.0
        outlier_ratio = 0.0
    else:
        ratios = np.array(ratios)
        ratio_mean = float(np.mean(ratios))
        ratio_std  = float(np.std(ratios))
        normalized_cv = round(ratio_std / ratio_mean, 4) if ratio_mean > 0.001 else 0.0

        threshold_outlier = ratio_mean + 2 * ratio_std
        outlier_ratio = round(
            float(np.sum(ratios > threshold_outlier)) / len(ratios),
            4
        )

    # معامل التباين التقليدي الكلاسيكي (كقيمة استرشادية)
    bm_mean  = float(np.mean(block_means))
    bm_std   = float(np.std(block_means))
    standard_cv = round(bm_std / bm_mean, 4) if bm_mean > 0.1 else 0.0

    return {
        "block_cv"      : normalized_cv,  # نستخدم المعامل الذكي كمعامل رئيسي
        "standard_cv"   : standard_cv,
        "outlier_ratio" : outlier_ratio,
        "max_diff"      : int(max_diff),
    }


# ══════════════════════════════════════════════════════════════════
# الوحدة 3 ─ محرك القواعد الإحصائي
# ══════════════════════════════════════════════════════════════════

# العتبات المحدثة المخصصة للتحليل المعدل بالنسيج
RULE_THRESHOLDS = {
    "block_cv"      : 0.38,   # عتبة الاشتباه المعدلة بالنسيج
    "outlier_ratio" : 0.05,   # نسبة الكتل الشاذة
}

VERDICT_LEVELS = [
    (0.40, "tampered"),
    (0.15, "suspicious"),
    (0.00, "clean"),
]


def rule_engine(stats: dict) -> tuple:
    norm_cv = stats["block_cv"]
    outlier = stats["outlier_ratio"]
    max_diff = stats["max_diff"]

    triggered = []

    # تحديد الحكم ونسبة الاشتباه بناءً على التشتت المعدل بالنسيج
    if norm_cv > 0.58:
        verdict_key = "tampered"
        score = 0.60 + min((norm_cv - 0.58) / 0.5, 0.40)
        triggered.append("block_cv")
        if outlier > 0.05:
            triggered.append("outlier_ratio")
    elif norm_cv > 0.38:
        verdict_key = "suspicious"
        score = 0.15 + ((norm_cv - 0.38) / 0.20) * 0.24
        triggered.append("block_cv")
        if outlier > 0.05:
            triggered.append("outlier_ratio")
    else:
        verdict_key = "clean"
        score = (norm_cv / 0.38) * 0.14
        if outlier > 0.05:
            triggered.append("outlier_ratio")
            score += 0.05

    low_evidence = max_diff < 15

    return verdict_key, round(score, 4), triggered, low_evidence


# ══════════════════════════════════════════════════════════════════
# الوحدة 4 ─ صياغة التقرير النصي
# ══════════════════════════════════════════════════════════════════

VERDICT_TEXTS = {
    "tampered"  : "⚠️  الصورة تحتوي على آثار تعديل بكسلات إحصائية\n     Image Tampered (High Pixel Discrepancy)",
    "suspicious": "🔶  الصورة مشبوهة — تفاوت طفيف بالضغط البكسلي\n     Image Suspicious — Inconclusive Compression History",
    "clean"     : "✅  الصورة سليمة ولا تحتوي على تعديل بكسلي غير طبيعي\n     Image Not Tampered (Consistent Pixel History)",
}

METRIC_LABELS = {
    "block_cv"      : "معامل تباين الكتل الذكي المعدل بالنسيج  (Texture-Normalized CV)",
    "standard_cv"   : "معامل تباين الكتل التقليدي الكلاسيكي    (Classic Standard CV)",
    "outlier_ratio" : "نسبة الكتل الشاذة بالتحليل المعدل      (Outlier Ratio)",
    "max_diff"      : "أقصى فارق خام                          (Max Raw Diff)",
}

THRESHOLD_DISPLAY = {
    "block_cv"      : RULE_THRESHOLDS["block_cv"],
    "standard_cv"   : "—",
    "outlier_ratio" : RULE_THRESHOLDS["outlier_ratio"],
    "max_diff"      : "—",
}


def build_report(stats: dict, verdict_key: str, score: float,
                 triggered: list, low_evidence: bool, quality: int) -> str:
    lines = [
        "══════════════════════════════════════════════",
        "   الحكم النهائي  /  Final Verdict",
        "══════════════════════════════════════════════",
        "",
        f"  {VERDICT_TEXTS[verdict_key]}",
        "",
        "══════════════════════════════════════════════",
        "  ⚠️  هذا التحليل استكشافي وليس دليلاً قاطعاً.",
        "      تتأثر النتائج بتاريخ الضغط السابق للصورة وسياق النسيج.",
        "      This analysis is exploratory, not conclusive.",
        "══════════════════════════════════════════════",
    ]

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════
# الوحدة 5 ─ دالة الواجهة الرئيسية
# ══════════════════════════════════════════════════════════════════

def analyze(uploaded, quality: int):
    if uploaded is None:
        return None, None, "⚠️ يرجى رفع صورة أولاً."

    original                       = Image.fromarray(uploaded)
    raw_diff, ela_display, max_diff = extract_ela(original, quality=int(quality))
    stats                          = compute_statistics(original, raw_diff, max_diff)
    verdict_key, score, triggered, low_evidence = rule_engine(stats)
    report                         = build_report(
        stats, verdict_key, score, triggered, low_evidence, int(quality)
    )

    return original, ela_display, report


# ══════════════════════════════════════════════════════════════════
# الوحدة 6 ─ واجهة Gradio
# ══════════════════════════════════════════════════════════════════

CSS = """
body, .gradio-container {
    background: #0d1117 !important;
    font-family: 'Segoe UI', Tahoma, sans-serif !important;
}
.gr-button-primary {
    background: linear-gradient(135deg, #1f6feb, #388bfd) !important;
    border: none !important; font-weight: 700 !important; font-size: 1rem !important;
}
.gr-textbox textarea {
    font-family: 'Courier New', monospace !important; font-size: 0.82rem !important;
    background: #161b22 !important; color: #c9d1d9 !important;
    border: 1px solid #30363d !important;
}
"""

HEADER_HTML = """
<div dir="rtl" style="
    background:linear-gradient(135deg,#0d1117 0%,#161b22 100%);
    border:1px solid #30363d; border-radius:12px;
    padding:20px 28px; color:#c9d1d9; font-family:'Segoe UI',sans-serif;
">
  <h2 style="color:#58a6ff; margin:0 0 6px;">
    🔬 Smart ELA Detector — محلل الجنائيات الرقمية الذكي
  </h2>
  <p style="color:#8b949e; margin:4px 0; font-size:0.9rem;">
    يعمل بالكامل على معالجة الصور الرياضية البحتة · بدون أي نموذج ذكاء اصطناعي
  </p>
  <hr style="border-color:#30363d; margin:10px 0;">
  <p style="font-size:0.87rem; color:#8b949e; margin:0;">
    ارفع صورة · اضبط جودة الضغط · اضغط <strong style="color:#58a6ff;">تحليل</strong>
    · احصل على خريطة ELA + حكم إحصائي تلقائي
  </p>
</div>
"""

if __name__ == "__main__":
    import gradio as gr

    with gr.Blocks(title="Smart ELA Detector") as demo:

        gr.HTML(HEADER_HTML)

        # ── الإدخال ──
        with gr.Row():
            with gr.Column(scale=1):
                input_img = gr.Image(
                    label="📤 ارفع الصورة المراد فحصها",
                    type="numpy", height=280,
                )
                quality_slider = gr.Slider(
                    minimum=50, maximum=99, value=90, step=1,
                    label="جودة إعادة الضغط  (Recompression Quality)",
                    info="90 للصور الطبيعية · جرّب 75 للصور المضغوطة مسبقاً"
                )
                run_btn = gr.Button("🔎  تشغيل التحليل الجنائي", variant="primary", size="lg")

        gr.Markdown("---")

        # ── الإخراج المرئي ──
        with gr.Row():
            orig_out = gr.Image(label="الصورة الأصلية", type="pil", height=320)
            ela_out  = gr.Image(label="🗺️ خريطة ELA", type="pil", height=320)

        # ── التقرير النصي ──
        report_out = gr.Textbox(
            label="📋 التقرير الجنائي الكامل  /  Full Forensic Report",
            lines=24, max_lines=32, interactive=False,
        )

        # ── ربط الزر ──
        run_btn.click(
            fn=analyze,
            inputs=[input_img, quality_slider],
            outputs=[orig_out, ela_out, report_out],
        )

        # ── دليل التفسير ──
        gr.Markdown(
            """
            ---
            ### 📖 دليل تفسير الحكم

            | الحكم | نسبة الاشتباه | المعنى |
            |---|---|---|
            | ✅ سليمة | < 15% | الكتل متجانسة — تاريخ ضغط موحّد |
            | 🔶 مشبوهة | 15% – 39% | بعض التباين — يُنصح بمراجعة بشرية |
            | ⚠️ مُعدَّلة | ≥ 40% | تباين واضح بين الكتل — تاريخ ضغط مختلف |

            **المقاييس المستخدمة في الحكم:**
            - **Block CV (معامل تباين الكتل):** القيمة الرئيسية — وزن 70%
            - **Outlier Ratio (نسبة الكتل الشاذة):** مقياس مكمّل — وزن 30%

            > ⚠️ **تنبيه:** ELA أداة استكشافية. تتأثر نتائجها بعدد مرات حفظ الصورة وجودتها الأصلية.
            > الصور المضغوطة بشدة مسبقاً (WhatsApp/Telegram) تُعطي موثوقية أقل.
            """
        )

    demo.launch(share=False, css=CSS)
