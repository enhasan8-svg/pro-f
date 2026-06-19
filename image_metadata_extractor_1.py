"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              ImageMetadataExtractor — Production-Ready Tool                 ║
║  استخراج شامل لجميع البيانات الوصفية (Metadata) من الصور                   ║
║                                                                              ║
║  المكتبات المستخدمة:                                                        ║
║    - Pillow       : قراءة بيانات EXIF وخصائص الصورة الأساسية               ║
║    - exifread     : استخراج تفاصيل EXIF العميقة والدقيقة                   ║
║    - pathlib      : التعامل مع مسارات الملفات بشكل احترافي                 ║
║    - json         : تصدير النتائج بتنسيق JSON منظم                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

التثبيت:
    pip install Pillow exifread

الاستخدام:
    extractor = ImageMetadataExtractor("path/to/image.jpg")
    metadata  = extractor.extract_all()
    extractor.pretty_print(metadata)
"""

import json
import os
import struct
from datetime import datetime
from pathlib import Path
from typing import Any

# ── مكتبات خارجية ─────────────────────────────────────────────────────────────
try:
    from PIL import Image
    from PIL.ExifTags import GPSTAGS, TAGS
except ImportError as e:
    raise ImportError(
        "مكتبة Pillow غير مثبّتة. قم بتشغيل: pip install Pillow"
    ) from e

try:
    import exifread
except ImportError as e:
    raise ImportError(
        "مكتبة exifread غير مثبّتة. قم بتشغيل: pip install exifread"
    ) from e


# ══════════════════════════════════════════════════════════════════════════════
# الـ Class الرئيسي
# ══════════════════════════════════════════════════════════════════════════════

class ImageMetadataExtractor:
    """
    استخراج شامل لجميع البيانات الوصفية من الصور.

    يدعم:
        - البيانات الأساسية  (الاسم، الحجم، الأبعاد، نظام الألوان ...)
        - بيانات EXIF        (الكاميرا، التعريض، ISO، التاريخ ...)
        - بيانات GPS         (خط الطول والعرض بدرجات عشرية)
        - بيانات IPTC/XMP    (الكاتب، الوصف، حقوق النشر — متى توفّرت)

    المعاملات:
        image_path (str | Path): المسار الكامل أو النسبي للصورة.

    مثال:
        extractor = ImageMetadataExtractor("photo.jpg")
        data = extractor.extract_all()
        extractor.pretty_print(data)
    """

    # ── ثوابت الصنف ───────────────────────────────────────────────────────────
    SUPPORTED_FORMATS: tuple[str, ...] = (
        ".jpg", ".jpeg", ".png", ".tiff", ".tif",
        ".bmp", ".gif", ".webp", ".heic", ".heif",
    )

    # خريطة اتجاه الصورة (Orientation) → وصف نصي
    ORIENTATION_MAP: dict[int, str] = {
        1: "Normal (0°)",
        2: "Mirrored Horizontal",
        3: "Rotated 180°",
        4: "Mirrored Vertical",
        5: "Mirrored Horizontal + Rotated 270°",
        6: "Rotated 90° CW",
        7: "Mirrored Horizontal + Rotated 90°",
        8: "Rotated 270° CW",
    }

    # ── الباني ────────────────────────────────────────────────────────────────
    def __init__(self, image_path: str | Path | None = None, file_bytes: bytes | None = None, filename: str = "") -> None:
        self.file_bytes = file_bytes
        self.filename = filename
        if image_path is not None:
            self.image_path = Path(image_path).resolve()
            self._validate_path()
        elif file_bytes is not None:
            self.image_path = None
        else:
            raise ValueError("يجب توفير مسار الصورة أو بياناتها كـ bytes")
            
        self._pil_image: Image.Image | None = None

    # ── التحقق من الملف ───────────────────────────────────────────────────────
    def _validate_path(self) -> None:
        """يتحقق من وجود الملف ودعم امتداده."""
        if self.image_path is None:
            return
        if not self.image_path.exists():
            raise FileNotFoundError(f"الملف غير موجود: {self.image_path}")
        if not self.image_path.is_file():
            raise ValueError(f"المسار لا يشير إلى ملف: {self.image_path}")
        if self.image_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"الامتداد '{self.image_path.suffix}' غير مدعوم. "
                f"الامتدادات المدعومة: {self.SUPPORTED_FORMATS}"
            )

    # ══════════════════════════════════════════════════════════════════════════
    # 1. البيانات الأساسية للملف
    # ══════════════════════════════════════════════════════════════════════════
    def _extract_basic_info(self) -> dict[str, Any]:
        """
        يستخرج البيانات الأساسية للملف:
            اسم الملف، حجمه على القرص، الامتداد، الأبعاد، نظام الألوان ...
        """
        if self.image_path:
            stat = self.image_path.stat()
            file_name = self.image_path.name
            file_path = str(self.image_path)
            file_extension = self.image_path.suffix.lower()
            file_size_bytes = stat.st_size
            created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
            modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
        else:
            file_name = self.filename
            file_path = "In-Memory"
            file_extension = os.path.splitext(self.filename)[1].lower() if self.filename else ""
            file_size_bytes = len(self.file_bytes)
            created_at = datetime.now().isoformat()
            modified_at = datetime.now().isoformat()

        info: dict[str, Any] = {
            "file_name"       : file_name,
            "file_path"       : file_path,
            "file_extension"  : file_extension,
            "file_size_bytes" : file_size_bytes,
            "file_size_kb"    : round(file_size_bytes / 1024, 2),
            "file_size_mb"    : round(file_size_bytes / (1024 ** 2), 4),
            "created_at"      : created_at,
            "modified_at"     : modified_at,
        }

        # فتح الصورة عبر Pillow لاستخراج خصائصها
        try:
            img = self._open_pil_image()
            info.update({
                "format"          : img.format or self.image_path.suffix.upper().lstrip("."),
                "mode"            : img.mode,                     # RGB, CMYK, L, RGBA ...
                "color_space"     : self._describe_mode(img.mode),
                "width_px"        : img.width,
                "height_px"       : img.height,
                "megapixels"      : round((img.width * img.height) / 1_000_000, 2),
                "aspect_ratio"    : self._calc_aspect_ratio(img.width, img.height),
                "is_animated"     : getattr(img, "is_animated", False),
                "n_frames"        : getattr(img, "n_frames", 1),
            })
        except Exception as exc:
            info["image_open_error"] = str(exc)

        return info

    @staticmethod
    def _describe_mode(mode: str) -> str:
        """يترجم رمز نظام الألوان إلى وصف نصي مفهوم."""
        descriptions = {
            "1"    : "1-bit Pixels (Black & White)",
            "L"    : "8-bit Grayscale",
            "P"    : "8-bit Palette-mapped",
            "RGB"  : "24-bit True Color (RGB)",
            "RGBA" : "32-bit True Color with Alpha (RGBA)",
            "CMYK" : "32-bit CMYK (Print)",
            "YCbCr": "YCbCr (Video/JPEG)",
            "LAB"  : "L*a*b* Color Space",
            "HSV"  : "Hue-Saturation-Value",
            "I"    : "32-bit Integer Pixels",
            "F"    : "32-bit Float Pixels",
        }
        return descriptions.get(mode, f"Unknown ({mode})")

    @staticmethod
    def _calc_aspect_ratio(width: int, height: int) -> str:
        """يحسب نسبة العرض إلى الارتفاع بصيغة مبسّطة مثل 16:9."""
        from math import gcd
        divisor = gcd(width, height)
        return f"{width // divisor}:{height // divisor}"

    # ══════════════════════════════════════════════════════════════════════════
    # 2. بيانات EXIF (الكاميرا والتعريض)
    # ══════════════════════════════════════════════════════════════════════════
    def _extract_exif_data(self) -> dict[str, Any]:
        """
        يستخرج بيانات EXIF المتعلقة بالكاميرا وإعدادات التصوير
        باستخدام مكتبتَي Pillow و exifread معاً لأقصى تغطية ممكنة.
        """
        exif_data: dict[str, Any] = {}

        # ── المرحلة الأولى: Pillow (بيانات عامة) ─────────────────────────────
        try:
            img = self._open_pil_image()
            raw_exif = img._getexif()  # type: ignore[attr-defined]
            if raw_exif:
                pillow_tags = {
                    TAGS.get(tag_id, tag_id): value
                    for tag_id, value in raw_exif.items()
                }
                exif_data["_pillow_raw"] = {
                    k: str(v) for k, v in pillow_tags.items()
                    if k != "MakerNote"   # MakerNote بيانات خام ضخمة — نتجاهلها
                }
        except Exception:
            pass   # الصورة لا تحتوي EXIF أو لا تدعمها Pillow

        # ── المرحلة الثانية: exifread (تفاصيل أدق) ───────────────────────────
        try:
            import io
            if self.image_path:
                f = open(self.image_path, "rb")
            else:
                f = io.BytesIO(self.file_bytes)
                
            tags = exifread.process_file(f, details=True, strict=False)
            
            if self.image_path:
                f.close()

            if tags:
                exif_data["_exifread_raw"] = {
                    k: str(v) for k, v in tags.items()
                    if "makernote" not in k.lower()   # تجاهل بيانات الشركة المصنّعة
                }
        except Exception:
            pass

        # ── المرحلة الثالثة: استخراج الحقول المهمة بشكل منظم ─────────────────
        structured = self._build_structured_exif(exif_data)
        return structured

    def _build_structured_exif(self, raw: dict) -> dict[str, Any]:
        """
        يبني قاموساً منظماً من البيانات الخام التي جمعتها
        Pillow و exifread، مع تحويل القيم إلى صيغ مقروءة.
        """
        pillow = raw.get("_pillow_raw", {})
        exifrd = raw.get("_exifread_raw", {})

        def get(*keys: str) -> Any:
            """يبحث عن القيمة في كلا المصدرين."""
            for k in keys:
                v = pillow.get(k) or exifrd.get(k) or exifrd.get(f"EXIF {k}") or exifrd.get(f"Image {k}")
                if v and str(v).strip() not in ("", "0", "None"):
                    return str(v).strip()
            return None

        structured: dict[str, Any] = {
            # ─ معلومات الكاميرا ─────────────────────────────────────────────
            "camera": {
                "make"             : get("Make"),
                "model"            : get("Model"),
                "software"         : get("Software"),
                "lens_make"        : get("LensMake"),
                "lens_model"       : get("LensModel", "LensSpecification"),
                "body_serial"      : get("BodySerialNumber", "CameraSerialNumber"),
            },

            # ─ إعدادات التعريض ───────────────────────────────────────────────
            "exposure": {
                "shutter_speed"    : get("ExposureTime", "ShutterSpeedValue"),
                "aperture_fstop"   : self._parse_aperture(get("FNumber", "ApertureValue")),
                "iso"              : get("ISOSpeedRatings", "ISO"),
                "focal_length_mm"  : self._parse_focal(get("FocalLength")),
                "focal_length_35mm": get("FocalLengthIn35mmFilm"),
                "exposure_mode"    : get("ExposureMode"),
                "exposure_program" : self._map_exposure_program(get("ExposureProgram")),
                "metering_mode"    : get("MeteringMode"),
                "flash"            : get("Flash"),
                "white_balance"    : get("WhiteBalance"),
                "brightness"       : get("BrightnessValue"),
                "exposure_bias"    : get("ExposureBiasValue"),
                "max_aperture"     : get("MaxApertureValue"),
                "digital_zoom"     : get("DigitalZoomRatio"),
                "scene_type"       : get("SceneCaptureType"),
            },

            # ─ التاريخ والوقت ─────────────────────────────────────────────────
            "datetime": {
                "original"         : self._parse_dt(get("DateTimeOriginal")),
                "digitized"        : self._parse_dt(get("DateTimeDigitized")),
                "modified"         : self._parse_dt(get("DateTime")),
                "subsec_original"  : get("SubSecTimeOriginal"),
                "offset_time"      : get("OffsetTime", "OffsetTimeOriginal"),
            },

            # ─ الدقة والطباعة ─────────────────────────────────────────────────
            "resolution": {
                "x_resolution"     : get("XResolution"),
                "y_resolution"     : get("YResolution"),
                "resolution_unit"  : self._map_res_unit(get("ResolutionUnit")),
            },

            # ─ الاتجاه والصورة ───────────────────────────────────────────────
            "image": {
                "orientation"      : self._map_orientation(get("Orientation")),
                "color_space"      : get("ColorSpace"),
                "sensing_method"   : get("SensingMethod"),
                "pixel_x_dimension": get("PixelXDimension", "ExifImageWidth"),
                "pixel_y_dimension": get("PixelYDimension", "ExifImageLength"),
                "light_source"     : get("LightSource"),
                "subject_distance" : get("SubjectDistance"),
                "artist"           : get("Artist"),
                "copyright"        : get("Copyright"),
                "image_description": get("ImageDescription"),
                "user_comment"     : get("UserComment"),
            },

            # ─ بيانات خام كاملة للمرجع ──────────────────────────────────────
            "raw_tags": {
                "pillow" : pillow,
                "exifread": exifrd,
            },
        }

        # إزالة الحقول الفارغة لتنظيف المخرجات
        structured = self._remove_none_values(structured)
        return structured

    # ══════════════════════════════════════════════════════════════════════════
    # 3. بيانات GPS
    # ══════════════════════════════════════════════════════════════════════════
    def _extract_gps_data(self) -> dict[str, Any]:
        """
        يستخرج إحداثيات GPS من بيانات EXIF ويحوّلها إلى:
            - درجات عشرية (Decimal Degrees) مناسبة لـ Google Maps
            - رابط مباشر لـ Google Maps
        """
        gps_info: dict[str, Any] = {"available": False}

        try:
            img = self._open_pil_image()
            raw_exif = img._getexif()  # type: ignore[attr-defined]
            if not raw_exif:
                return gps_info

            # البحث عن وسم GPS داخل بيانات EXIF
            gps_tag_id = next(
                (tid for tid, name in TAGS.items() if name == "GPSInfo"), None
            )
            if gps_tag_id is None or gps_tag_id not in raw_exif:
                return gps_info

            raw_gps: dict = raw_exif[gps_tag_id]
            gps_decoded = {GPSTAGS.get(k, k): v for k, v in raw_gps.items()}

            # استخراج خط العرض
            lat = self._dms_to_decimal(
                gps_decoded.get("GPSLatitude"),
                gps_decoded.get("GPSLatitudeRef", "N"),
            )
            # استخراج خط الطول
            lon = self._dms_to_decimal(
                gps_decoded.get("GPSLongitude"),
                gps_decoded.get("GPSLongitudeRef", "E"),
            )

            if lat is not None and lon is not None:
                gps_info = {
                    "available"         : True,
                    "latitude_dd"       : round(lat, 7),   # DD = Decimal Degrees
                    "longitude_dd"      : round(lon, 7),
                    "latitude_ref"      : gps_decoded.get("GPSLatitudeRef", "N"),
                    "longitude_ref"     : gps_decoded.get("GPSLongitudeRef", "E"),
                    "altitude_m"        : self._parse_altitude(
                                            gps_decoded.get("GPSAltitude"),
                                            gps_decoded.get("GPSAltitudeRef", 0),
                                          ),
                    "gps_speed"         : str(gps_decoded.get("GPSSpeed", "N/A")),
                    "gps_track"         : str(gps_decoded.get("GPSTrack", "N/A")),
                    "gps_timestamp"     : str(gps_decoded.get("GPSTimeStamp", "N/A")),
                    "gps_datestamp"     : str(gps_decoded.get("GPSDateStamp", "N/A")),
                    "google_maps_url"   : f"https://www.google.com/maps?q={round(lat,7)},{round(lon,7)}",
                    "google_maps_embed" : f"https://maps.google.com/maps/place/{round(lat,7)},{round(lon,7)}",
                }

        except Exception as exc:
            gps_info["error"] = str(exc)

        return gps_info

    @staticmethod
    def _dms_to_decimal(dms_values: Any, ref: str) -> float | None:
        """
        يحوّل إحداثيات DMS (Degrees, Minutes, Seconds) إلى درجات عشرية.

        مثال: (32°, 14', 30.5", "N")  →  32.241806°
        """
        if not dms_values or len(dms_values) < 3:
            return None
        try:
            def to_float(val: Any) -> float:
                """يحوّل كسر IFD (tuple) أو رقماً عادياً إلى float."""
                if hasattr(val, "numerator"):          # IFDRational
                    return float(val.numerator) / float(val.denominator)
                if isinstance(val, tuple) and len(val) == 2:
                    return float(val[0]) / float(val[1])
                return float(val)

            degrees = to_float(dms_values[0])
            minutes = to_float(dms_values[1])
            seconds = to_float(dms_values[2])
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

            # الاتجاه الجنوبي أو الغربي يعطي قيمة سالبة
            if ref in ("S", "W"):
                decimal = -decimal
            return decimal
        except Exception:
            return None

    @staticmethod
    def _parse_altitude(alt_val: Any, alt_ref: Any) -> str | None:
        """يحوّل قيمة الارتفاع ومرجعيته إلى نص مقروء."""
        if alt_val is None:
            return None
        try:
            if hasattr(alt_val, "numerator"):
                alt = float(alt_val.numerator) / float(alt_val.denominator)
            elif isinstance(alt_val, tuple):
                alt = float(alt_val[0]) / float(alt_val[1])
            else:
                alt = float(alt_val)

            prefix = "Below Sea Level" if (alt_ref and int(alt_ref) == 1) else "Above Sea Level"
            return f"{round(alt, 2)} m {prefix}"
        except Exception:
            return str(alt_val)

    # ══════════════════════════════════════════════════════════════════════════
    # 4. بيانات IPTC / XMP (متاحة في بعض الصور)
    # ══════════════════════════════════════════════════════════════════════════
    def _extract_iptc_xmp(self) -> dict[str, Any]:
        """
        يستخرج بيانات IPTC/XMP المتعلقة بحقوق النشر والكاتب
        والتسميات التوضيحية — إن وُجدت.
        """
        result: dict[str, Any] = {}
        try:
            img = self._open_pil_image()
            info = img.info or {}

            # بيانات IPTC
            if "iptc_info" in info:
                result["iptc"] = {str(k): str(v) for k, v in info["iptc_info"].items()}

            # بيانات XMP (نصية XML مضمّنة)
            if "xmp" in info:
                result["xmp_raw"] = info["xmp"].decode("utf-8", errors="replace")[:2000]

            # بيانات PNG الوصفية
            for key in ("comment", "Comment", "description", "Title", "Author",
                        "Copyright", "Software", "Creation Time"):
                if key in info:
                    result[key.lower()] = str(info[key])

            # بيانات TIFF الإضافية
            if hasattr(img, "tag_v2"):
                result["tiff_tags"] = {
                    str(k): str(v)[:200]
                    for k, v in img.tag_v2.items()  # type: ignore[attr-defined]
                }

        except Exception as exc:
            result["error"] = str(exc)

        return result

    # ══════════════════════════════════════════════════════════════════════════
    # نقطة الدخول الرئيسية
    # ══════════════════════════════════════════════════════════════════════════
    def extract_all(self) -> dict[str, Any]:
        """
        يجمع كل البيانات الوصفية في قاموس واحد منظم.

        العائد:
            dict مقسّم إلى أقسام:
                - basic_info  : البيانات الأساسية للملف والصورة
                - exif        : بيانات الكاميرا والتعريض
                - gps         : إحداثيات الموقع الجغرافي
                - iptc_xmp    : بيانات النشر والحقوق
                - extraction_info: معلومات عن عملية الاستخراج
        """
        result: dict[str, Any] = {
            "extraction_info": {
                "extracted_at"   : datetime.now().isoformat(),
                "extractor_version": "2.0.0",
                "source_file"    : str(self.image_path),
            }
        }

        # ── 1. البيانات الأساسية ───────────────────────────────────────────
        result["basic_info"] = self._safe_extract("basic_info", self._extract_basic_info)

        # ── 2. بيانات EXIF ─────────────────────────────────────────────────
        result["exif"] = self._safe_extract("exif", self._extract_exif_data)

        # ── 3. بيانات GPS ──────────────────────────────────────────────────
        result["gps"] = self._safe_extract("gps", self._extract_gps_data)

        # ── 4. بيانات IPTC/XMP ────────────────────────────────────────────
        result["iptc_xmp"] = self._safe_extract("iptc_xmp", self._extract_iptc_xmp)

        return result

    @staticmethod
    def _safe_extract(section: str, extractor_func) -> dict:
        """
        يُشغّل دالة الاستخراج داخل try-except لضمان
        عدم توقف البرنامج بسبب خطأ في قسم واحد.
        """
        try:
            return extractor_func()
        except Exception as exc:
            return {
                "error"  : f"فشل استخراج قسم '{section}'",
                "details": str(exc),
            }

    # ══════════════════════════════════════════════════════════════════════════
    # التصدير
    # ══════════════════════════════════════════════════════════════════════════
    def to_json(self, indent: int = 2, include_raw: bool = False) -> str:
        """
        يُصدّر البيانات بتنسيق JSON.

        المعاملات:
            indent      : مستوى المسافة البادئة (افتراضي: 2)
            include_raw : تضمين البيانات الخام من Pillow/exifread
        """
        data = self.extract_all()
        if not include_raw and "exif" in data and "raw_tags" in data["exif"]:
            del data["exif"]["raw_tags"]
        return json.dumps(data, ensure_ascii=False, indent=indent, default=str)

    def save_json(self, output_path: str | Path | None = None,
                  include_raw: bool = False) -> Path:
        """
        يحفظ البيانات في ملف JSON.

        المعاملات:
            output_path : مسار الحفظ (افتراضي: نفس مجلد الصورة باسم <image>.metadata.json)
            include_raw : تضمين البيانات الخام
        العائد:
            Path: مسار الملف المحفوظ.
        """
        if output_path is None:
            output_path = self.image_path.with_suffix(".metadata.json")
        output_path = Path(output_path)
        output_path.write_text(
            self.to_json(include_raw=include_raw),
            encoding="utf-8"
        )
        return output_path

    @staticmethod
    def pretty_print(data: dict[str, Any], include_raw: bool = False) -> None:
        """
        يطبع البيانات بشكل منسق وجميل في الـ Terminal.

        المعاملات:
            data        : القاموس العائد من extract_all()
            include_raw : طباعة البيانات الخام (قد تكون طويلة جداً)
        """
        SEP  = "═" * 70
        SEP2 = "─" * 70

        def _print_section(title: str, content: dict, depth: int = 0) -> None:
            indent = "  " * depth
            for key, value in content.items():
                if key == "raw_tags" and not include_raw:
                    continue
                if isinstance(value, dict):
                    print(f"{indent}  📂 {key}:")
                    _print_section(key, value, depth + 1)
                elif value not in (None, "", "N/A", "None"):
                    print(f"{indent}  ✦ {key:<28}: {value}")

        print(f"\n{SEP}")
        print(f"  🖼️  تقرير البيانات الوصفية للصورة")
        if "extraction_info" in data:
            print(f"  📅 {data['extraction_info'].get('extracted_at', '')}")
            print(f"  📄 {data['extraction_info'].get('source_file', '')}")
        print(SEP)

        sections = {
            "basic_info" : ("📋", "البيانات الأساسية"),
            "exif"       : ("📷", "بيانات EXIF (الكاميرا والتعريض)"),
            "gps"        : ("🌍", "بيانات الموقع الجغرافي (GPS)"),
            "iptc_xmp"   : ("📝", "بيانات IPTC / XMP"),
        }

        for section_key, (icon, label) in sections.items():
            if section_key not in data:
                continue
            content = data[section_key]
            if not content or content == {"available": False}:
                continue

            print(f"\n{SEP2}")
            print(f"  {icon}  {label}")
            print(SEP2)
            _print_section(label, content)

        print(f"\n{SEP}\n")

    # ══════════════════════════════════════════════════════════════════════════
    # دوال مساعدة
    # ══════════════════════════════════════════════════════════════════════════
    def _open_pil_image(self) -> Image.Image:
        """يفتح الصورة مرة واحدة ويخزّنها مؤقتاً تجنباً لإعادة الفتح."""
        if self._pil_image is None:
            if self.image_path:
                self._pil_image = Image.open(self.image_path)
            else:
                import io
                self._pil_image = Image.open(io.BytesIO(self.file_bytes))
        return self._pil_image

    @staticmethod
    def _parse_aperture(raw: str | None) -> str | None:
        """يحوّل قيمة FNumber إلى تنسيق f/2.8 المألوف."""
        if not raw:
            return None
        try:
            if "/" in str(raw):
                num, den = raw.split("/")
                val = float(num) / float(den)
            else:
                val = float(raw)
            return f"f/{val:.1f}" if val else None
        except Exception:
            return raw

    @staticmethod
    def _parse_focal(raw: str | None) -> str | None:
        """يحوّل FocalLength من كسر إلى mm."""
        if not raw:
            return None
        try:
            if "/" in str(raw):
                num, den = raw.split("/")
                val = float(num) / float(den)
            else:
                val = float(raw)
            return f"{val:.1f} mm"
        except Exception:
            return raw

    @staticmethod
    def _parse_dt(raw: str | None) -> str | None:
        """يحوّل تنسيق EXIF للتاريخ (2024:07:15 14:30:00) إلى ISO 8601."""
        if not raw:
            return None
        try:
            dt = datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S")
            return dt.isoformat()
        except Exception:
            return raw

    @staticmethod
    def _map_orientation(raw: str | None) -> str | None:
        """يحوّل رقم Orientation إلى وصف نصي."""
        if not raw:
            return None
        try:
            return ImageMetadataExtractor.ORIENTATION_MAP.get(int(raw), raw)
        except Exception:
            return raw

    @staticmethod
    def _map_exposure_program(raw: str | None) -> str | None:
        """يحوّل رقم ExposureProgram إلى وصف نصي."""
        programs = {
            "0": "Not Defined", "1": "Manual", "2": "Normal Program",
            "3": "Aperture Priority", "4": "Shutter Priority",
            "5": "Creative (depth of field bias)",
            "6": "Action (fast shutter speed bias)",
            "7": "Portrait", "8": "Landscape",
        }
        return programs.get(str(raw), raw) if raw else None

    @staticmethod
    def _map_res_unit(raw: str | None) -> str | None:
        """يحوّل رقم ResolutionUnit إلى وصف نصي."""
        units = {"1": "No unit", "2": "Inch (DPI)", "3": "Centimeter (DPCM)"}
        return units.get(str(raw), raw) if raw else None

    @staticmethod
    def _remove_none_values(data: Any) -> Any:
        """يُزيل القيم الفارغة من القاموس بشكل متكرر (Recursive)."""
        if isinstance(data, dict):
            return {
                k: ImageMetadataExtractor._remove_none_values(v)
                for k, v in data.items()
                if v not in (None, "", "N/A", "None", "0")
            }
        if isinstance(data, list):
            return [
                ImageMetadataExtractor._remove_none_values(i)
                for i in data
                if i not in (None, "")
            ]
        return data


# ══════════════════════════════════════════════════════════════════════════════
# مثال تشغيلي (Usage Example)
# ══════════════════════════════════════════════════════════════════════════════

def demo() -> None:
    """
    مثال كامل على كيفية استخدام الـ Class:

        1. استخراج البيانات وطباعتها بشكل جميل
        2. الحصول على بيانات JSON جاهزة للاستخدام
        3. حفظ البيانات في ملف JSON
        4. الوصول إلى بيانات محددة مثل إحداثيات GPS
    """
    import sys

    # ── تحديد مسار الصورة ─────────────────────────────────────────────────────
    if len(sys.argv) > 1:
        image_path = sys.argv[1]   # من سطر الأوامر: python script.py photo.jpg
    else:
        # للتجربة: تحديد مسار هنا مباشرةً
        image_path = "sample.jpg"
        print(f"⚠️  لم يُحدَّد مسار صورة. جاري محاولة فتح: '{image_path}'")
        print("    الاستخدام: python image_metadata_extractor.py <مسار_الصورة>\n")

    # ── إنشاء كائن المستخرج ───────────────────────────────────────────────────
    try:
        extractor = ImageMetadataExtractor(image_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ خطأ: {e}")
        return

    print("⏳ جاري استخراج البيانات الوصفية ...\n")

    # ── 1. استخراج كل البيانات ────────────────────────────────────────────────
    metadata = extractor.extract_all()

    # ── 2. طباعة منسّقة وجميلة ───────────────────────────────────────────────
    ImageMetadataExtractor.pretty_print(metadata)

    # ── 3. الوصول إلى بيانات محددة ───────────────────────────────────────────
    print("── أمثلة على الوصول المباشر للبيانات ──")

    basic = metadata.get("basic_info", {})
    print(f"  📁 اسم الملف    : {basic.get('file_name', 'N/A')}")
    print(f"  📐 الأبعاد      : {basic.get('width_px')}×{basic.get('height_px')} px")
    print(f"  💾 الحجم        : {basic.get('file_size_mb')} MB")

    exif = metadata.get("exif", {})
    camera = exif.get("camera", {})
    exposure = exif.get("exposure", {})
    print(f"  📷 الكاميرا     : {camera.get('make', 'N/A')} {camera.get('model', '')}")
    print(f"  ⏱️  سرعة الغالق  : {exposure.get('shutter_speed', 'N/A')}")
    print(f"  🔆 فتحة العدسة  : {exposure.get('aperture_fstop', 'N/A')}")
    print(f"  📊 ISO           : {exposure.get('iso', 'N/A')}")
    print(f"  🔭 البعد البؤري  : {exposure.get('focal_length_mm', 'N/A')}")

    gps = metadata.get("gps", {})
    if gps.get("available"):
        print(f"\n  🌍 خط العرض    : {gps.get('latitude_dd')}")
        print(f"  🌍 خط الطول    : {gps.get('longitude_dd')}")
        print(f"  🗺️  Google Maps  : {gps.get('google_maps_url')}")
    else:
        print("\n  🌍 GPS          : غير متوفر في هذه الصورة")

    # ── 4. الحصول على JSON جاهز للاستخدام في API ──────────────────────────────
    print("\n── تصدير JSON (أول 500 حرف) ──")
    json_output = extractor.to_json(indent=2, include_raw=False)
    print(json_output[:500] + "\n  ...")

    # ── 5. حفظ ملف JSON ───────────────────────────────────────────────────────
    try:
        saved_path = extractor.save_json(include_raw=False)
        print(f"\n✅ تم حفظ ملف JSON في: {saved_path}")
    except Exception as e:
        print(f"\n⚠️  لم يتم حفظ ملف JSON: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# تشغيل مباشر من سطر الأوامر
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    demo()
