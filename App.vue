<template>
  <div class="main-layout" :class="{ 'light-theme': !isDark }">
    <MouseTrail />
    <AIGHero :isArabic="isArabic" :isDark="isDark" @toggleLang="toggleLanguage" @toggleTheme="toggleTheme" @showLogs="isLogsModalOpen = true" />
    <div id="page-2" class="app-container" :class="{ 'rtl-mode': isArabic, 'light-theme': !isDark }" :dir="isArabic ? 'rtl' : 'ltr'">
      <div class="content-wrapper">
      


      <main class="main-content">
        
        <div class="panel-left">


          <div class="upload-section">
            <div 
              class="drop-zone"
              :class="{ 'preview-active': imagePreview, 'drag-active': isDragOver }"
              @dragover.prevent="isDragOver = true"
              @dragleave.prevent="isDragOver = false"
              @drop.prevent="handleDrop"
              @click="$refs.fileInput.click()"
            >
              <input type="file" ref="fileInput" hidden @change="handleFileUpload" accept="image/*">
              
              <div v-if="!imagePreview" class="zone-prompt">
                <div class="upload-icon-circle">
                  <CloudUpload class="new-upload-icon" />
                </div>
                <h3 class="new-zone-title">{{ isArabic ? 'قم بإسقاط الصورة هنا لفحصها' : 'Drop the image here to scan' }}</h3>
                <p class="new-zone-subtitle">{{ isArabic ? 'أو انقر لاختيار ملف من جهازك' : 'Or click to select a file from your device' }}</p>
                <div class="supported-formats">
                  <span class="format-badge">JPEG</span>
                  <span class="format-badge">PNG</span>
                  <span class="format-badge">JPG</span>
                </div>
              </div>

              <div v-else class="zone-preview">
                <img :src="imagePreview" class="img-thumb" alt="Face Preview">
                <div class="img-controls">
                  <button class="clear-btn" @click.stop="removeImage">
                    <i class="fas fa-trash-alt"></i> {{ isArabic ? 'إلغاء' : 'Remove' }}
                  </button>
                </div>
              </div>
            </div>

            <button class="execute-btn" v-if="imagePreview" @click="startAnalysisPipeline" :disabled="isAnalyzing">
              <i class="fas fa-sliders-h" :class="{ 'fa-spin': isAnalyzing }"></i>
              {{ isAnalyzing ? (isArabic ? 'جاري الفحص السلوكي للبكسل...' : 'Analyzing Pixel Behavior...') : (isArabic ? 'بدء معالجة وفحص الصورة' : 'Execute Core Pipeline') }}
            </button>
          </div>

          <div class="terminal-panel" v-if="showTerminal">
            <div class="terminal-bar">
              <div class="window-dots"><span class="d-red"></span><span class="d-yellow"></span><span class="d-green"></span></div>
              <span class="bar-title">CORE_PIPELINE_OUTPUT</span>
            </div>
            <div class="terminal-logs">
              <div class="log-row" :class="{ 'active-row': pipelineStep >= 1 }">
                <span class="tag-success">[SUCCESS]</span>
                <span class="txt">
                  <span v-if="analysisResult">
                    {{ isArabic ? `تم استخلاص وتصحيح عدد (${analysisResult.metadata.faces_detected}) وجوه بنجاح.` : `Extracted and aligned ${analysisResult.metadata.faces_detected} face(s) successfully.` }}
                  </span>
                  <span v-else>
                    {{ isArabic ? 'جاري التعرف على ملامح الوجه وعزل الخلفية...' : 'Detecting face contours and separating background...' }}
                  </span>
                </span>
              </div>
              <div class="log-row" :class="{ 'active-row': pipelineStep >= 2 }">
                <span class="tag-success">[SUCCESS]</span>
                <span class="txt">
                  <span v-if="analysisResult">
                    {{ isArabic ? 'تم تعديل اتجاه ومحاذاة الملامح بنجاح.' : 'Face alignment and contours correction completed successfully.' }}
                  </span>
                  <span v-else>
                    {{ isArabic ? 'جاري تحليل زوايا الميلان وتعديل اتجاه الوجه...' : 'Analyzing tilt angles and correcting face direction...' }}
                  </span>
                </span>
              </div>
              <div class="log-row" :class="{ 'active-row': pipelineStep >= 3 }">
                <span class="tag-info">[REPORT]</span>
                <span class="txt font-bold">{{ isArabic ? 'تحليل المخرجات والتقرير الوصفي المولد:' : 'Output report and generated metadata description:' }}</span>
                <div class="final-desc-box" :style="{ borderColor: (analysisResult && analysisResult.verdict.is_deepfake) ? '#ef4444' : '#10b981' }">
                  <span v-if="analysisResult">
                    {{ isArabic ? analysisResult.verdict.description_ar : analysisResult.verdict.description_en }}
                  </span>
                  <span v-else>
                    {{ isArabic ? 'جاري معالجة بكسلات الصورة وإعداد تقرير الفحص...' : 'Processing image pixels and generating forensic report...' }}
                  </span>
                </div>
              </div>
            </div>
          </div>

        </div>

        <div class="panel-right">
          <!-- NO FACE DETECTED BLOCK -->
          <div v-if="analysisResult && !isAnalyzing && analysisResult.faces && analysisResult.faces.length === 0" class="no-face-error-card">
            <i class="fas fa-user-slash"></i>
            <h3>{{ isArabic ? 'لم يتم العثور على وجه!' : 'No Face Detected!' }}</h3>
            <p>{{ isArabic ? 'عذراً، لم يتمكن النظام من العثور على أي وجه في هذه الصورة. تقنيات الفحص المتقدمة (مثل ELA) تعتمد على وجود وجه للتحليل الجنائي. يرجى رفع صورة أخرى تحتوي على وجه واضح.' : 'Sorry, the system could not find any face in this image. Forensic techniques rely on face detection. Please upload another image with a clear face.' }}</p>
          </div>

          <!-- Result Tabs Navigation -->
          <div v-if="analysisResult && !isAnalyzing && analysisResult.faces && analysisResult.faces.length > 0" class="result-tabs">
            <button class="tab-btn" :class="{ active: activeTab === 'ai' }" @click="activeTab = 'ai'">
              <i class="fas fa-brain"></i>
              <span>{{ isArabic ? 'نموذج الذكاء الاصطناعي (AI)' : 'AI Deepfake Model' }}</span>
            </button>
            <button class="tab-btn" :class="{ active: activeTab === 'ela' }" @click="activeTab = 'ela'">
              <i class="fas fa-layer-group"></i>
              <span>{{ isArabic ? 'مستوى الخطأ (ELA)' : 'Error Level Analysis' }}</span>
            </button>
            <button class="tab-btn" :class="{ active: activeTab === 'metadata' }" @click="activeTab = 'metadata'">
              <i class="fas fa-info-circle"></i>
              <span>{{ isArabic ? 'بيانات الصورة (Metadata)' : 'Image Metadata' }}</span>
            </button>
          </div>

          <!-- Timeline View when results are ready and AI tab is active -->
          <div v-if="analysisResult && !isAnalyzing && activeTab === 'ai' && analysisResult.faces && analysisResult.faces.length > 0" class="timeline">
            <!-- Part 1: Face Extraction -->
            <div class="timeline-item">
              <div class="timeline-badge" style="background-color: #38bdf8;">
                <i class="fas fa-crop-simple"></i>
              </div>
              <div class="timeline-card" style="--card-border-color: #38bdf8;">
                <h4 class="timeline-card-title">
                  <i class="fas fa-user-circle text-blue"></i>
                  {{ isArabic ? '1. استخلاص الوجوه وتصحيحها' : '1. Face Extraction & Alignment' }}
                </h4>
                <div class="timeline-card-text">
                  <p style="margin: 0 0 10px 0; font-size: 0.8rem; color: #64748b;">
                    {{ isArabic ? 'تم عزل وتدوير الوجوه المكتشفة بالكامل:' : 'Extracted and auto-aligned biometric face regions:' }}
                  </p>
                  <div class="faces-list">
                    <template v-for="face in analysisResult.faces" :key="face.index">
                      <div v-if="face.aligned" class="face-detail-card" :style="{ borderColor: face.fake_probability > 50 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)' }">
                        <div class="face-header-info">
                          <span class="face-avatar-label"><i class="fas fa-user-circle"></i> {{ isArabic ? 'وجه' : 'Face' }} #{{ face.index + 1 }}</span>
                          <span class="face-result-badge" :class="face.fake_probability > 50 ? 'bg-red' : 'bg-green'">
                            {{ face.fake_probability > 50 ? (isArabic ? 'مزيف' : 'Fake') : (isArabic ? 'حقيقي' : 'Real') }}
                            ({{ face.fake_probability > 50 ? face.fake_probability : face.real_probability }}%)
                          </span>
                        </div>
                        <div class="face-images-row">
                          <div class="face-image-box">
                            <span class="face-box-title">{{ isArabic ? 'الوجه المستخلص' : 'Aligned Face' }}</span>
                            <img :src="face.aligned" class="face-img-render" />
                          </div>
                          <div class="face-image-box" v-if="face.gradcam_image">
                            <span class="face-box-title gradcam-title"><i class="fas fa-eye"></i> {{ isArabic ? 'تركيز الموديل (Grad-CAM)' : 'Grad-CAM Focus' }}</span>
                            <img :src="face.gradcam_image" class="face-img-render" />
                          </div>
                        </div>
                      </div>
                    </template>
                    <div v-if="analysisResult.faces.filter(f => f.aligned).length === 0" class="no-faces-message">
                      <i class="fas fa-user-slash"></i> {{ isArabic ? 'لم يتم كشف وجوه' : 'No faces detected' }}
                    </div>
                  </div>
                </div>
              </div>
            </div>



            <!-- Part 3: Result Bars -->
            <div class="face-result-bars-container">
              <div 
                v-for="face in analysisResult.faces" 
                :key="'res-'+face.index"
                class="face-result-bar"
                :class="{ 'is-real': face.fake_probability <= 50 }"
              >
                <div class="bar-header">
                  <span class="bar-verdict" :class="face.fake_probability > 50 ? 'text-red' : 'text-green'">
                    {{ face.fake_probability > 50 ? 'FAKE' : 'REAL' }}
                  </span>
                  <span class="bar-face-label">{{ isArabic ? 'وجه ' : 'Face ' }}{{ face.index + 1 }}</span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill" :class="face.fake_probability > 50 ? 'bg-red' : 'bg-green'" :style="{ width: (face.fake_probability > 50 ? face.fake_probability : face.real_probability) + '%' }"></div>
                </div>
                <div class="bar-footer">
                  <span class="bar-percentage">{{ (face.fake_probability > 50 ? face.fake_probability : face.real_probability).toFixed(1) }}% {{ isArabic ? 'الثقة' : 'Confidence' }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- ELA Details View when results are ready and ELA tab is active -->
          <div v-if="analysisResult && !isAnalyzing && activeTab === 'ela' && analysisResult.faces && analysisResult.faces.length > 0" class="ela-details-container">
            <div class="ela-verdict-card" :class="'ela-' + analysisResult.ela.verdict">
              <div class="ela-verdict-icon">
                <i class="fas" :class="{
                  'fa-check-circle': analysisResult.ela.verdict === 'clean',
                  'fa-exclamation-triangle': analysisResult.ela.verdict === 'suspicious',
                  'fa-triangle-exclamation': analysisResult.ela.verdict === 'tampered'
                }"></i>
              </div>
              <div class="ela-verdict-content">
                <h3 class="ela-verdict-title">
                  <span v-if="analysisResult.ela.verdict === 'clean'">{{ isArabic ? 'الصورة سليمة (غير معدلة بكسلياً)' : 'Image Clean (No Pixel Tampering)' }}</span>
                  <span v-else-if="analysisResult.ela.verdict === 'suspicious'">{{ isArabic ? 'الصورة مشبوهة (تحليل غير حاسم)' : 'Image Suspicious (Inconclusive)' }}</span>
                  <span v-else>{{ isArabic ? 'آثار تعديل بكسلات (Image Tampered)' : 'Pixel Tampering Detected' }}</span>
                </h3>
                <p class="ela-verdict-desc">
                  <span v-if="analysisResult.ela.verdict === 'clean'">
                    {{ isArabic ? 'معامل التباين والكتل الشاذة متجانس، لا توجد فروق ضغط غير طبيعية.' : 'Block CV and outliers are within limits; no anomalous recompression differences found.' }}
                  </span>
                  <span v-else-if="analysisResult.ela.verdict === 'suspicious'">
                    {{ isArabic ? 'بعض الكتل تظهر تفاوتاً طفيفاً في جودة الضغط، يوصى بالتحقق اليدوي.' : 'Some image blocks exhibit subtle recompression variations. Manual review recommended.' }}
                  </span>
                  <span v-else>
                    {{ isArabic ? 'تفاوت كبير في معامل التباين والكتل الشاذة. دليل إحصائي على تعديل بكسل الصورة.' : 'High variance detected in block compression. Strong statistical indicators of pixel manipulation.' }}
                  </span>
                </p>
              </div>
            </div>



            <!-- Side by Side Comparison -->
            <div class="ela-visuals-box">
              <h4 class="section-title"><i class="fas fa-images"></i> {{ isArabic ? 'مقارنة الصورة الأصلية بخريطة ELA' : 'Original vs ELA Map Comparison' }}</h4>
              <div class="ela-images-comparison">
                <div class="comparison-panel-img">
                  <span class="panel-label">{{ isArabic ? 'الأصلية' : 'Original' }}</span>
                  <img :src="imagePreview" class="comp-img" />
                </div>
                <div class="comparison-panel-img">
                  <span class="panel-label ELA-label">{{ isArabic ? 'خريطة ELA' : 'ELA Map' }}</span>
                  <img :src="analysisResult.ela.ela_image" class="comp-img" />
                </div>
              </div>
            </div>

            <!-- Full Report text -->
            <div class="ela-report-box">
              <div class="ela-report-header">
                <span>{{ isArabic ? 'تقرير الجنايات الرقمية الكامل (TXT)' : 'Forensic Text Report (TXT)' }}</span>
                <button class="copy-report-btn" @click="copyReportText(analysisResult.ela.report)">
                  <i class="fas" :class="reportCopied ? 'fa-check text-green' : 'fa-copy'"></i>
                  <span class="copy-tooltip" v-if="reportCopied">{{ isArabic ? ' تم النسخ!' : ' Copied!' }}</span>
                </button>
              </div>
              <pre class="ela-report-content">{{ analysisResult.ela.report }}</pre>
            </div>
          </div>

          <!-- Metadata Tab Content -->
          <div v-if="analysisResult && !isAnalyzing && activeTab === 'metadata' && analysisResult.faces && analysisResult.faces.length > 0" class="metadata-details-container">
            <!-- Checking if metadata is successfully extracted -->
            <div v-if="analysisResult.detailed_metadata && analysisResult.detailed_metadata.success" class="metadata-grid-wrapper">
              
              <!-- 1. Basic Info Section -->
              <div class="metadata-section-card" v-if="analysisResult.detailed_metadata.data.basic_info">
                <h4 class="section-title"><i class="fas fa-file-image"></i> {{ isArabic ? 'البيانات الأساسية للملف' : 'Basic File Information' }}</h4>
                <div class="details-grid">
                  <div class="details-row-cell">
                    <span class="cell-label">{{ isArabic ? 'اسم الملف' : 'Filename' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.basic_info.file_name }}</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.basic_info.format">
                    <span class="cell-label">{{ isArabic ? 'صيغة الصورة' : 'Image Format' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.basic_info.format }}</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.basic_info.file_size_mb">
                    <span class="cell-label">{{ isArabic ? 'حجم الملف' : 'File Size' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.basic_info.file_size_mb }} MB</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.basic_info.width_px">
                    <span class="cell-label">{{ isArabic ? 'الأبعاد (العرض × الارتفاع)' : 'Dimensions (W x H)' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.basic_info.width_px }} × {{ analysisResult.detailed_metadata.data.basic_info.height_px }} px</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.basic_info.megapixels">
                    <span class="cell-label">{{ isArabic ? 'ميجابكسل' : 'Megapixels' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.basic_info.megapixels }} MP</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.basic_info.aspect_ratio">
                    <span class="cell-label">{{ isArabic ? 'نسبة الأبعاد' : 'Aspect Ratio' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.basic_info.aspect_ratio }}</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.basic_info.color_space">
                    <span class="cell-label">{{ isArabic ? 'نظام الألوان' : 'Color Space' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.basic_info.color_space }}</span>
                  </div>
                </div>
              </div>

              <!-- 2. Camera Info Section -->
              <div class="metadata-section-card" v-if="analysisResult.detailed_metadata.data.exif && analysisResult.detailed_metadata.data.exif.camera && Object.keys(analysisResult.detailed_metadata.data.exif.camera).length > 0">
                <h4 class="section-title"><i class="fas fa-camera"></i> {{ isArabic ? 'آلة التصوير والعدسة' : 'Camera & Lens' }}</h4>
                <div class="details-grid">
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.exif.camera.make">
                    <span class="cell-label">{{ isArabic ? 'الشركة المصنعة' : 'Manufacturer' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.exif.camera.make }}</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.exif.camera.model">
                    <span class="cell-label">{{ isArabic ? 'طراز الكاميرا' : 'Camera Model' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.exif.camera.model }}</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.exif.camera.lens_model">
                    <span class="cell-label">{{ isArabic ? 'طراز العدسة' : 'Lens Model' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.exif.camera.lens_model }}</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.exif.camera.software">
                    <span class="cell-label">{{ isArabic ? 'برمجية النظام' : 'Software' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.exif.camera.software }}</span>
                  </div>
                </div>
              </div>

              <!-- 3. Exposure Info Section -->
              <div class="metadata-section-card" v-if="analysisResult.detailed_metadata.data.exif && analysisResult.detailed_metadata.data.exif.exposure && Object.keys(analysisResult.detailed_metadata.data.exif.exposure).length > 0">
                <h4 class="section-title"><i class="fas fa-sliders"></i> {{ isArabic ? 'إعدادات التعريض والتصوير' : 'Exposure & Capture Settings' }}</h4>
                <div class="details-grid">
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.exif.exposure.shutter_speed">
                    <span class="cell-label">{{ isArabic ? 'سرعة الغالق' : 'Shutter Speed' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.exif.exposure.shutter_speed }} s</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.exif.exposure.aperture_fstop">
                    <span class="cell-label">{{ isArabic ? 'فتحة العدسة' : 'Aperture' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.exif.exposure.aperture_fstop }}</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.exif.exposure.iso">
                    <span class="cell-label">{{ isArabic ? 'حساسية المستشعر (ISO)' : 'ISO' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.exif.exposure.iso }}</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.exif.exposure.focal_length_mm">
                    <span class="cell-label">{{ isArabic ? 'البعد البؤري' : 'Focal Length' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.exif.exposure.focal_length_mm }}</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.exif.exposure.exposure_program">
                    <span class="cell-label">{{ isArabic ? 'برنامج التعريض' : 'Exposure Program' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.exif.exposure.exposure_program }}</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.exif.exposure.white_balance">
                    <span class="cell-label">{{ isArabic ? 'توازن اللون الأبيض' : 'White Balance' }}</span>
                    <span class="cell-val">{{ analysisResult.detailed_metadata.data.exif.exposure.white_balance }}</span>
                  </div>
                  <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.exif.datetime && analysisResult.detailed_metadata.data.exif.datetime.original">
                    <span class="cell-label">{{ isArabic ? 'تاريخ التصوير الأصلي' : 'Date Taken' }}</span>
                    <span class="cell-val">{{ new Date(analysisResult.detailed_metadata.data.exif.datetime.original).toLocaleString(isArabic ? 'ar' : 'en') }}</span>
                  </div>
                </div>
              </div>

              <!-- 4. GPS Location Section -->
              <div class="metadata-section-card" v-if="analysisResult.detailed_metadata.data.gps && analysisResult.detailed_metadata.data.gps.available">
                <h4 class="section-title"><i class="fas fa-location-dot"></i> {{ isArabic ? 'الموقع الجغرافي (GPS)' : 'Geographic Location (GPS)' }}</h4>
                
                <div class="gps-data-block">
                  <div class="details-grid">
                    <div class="details-row-cell">
                      <span class="cell-label">{{ isArabic ? 'خط العرض' : 'Latitude' }}</span>
                      <span class="cell-val">{{ analysisResult.detailed_metadata.data.gps.latitude_dd }}° {{ analysisResult.detailed_metadata.data.gps.latitude_ref }}</span>
                    </div>
                    <div class="details-row-cell">
                      <span class="cell-label">{{ isArabic ? 'خط الطول' : 'Longitude' }}</span>
                      <span class="cell-val">{{ analysisResult.detailed_metadata.data.gps.longitude_dd }}° {{ analysisResult.detailed_metadata.data.gps.longitude_ref }}</span>
                    </div>
                    <div class="details-row-cell" v-if="analysisResult.detailed_metadata.data.gps.altitude_m">
                      <span class="cell-label">{{ isArabic ? 'الارتفاع عن سطح البحر' : 'Altitude' }}</span>
                      <span class="cell-val">{{ analysisResult.detailed_metadata.data.gps.altitude_m }}</span>
                    </div>
                  </div>
                  
                  <!-- Google Maps Link -->
                  <div class="maps-redirect-banner">
                    <i class="fas fa-map-location-dot"></i>
                    <div class="banner-text">
                      <strong>{{ isArabic ? 'موقع الصورة متوفر على الخريطة' : 'Image Location Available on Map' }}</strong>
                      <p>{{ isArabic ? 'يمكنك عرض موقع التقاط هذه الصورة على خرائط Google.' : 'You can view where this photo was taken on Google Maps.' }}</p>
                    </div>
                    <a :href="analysisResult.detailed_metadata.data.gps.google_maps_url" target="_blank" class="maps-btn">
                      {{ isArabic ? 'عرض الخريطة' : 'Open Map' }} <i class="fas fa-external-link-alt"></i>
                    </a>
                  </div>
                </div>
              </div>

            </div>
            
            <div v-else class="metadata-error-card">
              <i class="fas fa-circle-exclamation"></i>
              <span>{{ isArabic ? 'فشل استخراج البيانات الوصفية أو الملف لا يحتوي على EXIF.' : 'Metadata extraction failed or image does not contain EXIF parameters.' }}</span>
            </div>
          </div>

          <!-- Steps Stack shown while analyzing or when no results exist -->
          <div v-if="!analysisResult || isAnalyzing" class="steps-stack">


            <div v-if="analysisError" class="error-alert">
              <i class="fas fa-circle-exmark"></i>
              <div class="error-content">
                <strong>{{ isArabic ? 'خطأ في الاتصال بالسيرفر:' : 'Server Connection Error:' }}</strong>
                <span>{{ analysisError }}</span>
              </div>
            </div>
          </div>
        </div>

      </main>

      <footer class="footer">
        <div class="stat-block">
          <span class="v-text">99.8%</span>
          <span class="l-text">{{ isArabic ? 'نسبة دقة النموذج' : 'Model Accuracy' }}</span>
        </div>
        <div class="divider"></div>
        <div class="stat-block">
          <span class="v-text">Pipeline</span>
          <span class="l-text">{{ isArabic ? 'هيكلية المعالجة' : 'Architecture Style' }}</span>
        </div>
        <div class="divider"></div>
        <div class="stat-block">
          <span class="v-text">CapsuleNet</span>
          <span class="l-text">{{ isArabic ? 'المحرك الذكي' : 'AI Engine Core' }}</span>
        </div>
      </footer>

    </div>
    </div>

    <!-- Logs Modal -->
    <div v-if="isLogsModalOpen" class="logs-modal-overlay" @click="isLogsModalOpen = false">
      <div class="logs-modal-content" @click.stop :class="{ 'light-theme': !isDark, 'rtl-mode': isArabic }" :dir="isArabic ? 'rtl' : 'ltr'">
        <div class="modal-header">
          <h2><History class="header-icon" /> {{ isArabic ? 'سجل الفحوصات السابقة' : 'Recent Scan Logs' }}</h2>
          <button class="close-modal-btn" @click="isLogsModalOpen = false"><X class="close-icon" /></button>
        </div>
        
        <div class="logs-list" v-if="recentLogs.length > 0">
          <div v-for="(log, idx) in recentLogs" :key="log.id" class="log-list-item">
            <div class="log-item-image">
              <img :src="log.image" class="log-img" />
            </div>
            
            <div class="log-item-info">
              <div class="log-time-date">
                <span class="log-date">{{ log.timestamp.toLocaleDateString(isArabic ? 'ar-EG' : 'en-US') }}</span>
                <span class="log-time">{{ log.timestamp.toLocaleTimeString(isArabic ? 'ar-EG' : 'en-US', { hour: '2-digit', minute: '2-digit' }) }}</span>
              </div>
              <div class="log-result-badge" :class="log.isFake ? 'badge-fake' : 'badge-real'">
                <AlertTriangle v-if="log.isFake" class="result-icon" />
                <CheckCircle2 v-else class="result-icon" />
                <span>{{ log.isFake ? (isArabic ? 'صورة مزيفة (Fake)' : 'Fake Image') : (isArabic ? 'صورة حقيقية (Real)' : 'Real Image') }}</span>
              </div>
            </div>

            <div class="log-item-actions">
              <button class="log-action-btn btn-view" @click="viewLogResult(log)" :title="isArabic ? 'عرض النتيجة' : 'View Result'">
                <Eye class="action-icon" />
                <span>{{ isArabic ? 'عرض' : 'View' }}</span>
              </button>
              <button class="log-action-btn btn-download" @click="downloadLogPDF(log)" :title="isArabic ? 'تحميل كـ PDF' : 'Download PDF'" :disabled="downloadingLogId === log.id" :class="{ 'btn-loading': downloadingLogId === log.id }">
                <i v-if="downloadingLogId === log.id" class="fas fa-spinner fa-spin action-icon" style="font-size: 16px;"></i>
                <Download v-else class="action-icon" />
                <span>{{ downloadingLogId === log.id ? (isArabic ? 'جاري التحميل...' : 'Downloading...') : (isArabic ? 'تحميل' : 'Download') }}</span>
              </button>
            </div>
          </div>
        </div>
        <div v-else class="empty-logs">
          <BoxSelect class="empty-icon" />
          <p>{{ isArabic ? 'لم تقم بتجربة أي صور بعد. سجلاتك فارغة.' : 'You haven\'t tried any images yet. Logs are empty.' }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AIGHero from './components/AIGHero.vue'
import MouseTrail from './components/MouseTrail.vue'
import { CloudUpload, History, X, Download, Eye, CheckCircle2, AlertTriangle, BoxSelect, ShieldCheck } from 'lucide-vue-next'

const isArabic = ref(true)
const isDragOver = ref(false)
const isDark = ref(true)
const imagePreview = ref(null)
const uploadedFile = ref(null)
const isAnalyzing = ref(false)
const showTerminal = ref(false)
const pipelineStep = ref(0)
const fileInput = ref(null)
const analysisResult = ref(null)
const analysisError = ref(null)
const elaQuality = ref(90)
const activeTab = ref('ai')
const reportCopied = ref(false)
const isLogsModalOpen = ref(false)
const recentLogs = ref([])
const downloadingLogId = ref(null)

const viewLogResult = (log) => {
  imagePreview.value = log.image;
  analysisResult.value = log.result;
  isAnalyzing.value = false;
  showTerminal.value = true;
  pipelineStep.value = 3;
  isLogsModalOpen.value = false;
  
  setTimeout(() => {
    const resultsPanel = document.querySelector('.panel-right');
    if (resultsPanel) {
      resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, 100);
}

const generatePDFHtml = (log, isArabicLang) => {
  const result = log.result;
  const isFake = log.isFake;
  const dateStr = log.timestamp.toLocaleString(isArabicLang ? 'ar-EG' : 'en-US');
  
  let facesHtml = '';
  if (result.faces && result.faces.length > 0) {
    facesHtml = `
      <div class="avoid-break" style="margin-bottom: 30px; text-align: ${isArabicLang ? 'right' : 'left'};">
        <h3 style="font-size: 1.3rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 15px; color: #0f172a;" dir="${isArabicLang ? 'rtl' : 'ltr'}">${isArabicLang ? 'تحليل الوجوه (الذكاء الاصطناعي)' : 'Face Analysis (AI)'}</h3>
        <div style="display: flex; flex-wrap: wrap; gap: 20px; flex-direction: ${isArabicLang ? 'row-reverse' : 'row'};">
          ${result.faces.map(face => `
            <div style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; width: calc(50% - 10px); background: #f8fafc; box-sizing: border-box;">
              <div style="display: flex; justify-content: space-between; margin-bottom: 10px; font-weight: bold; flex-direction: ${isArabicLang ? 'row-reverse' : 'row'};">
                <span dir="${isArabicLang ? 'rtl' : 'ltr'}">${isArabicLang ? 'وجه' : 'Face'} #${face.index + 1}</span>
                <span style="padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; color: white; background: ${face.fake_probability > 50 ? '#ef4444' : '#10b981'};">
                  ${face.fake_probability > 50 ? 'FAKE' : 'REAL'} (${(face.fake_probability > 50 ? face.fake_probability : face.real_probability).toFixed(1)}%)
                </span>
              </div>
              <div style="display: flex; gap: 10px; flex-direction: ${isArabicLang ? 'row-reverse' : 'row'};">
                ${face.aligned ? `
                <div style="display: flex; flex-direction: column; gap: 5px; align-items: center;">
                  <span style="font-size: 0.75rem; color: #64748b;" dir="${isArabicLang ? 'rtl' : 'ltr'}">${isArabicLang ? 'الوجه المستخلص' : 'Aligned Face'}</span>
                  <img src="${face.aligned}" crossorigin="anonymous" style="width: 100px; height: 100px; object-fit: cover; border-radius: 6px; border: 1px solid #e2e8f0;" />
                </div>` : ''}
                ${face.gradcam_image ? `
                <div style="display: flex; flex-direction: column; gap: 5px; align-items: center;">
                  <span style="font-size: 0.75rem; color: #64748b;" dir="${isArabicLang ? 'rtl' : 'ltr'}">${isArabicLang ? 'تركيز الموديل' : 'Grad-CAM'}</span>
                  <img src="${face.gradcam_image}" crossorigin="anonymous" style="width: 100px; height: 100px; object-fit: cover; border-radius: 6px; border: 1px solid #e2e8f0;" />
                </div>` : ''}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  let elaHtml = '';
  if (result.ela) {
    let verdictText = '';
    const v = result.ela.verdict.toUpperCase();
    if (v === 'CLEAN') verdictText = isArabicLang ? 'سليمة (CLEAN)' : 'CLEAN';
    else if (v === 'TAMPERED') verdictText = isArabicLang ? 'معدلة (TAMPERED)' : 'TAMPERED';
    else verdictText = isArabicLang ? 'مشبوهة (SUSPICIOUS)' : 'SUSPICIOUS';

    elaHtml = `
      <div class="avoid-break" style="margin-bottom: 30px; text-align: ${isArabicLang ? 'right' : 'left'};">
        <h3 style="font-size: 1.3rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 15px; color: #0f172a;" dir="${isArabicLang ? 'rtl' : 'ltr'}">${isArabicLang ? 'تحليل مستوى الخطأ (ELA)' : 'Error Level Analysis (ELA)'}</h3>
        <div style="display: flex; gap: 20px; margin-bottom: 15px; flex-direction: ${isArabicLang ? 'row-reverse' : 'row'};">
          <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 10px;">
            <span dir="${isArabicLang ? 'rtl' : 'ltr'}">${isArabicLang ? 'الصورة الأصلية' : 'Original'}</span>
            <img src="${log.image}" crossorigin="anonymous" style="width: 100%; max-width: 250px; border: 1px solid #cbd5e1; border-radius: 6px;" />
          </div>
          <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 10px;">
            <span dir="${isArabicLang ? 'rtl' : 'ltr'}">${isArabicLang ? 'خريطة ELA' : 'ELA Map'}</span>
            <img src="${result.ela.ela_image}" crossorigin="anonymous" style="width: 100%; max-width: 250px; border: 1px solid #cbd5e1; border-radius: 6px;" />
          </div>
        </div>
        <div style="background: #f1f5f9; padding: 15px; border-radius: 6px; text-align: center; font-size: 1.1rem;" dir="${isArabicLang ? 'rtl' : 'ltr'}">
          <strong>${isArabicLang ? 'النتيجة (ELA):' : 'ELA Verdict:'} </strong> ${verdictText}
        </div>
      </div>
    `;
  }

  let metadataHtml = '';
  if (result.detailed_metadata && result.detailed_metadata.success && result.detailed_metadata.data.basic_info) {
    const basic = result.detailed_metadata.data.basic_info;
    const exif = result.detailed_metadata.data.exif;
    metadataHtml = `
      <div class="avoid-break" style="margin-bottom: 30px; text-align: ${isArabicLang ? 'right' : 'left'};">
        <h3 style="font-size: 1.3rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 15px; color: #0f172a;" dir="${isArabicLang ? 'rtl' : 'ltr'}">${isArabicLang ? 'البيانات الوصفية (Metadata)' : 'Image Metadata'}</h3>
        <table style="width: 100%; border-collapse: collapse; text-align: ${isArabicLang ? 'right' : 'left'};" dir="${isArabicLang ? 'rtl' : 'ltr'}">
          <tbody>
            ${basic.format ? `<tr><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;"><strong>${isArabicLang ? 'الصيغة' : 'Format'}</strong></td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">${basic.format}</td></tr>` : ''}
            ${basic.width_px ? `<tr><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;"><strong>${isArabicLang ? 'الأبعاد' : 'Dimensions'}</strong></td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">${basic.width_px} x ${basic.height_px}</td></tr>` : ''}
            ${(exif && exif.camera && exif.camera.make) ? `<tr><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;"><strong>${isArabicLang ? 'الكاميرا' : 'Camera'}</strong></td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">${exif.camera.make} ${exif.camera.model || ''}</td></tr>` : ''}
            ${(exif && exif.datetime && exif.datetime.original) ? `<tr><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;"><strong>${isArabicLang ? 'تاريخ الالتقاط' : 'Date Taken'}</strong></td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">${new Date(exif.datetime.original).toLocaleString(isArabicLang ? 'ar' : 'en')}</td></tr>` : ''}
          </tbody>
        </table>
      </div>
    `;
  }

  const verdictTitle = isFake ? (isArabicLang ? 'النتيجة النهائية: مزيفة' : 'Final Verdict: FAKE') : (isArabicLang ? 'النتيجة النهائية: حقيقية' : 'Final Verdict: REAL');
  const verdictDesc = isArabicLang ? result.verdict.description_ar : result.verdict.description_en;
  const verdictStyle = isFake ? "background: #fef2f2; border-color: #fecaca; color: #991b1b;" : "background: #f0fdf4; border-color: #bbf7d0; color: #166534;";
  const verdictTitleColor = isFake ? "#dc2626" : "#16a34a";

  return `
    <div style="width: 800px; background: #ffffff; color: #000000; padding: 40px; font-family: 'Tajawal', sans-serif; box-sizing: border-box; text-align: ${isArabicLang ? 'right' : 'left'};" dir="ltr">
      
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-direction: ${isArabicLang ? 'row-reverse' : 'row'}; border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; margin-bottom: 30px;">
        <div style="display: flex; align-items: center; gap: 15px; flex-direction: ${isArabicLang ? 'row-reverse' : 'row'};">
          <div style="width: 48px; height: 48px; background: #0ea5e9; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 24px;">Y</div>
          <div style="text-align: ${isArabicLang ? 'right' : 'left'};">
            <h1 style="margin: 0; font-size: 1.8rem; color: #0f172a;" dir="${isArabicLang ? 'rtl' : 'ltr'}">${isArabicLang ? 'نظام يقين للأدلة الجنائية' : 'Yaqeen Forensics System'}</h1>
            <p style="margin: 5px 0 0 0; color: #64748b; font-size: 1.1rem;" dir="${isArabicLang ? 'rtl' : 'ltr'}">${isArabicLang ? 'تقرير فحص التزييف العميق' : 'Deepfake Analysis Report'}</p>
          </div>
        </div>
        <div style="text-align: ${isArabicLang ? 'left' : 'right'}; font-size: 0.9rem; color: #475569; line-height: 1.6;" dir="${isArabicLang ? 'rtl' : 'ltr'}">
          <div><strong>${isArabicLang ? 'رقم التقرير:' : 'Report ID:'}</strong> YQ-${log.id}</div>
          <div><strong>${isArabicLang ? 'التاريخ:' : 'Date:'}</strong> ${dateStr}</div>
        </div>
      </div>

      <!-- Summary -->
      <div style="display: flex; gap: 30px; align-items: flex-start; margin-bottom: 30px; flex-direction: ${isArabicLang ? 'row-reverse' : 'row'};">
        <div style="flex: 1; max-width: 300px;">
          <img src="${log.image}" crossorigin="anonymous" style="width: 100%; border-radius: 8px; border: 1px solid #cbd5e1;" />
        </div>
        <div style="flex: 2; padding: 20px; border-radius: 10px; border: 2px solid transparent; text-align: ${isArabicLang ? 'right' : 'left'}; ${verdictStyle}" dir="${isArabicLang ? 'rtl' : 'ltr'}">
          <h2 style="color: ${verdictTitleColor}; margin-top: 0;">${verdictTitle}</h2>
          <p style="margin: 0; line-height: 1.6;">${verdictDesc}</p>
        </div>
      </div>

      ${facesHtml}
      ${elaHtml}
      ${metadataHtml}

      <!-- Footer -->
      <div style="text-align: center; margin-top: 50px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 0.85rem;" dir="${isArabicLang ? 'rtl' : 'ltr'}">
        ${isArabicLang ? 'تم إنشاء هذا التقرير آلياً بواسطة نظام يقين للأدلة الجنائية الرقمية.' : 'This report was automatically generated by Yaqeen Digital Forensics System.'}
      </div>

    </div>
  `;
};

const downloadLogPDF = (log) => {
  downloadingLogId.value = log.id;
  
  let htmlContent = generatePDFHtml(log, isArabic.value);
  const isAr = isArabic.value;
  
  // Clean up html2canvas LTR hacks so native print uses real RTL correctly
  if (isAr) {
    htmlContent = htmlContent.replace(/dir="ltr"/g, 'dir="rtl"');
    htmlContent = htmlContent.replace(/flex-direction:\s*row-reverse/g, 'flex-direction: row');
  } else {
    htmlContent = htmlContent.replace(/dir="rtl"/g, 'dir="ltr"');
  }
  
  const printHtml = `<!DOCTYPE html>
<html lang="${isAr ? 'ar' : 'en'}" dir="${isAr ? 'rtl' : 'ltr'}">
<head>
  <meta charset="UTF-8">
  <title>Yaqeen_Scan_Report_${log.id}</title>
  <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    @page { size: A4; margin: 15mm; }
    body { 
      font-family: 'Tajawal', sans-serif; 
      margin: 0; 
      padding: 0;
      background: #f8fafc;
      color: #0f172a;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    .report-container {
      width: 100%;
      max-width: 900px;
      margin: 0 auto;
      background: #ffffff;
      padding: 20px;
      box-sizing: border-box;
      border: 1px solid #e2e8f0;
      min-height: 100vh;
    }
    .avoid-break {
      page-break-inside: avoid;
      break-inside: avoid;
    }
    .print-btn-container {
      text-align: center;
      padding: 20px;
      background: #ffffff;
      border-bottom: 1px solid #e2e8f0;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .print-btn {
      padding: 12px 24px;
      background: #0ea5e9;
      color: white;
      border: none;
      border-radius: 8px;
      font-family: 'Tajawal', sans-serif;
      font-size: 1.1rem;
      cursor: pointer;
      font-weight: bold;
      transition: background 0.3s ease;
    }
    .print-btn:hover { background: #0284c7; }
    @media print {
      body { background: #ffffff; }
      .report-container { border: none; padding: 0; box-shadow: none; }
      .no-print { display: none !important; }
    }
  </style>
</head>
<body>
  <div class="no-print print-btn-container">
    <button class="print-btn" onclick="window.print()">${isAr ? 'طباعة / حفظ كـ PDF' : 'Print / Save as PDF'}</button>
  </div>
  <div class="report-container">
    ${htmlContent}
  </div>
  <script>
    window.onload = function() {
      setTimeout(function() {
        window.print();
      }, 500);
    };
  <\/script>
</body>
</html>`;

  const win = window.open('', '_blank', 'width=1000,height=800');
  if (win) {
    win.document.open();
    win.document.write(printHtml);
    win.document.close();
  } else {
    alert(isAr ? 'يرجى السماح بالنوافذ المنبثقة (Pop-ups) لعرض التقرير.' : 'Please allow pop-ups to view the report.');
  }
  
  downloadingLogId.value = null;
}

const copyReportText = (text) => {
  navigator.clipboard.writeText(text).then(() => {
    reportCopied.value = true
    setTimeout(() => { reportCopied.value = false }, 2000)
  })
}

const toggleLanguage = () => {
  isArabic.value = !isArabic.value
}

const toggleTheme = () => {
  isDark.value = !isDark.value
  if (isDark.value) {
    document.body.classList.remove('light-theme')
  } else {
    document.body.classList.add('light-theme')
  }
}

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    uploadedFile.value = file
    buildPreview(file)
  }
}

const handleDrop = (event) => {
  isDragOver.value = false
  const file = event.dataTransfer.files[0]
  if (file) {
    uploadedFile.value = file
    buildPreview(file)
  }
}

const buildPreview = (file) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = e.target.result
    clearPipeline()
  }
  reader.readAsDataURL(file)
}

const removeImage = () => {
  imagePreview.value = null
  uploadedFile.value = null
  analysisResult.value = null
  analysisError.value = null
  clearPipeline()
}

const clearPipeline = () => {
  showTerminal.value = false
  isAnalyzing.value = false
  pipelineStep.value = 0
  analysisResult.value = null
  analysisError.value = null
  activeTab.value = 'ai'
}

const startAnalysisPipeline = async () => {
  if (!uploadedFile.value) return

  isAnalyzing.value = true
  showTerminal.value = true
  pipelineStep.value = 0
  analysisError.value = null
  analysisResult.value = null

  // Start terminal progress logs sequence
  const s1 = setTimeout(() => { pipelineStep.value = 1 }, 800)
  const s2 = setTimeout(() => { pipelineStep.value = 2 }, 1800)
  const s3 = setTimeout(() => { pipelineStep.value = 3 }, 2800)

  const formData = new FormData()
  formData.append('file', uploadedFile.value)
  formData.append('ela_quality', elaQuality.value)

  try {
    const response = await fetch('http://127.0.0.1:5000/api/analyze', {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const errData = await response.json()
      throw new Error(errData.error || 'Server returned error response')
    }

    const data = await response.json()
    
    if (data.success) {
      let isFake = false;
      if (data.faces && data.faces.length > 0) {
        isFake = data.faces.some(f => f.fake_probability > 50);
      }

      // Allow terminal animation to complete or fast-forward
      setTimeout(() => {
        analysisResult.value = data
        isAnalyzing.value = false

        // Save to recent logs here
        recentLogs.value.unshift({
          id: Date.now(),
          image: imagePreview.value,
          timestamp: new Date(),
          result: data,
          isFake: isFake
        });
        if (recentLogs.value.length > 3) {
          recentLogs.value.pop();
        }

        setTimeout(() => {
          const resultsPanel = document.querySelector('.panel-right')
          if (resultsPanel) {
            resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' })
          }
        }, 100)
      }, 3000)
    } else {
      throw new Error(data.error || 'Pipeline execution failed on server')
    }
  } catch (error) {
    console.error('Error during backend analysis request:', error)
    clearTimeout(s1)
    clearTimeout(s2)
    clearTimeout(s3)
    analysisError.value = error.message || 'Could not connect to analysis server.'
    isAnalyzing.value = false
    pipelineStep.value = 0
  }
}
</script>

<style>
/* تصفير الهوامش لضمان ملء كامل الشاشة دون فراغات أو انسحاب جانبى */
html, body {
  margin: 0 !important;
  padding: 0 !important;
  width: 100% !important;
  height: 100% !important;
  background-color: #0B0F19;
  box-sizing: border-box;
  overflow-x: hidden;
  transition: background-color 0.3s ease;
}
body.light-theme {
  background-color: #f8fafc !important;
}
*, *::before, *::after {
  box-sizing: inherit;
}
</style>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;800&family=Tajawal:wght@400;700;900&display=swap');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css');



.app-container {
  background-color: #0B0F19;
  color: #ffffff;
  font-family: 'Sora', 'Tajawal', sans-serif;
  min-height: 100vh;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.3s ease;
}

.app-container.light-theme {
  background-color: #f8fafc;
  color: #0f172a;
}
.light-theme .main-title, .light-theme .new-zone-title, .light-theme .item-text h3, .light-theme .v-text, .light-theme .font-bold {
  color: #0f172a !important;
}
.light-theme .drop-zone {
  background: #ffffff;
  border-color: #cbd5e1;
}
.light-theme .drop-zone:hover, .light-theme .drop-zone.drag-active {
  border-color: #0ea5e9;
  background: #f0f9ff;
  box-shadow: 0 0 30px rgba(14, 165, 233, 0.15), inset 0 0 20px rgba(14, 165, 233, 0.05);
}
.light-theme .upload-icon-circle {
  background: #f8fafc;
  border-color: #e2e8f0;
}
.light-theme .drop-zone:hover .upload-icon-circle, .light-theme .drop-zone.drag-active .upload-icon-circle {
  border-color: #0ea5e9;
  background: #ffffff;
}
.light-theme .format-badge {
  background: #f1f5f9;
  border-color: #e2e8f0;
  color: #475569;
}
.light-theme .terminal-panel {
  background: #ffffff;
  border-color: #cbd5e1;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
.light-theme .terminal-bar {
  background: #f1f5f9;
}
.light-theme .timeline-card {
  background: #ffffff;
  border-color: #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
.light-theme .timeline-card-title {
  color: #0f172a;
}
.light-theme .face-detail-card {
  background: #f8fafc;
}

.content-wrapper {
  width: 100%;
  padding: 0 40px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* الهيدر العلوي */
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 0;
  width: 100%;
}
.brand { display: flex; align-items: center; gap: 10px; }
.brand-icon { color: #38bdf8; font-size: 1.4rem; }
.brand-name { font-weight: 800; font-size: 1.3rem; letter-spacing: -0.5px; }

.nav-menu {
  display: flex; background: rgba(255, 255, 255, 0.02);
  padding: 5px; border-radius: 50px; border: 1px solid rgba(255, 255, 255, 0.05);
}
.menu-item {
  background: transparent; border: none; padding: 10px 18px; border-radius: 50px;
  font-size: 0.8rem; font-weight: 600; cursor: pointer; color: #94a3b8; display: flex; align-items: center; gap: 8px;
}
.menu-item.active { background: rgba(56, 189, 248, 0.1); color: #38bdf8; }

.nav-actions { display: flex; align-items: center; gap: 15px; }
.lang-btn {
  background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08);
  color: #fff; padding: 8px 16px; border-radius: 50px; cursor: pointer; font-size: 0.8rem; font-weight: 600;
}
.avatar-box { width: 38px; height: 38px; border-radius: 50%; border: 1px solid rgba(255, 255, 255, 0.1); overflow: hidden; }
.user-avatar { width: 100%; height: 100%; }

/* مساحة المحتوى المركزيّة */
.main-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 50px;
  width: 100%;
  flex-grow: 1;
  padding: 25px 0;
}

.panel-left { width: 100%; max-width: 850px; }
.panel-right { width: 100%; max-width: 1000px; }

/* دعم الاتجاه العربي بشكل هندسي آمن دون تهجير العناصر */
.rtl-mode .sub-badge { border-left: none; border-right: 3px solid #38bdf8; padding-left: 0; padding-right: 10px; }
.rtl-mode .final-desc-box { border-left: none; border-right: 2px solid #10b981; }

/* التفاصيل الدقيقة */
.sub-badge { color: #38bdf8; font-size: 0.75rem; font-weight: 800; letter-spacing: 1px; border-left: 3px solid #38bdf8; padding-left: 10px; }
.main-title { font-size: 2.8rem; font-weight: 800; line-height: 1.2; margin: 15px 0; letter-spacing: -1px; }
.gradient-text { background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.main-description { color: #64748b; font-size: 0.95rem; line-height: 1.6; margin-bottom: 25px; }

/* منطقة الرفع السفليّة */
.upload-section { display: flex; flex-direction: column; gap: 15px; margin-top: 20px; }
.drop-zone {
  width: 100%; height: 350px; max-width: 850px; margin: 0 auto;
  background: rgba(15, 23, 42, 0.6);
  border: 2px dashed rgba(255, 255, 255, 0.05); border-radius: 16px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; transition: all 0.3s;
}
.drop-zone:hover, .drop-zone.drag-active { 
  border-color: #22d3ee; 
  background: rgba(15, 23, 42, 0.8);
  box-shadow: 0 0 30px rgba(34, 211, 238, 0.15), inset 0 0 20px rgba(34, 211, 238, 0.05);
}

.zone-prompt { 
  display: flex; flex-direction: column; align-items: center; gap: 12px;
}
.upload-icon-circle {
  width: 80px; height: 80px; border-radius: 50%; background: #0B0F19;
  display: flex; align-items: center; justify-content: center; margin-bottom: 10px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: all 0.3s;
}

.drop-zone:hover .upload-icon-circle, .drop-zone.drag-active .upload-icon-circle {
  border-color: #22d3ee;
  box-shadow: 0 0 15px rgba(34, 211, 238, 0.2);
}

.new-upload-icon { width: 36px; height: 36px; color: #94a3b8; transition: color 0.3s; }
.drop-zone:hover .new-upload-icon, .drop-zone.drag-active .new-upload-icon { color: #22d3ee; }

.new-zone-title { margin: 0; font-size: 1.4rem; color: #ffffff; font-weight: 700; }
.new-zone-subtitle { margin: 0; font-size: 0.95rem; color: #64748b; margin-top: 5px; }

.supported-formats {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}
.format-badge {
  background: rgba(11, 15, 25, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.05);
  color: #94a3b8;
  padding: 6px 16px;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.zone-preview { width: 100%; height: 100%; position: relative; display: flex; justify-content: center; align-items: center; }
.img-thumb { height: 85%; max-width: 80%; object-fit: contain; border-radius: 8px; }
.img-controls { position: absolute; top: 8px; right: 8px; }
.clear-btn { background: rgba(239, 68, 68, 0.9); border: none; color: #fff; padding: 5px 10px; border-radius: 6px; cursor: pointer; font-size: 0.75rem; font-weight: bold; }

.execute-btn {
  width: 100%; background: #3b82f6; color: white; border: none; padding: 14px; border-radius: 10px;
  font-size: 0.95rem; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}
.execute-btn:disabled { background: #1e293b; color: #64748b; cursor: not-allowed; box-shadow: none; }

/* شاشة الترمنال المحاكية للخطوات */
.terminal-panel { margin-top: 20px; background: #060b19; border: 1px solid rgba(56, 189, 248, 0.15); border-radius: 10px; overflow: hidden; }
.terminal-bar { background: #0c1429; padding: 8px 12px; display: flex; align-items: center; justify-content: space-between; }
.window-dots { display: flex; gap: 5px; }
.window-dots span { width: 8px; height: 8px; border-radius: 50%; }
.d-red { background: #ef4444; } .d-yellow { background: #f59e0b; } .d-green { background: #10b981; }
.bar-title { font-family: monospace; font-size: 0.7rem; color: #64748b; }
.terminal-logs { padding: 15px; font-family: monospace; font-size: 0.8rem; display: flex; flex-direction: column; gap: 10px; }

.log-row { opacity: 0; display: none; transform: translateY(3px); transition: all 0.4s ease; }
.log-row.active-row { opacity: 1; display: block; }
.tag-success { color: #10b981; font-weight: bold; margin: 0 5px; }
.tag-info { color: #38bdf8; font-weight: bold; margin: 0 5px; }
.font-bold { color: #fff; }
.final-desc-box { margin-top: 5px; color: #a7f3d0; background: rgba(16, 185, 129, 0.04); padding: 8px; border-radius: 6px; border-left: 2px solid #10b981; line-height: 1.4; }

/* Logs Modal Styles */
.logs-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(4, 6, 14, 0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999999;
  padding: 20px;
}
.logs-modal-content {
  background: #0B0F19;
  border: 1px solid rgba(34, 211, 238, 0.2);
  border-radius: 16px;
  width: 100%;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  padding: 24px;
}
.logs-modal-content.light-theme {
  background: #ffffff;
  border-color: #cbd5e1;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 16px;
}
.light-theme .modal-header { border-color: #e2e8f0; }
.modal-header h2 {
  font-size: 1.4rem;
  font-weight: 700;
  margin: 0;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 10px;
}
.logs-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.log-list-item {
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  display: flex;
  align-items: center;
  padding: 12px;
  gap: 20px;
  transition: all 0.3s ease;
}
.light-theme .log-list-item {
  background: #f8fafc;
  border-color: #e2e8f0;
}
.log-list-item:hover {
  background: rgba(15, 23, 42, 0.8);
  border-color: rgba(34, 211, 238, 0.3);
  transform: translateX(-4px);
}
.rtl-mode .log-list-item:hover {
  transform: translateX(4px);
}
.log-item-image {
  width: 100px;
  height: 80px;
  border-radius: 8px;
  overflow: hidden;
  background: #000;
  flex-shrink: 0;
}
.log-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.log-item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.log-time-date {
  display: flex;
  gap: 12px;
  font-size: 0.85rem;
  color: #94a3b8;
}
.light-theme .log-time-date { color: #64748b; }
.log-result-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 50px;
  width: fit-content;
}
.badge-fake {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.2);
}
.badge-real {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.2);
}
.result-icon { width: 16px; height: 16px; }

.log-item-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}
.log-action-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #e2e8f0;
  border-radius: 8px;
  padding: 8px 16px;
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
}
.light-theme .log-action-btn { background: #fff; border-color: #cbd5e1; color: #475569; }
.log-action-btn:hover {
  background: rgba(34, 211, 238, 0.1);
  color: #22d3ee;
  border-color: rgba(34, 211, 238, 0.3);
}
.light-theme .log-action-btn:hover { background: #f0f9ff; color: #0ea5e9; border-color: #bae6fd; }
.action-icon { width: 18px; height: 18px; }

.header-icon { width: 24px; height: 24px; color: #22d3ee; }
.light-theme .header-icon { color: #0ea5e9; }
.close-icon { width: 20px; height: 20px; }
.empty-icon { width: 64px; height: 64px; margin-bottom: 15px; opacity: 0.5; }


/* بطاقات المخطط بالجانب الآخر */
.steps-stack { display: flex; flex-direction: column; gap: 15px; width: 100%; }
.step-item { display: flex; gap: 15px; background: rgba(255, 255, 255, 0.005); border: 1px solid rgba(255, 255, 255, 0.02); padding: 15px; border-radius: 12px; align-items: center; transition: all 0.3s; }
.item-focused { background: linear-gradient(135deg, rgba(56, 189, 248, 0.05), rgba(129, 140, 248, 0.05)); border-color: rgba(56, 189, 248, 0.2); }
.item-number { font-size: 1.4rem; font-weight: 900; color: rgba(56, 189, 248, 0.25); }
.item-text h3 { margin: 0 0 2px 0; font-size: 0.95rem; color: #fff; }
.item-text p { margin: 0; color: #64748b; font-size: 0.8rem; line-height: 1.4; }

/* الفوتر */
.footer { display: flex; align-items: center; gap: 35px; padding: 20px 0; border-top: 1px solid rgba(255, 255, 255, 0.03); justify-content: center; width: 100%; }
.stat-block { display: flex; flex-direction: column; align-items: center; }
.v-text { font-size: 1.3rem; font-weight: 800; color: #fff; }
.l-text { color: #64748b; font-size: 0.75rem; margin-top: 3px; }
.divider { width: 1px; height: 25px; background: rgba(255, 255, 255, 0.05); }

/* Responsive Design - دعم كامل لشاشات الجوال واللابتوب */
@media (max-width: 1024px) {
  .content-wrapper { padding: 0 25px; }
  .main-content { flex-direction: column !important; gap: 40px; }
  .panel-left, .panel-right { width: 100% !important; }
  .navbar { flex-wrap: wrap; gap: 15px; }
  .nav-menu { order: 3; width: 100%; justify-content: center; margin-top: 10px; }
  .footer { flex-wrap: wrap; gap: 20px; }
}

@media (max-width: 600px) {
  .content-wrapper { padding: 0 15px; }
  .main-title { font-size: 2rem; }
  .brand-name { display: none; } /* إخفاء النص لتقليل المساحة وإبقاء الأيقونة */
  .menu-item { padding: 8px 12px; font-size: 0.75rem; }
  .menu-item span { display: none; } /* عرض الأيقونات فقط في الجوال */
}

/* Timeline Styles */
.timeline {
  position: relative;
  padding-left: 32px;
  border-left: 2px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 25px;
}
.rtl-mode .timeline {
  padding-left: 0;
  padding-right: 32px;
  border-left: none;
  border-right: 2px solid rgba(255, 255, 255, 0.05);
}

.timeline-item {
  position: relative;
  width: 100%;
}

.timeline-badge {
  position: absolute;
  top: 12px;
  left: -43px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  color: #030612;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
  z-index: 2;
}
.rtl-mode .timeline-badge {
  left: auto;
  right: -43px;
}

.timeline-card {
  background: rgba(255, 255, 255, 0.01);
  border: 1px solid rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  padding: 18px;
  transition: all 0.3s ease;
  border-left: 3px solid var(--card-border-color, #38bdf8);
}
.rtl-mode .timeline-card {
  border-left: 1px solid rgba(255, 255, 255, 0.02);
  border-right: 3px solid var(--card-border-color, #38bdf8);
}
.timeline-card:hover {
  background: rgba(255, 255, 255, 0.02);
  border-color: rgba(255, 255, 255, 0.05);
}

.timeline-card-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 12px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.timeline-card-title i {
  font-size: 1.1rem;
}

.timeline-card-text {
  font-size: 0.85rem;
  color: #94a3b8;
}

/* Faces Extracted List & Grad-CAM Cards */
.faces-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 10px;
}

.face-detail-card {
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.face-detail-card:hover {
  background: rgba(255, 255, 255, 0.025);
  border-color: rgba(255, 255, 255, 0.08);
}

.face-header-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  padding-bottom: 8px;
}

.face-images-row {
  display: flex;
  gap: 12px;
  width: 100%;
}

.face-image-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
}

.face-box-title {
  font-size: 0.72rem;
  color: #64748b;
  font-weight: 700;
  text-transform: uppercase;
}

.gradcam-title {
  color: #38bdf8 !important;
  display: flex;
  align-items: center;
  gap: 4px;
}

.face-img-render {
  width: 100%;
  max-width: 180px;
  height: 140px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.03);
  background: #060b19;
  transition: transform 0.2s;
}
.face-img-render:hover {
  transform: scale(1.03);
}

.face-avatar-label {
  font-size: 0.82rem;
  color: #ffffff;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
}
.face-avatar-label i {
  color: #38bdf8;
}

.no-faces-message {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ef4444;
  font-weight: 600;
  font-size: 0.85rem;
}

/* Metadata Grid styling */
.metadata-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.metadata-cell {
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 0.7rem;
  color: #64748b;
  text-transform: uppercase;
  font-weight: 600;
}

.meta-value {
  font-size: 0.85rem;
  color: #ffffff;
  font-weight: 700;
}

/* Verdict Styles */
.verdict-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.verdict-score-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.02);
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.verdict-score-label {
  font-size: 0.8rem;
  color: #94a3b8;
  font-weight: 600;
}

.verdict-score-value {
  font-size: 1.1rem;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.verdict-paragraph {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.5;
  color: #cbd5e1;
}

.verdict-actions {
  display: flex;
  margin-top: 5px;
}

.verdict-btn {
  background: transparent;
  border: 1px solid;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s;
  width: 100%;
}
.verdict-btn:hover {
  background: rgba(255, 255, 255, 0.03);
}

/* Error alert styling */
.error-alert {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 10px;
  padding: 12px 15px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: #fca5a5;
  margin-top: 15px;
}

.error-alert i {
  color: #ef4444;
  font-size: 1rem;
  margin-top: 2px;
}

.error-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.8rem;
}

/* Helper text colors */
.text-blue { color: #38bdf8; }
.text-indigo { color: #818cf8; }
.text-green { color: #10b981; }
.text-red { color: #ef4444; }

/* Face classification badges */
.face-result-badge {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
  margin-top: 4px;
  text-align: center;
}
.bg-red {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.3);
}
.bg-green {
  background: rgba(16, 185, 129, 0.15);
  color: #a7f3d0;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

/* Warning alert styling */
.warning-alert {
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 10px;
  padding: 12px 15px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: #fde047;
  margin-top: 5px;
  margin-bottom: 15px;
  text-align: right;
}

.rtl-mode .warning-alert {
  text-align: right;
}

.warning-alert i {
  color: #f59e0b;
  font-size: 1.1rem;
  margin-top: 2px;
}

.warning-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.8rem;
  line-height: 1.4;
}

/* ELA Forensic Styling additions */
.ela-quality-container {
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 12px;
  padding: 15px;
  margin-top: 10px;
  margin-bottom: 5px;
  text-align: right;
}
.rtl-mode .ela-quality-container {
  text-align: right;
}
.ela-quality-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.ela-quality-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: #cbd5e1;
  display: flex;
  align-items: center;
  gap: 8px;
}
.ela-quality-label i {
  color: #38bdf8;
}
.ela-quality-value {
  font-size: 0.9rem;
  font-weight: 800;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.1);
  padding: 2px 8px;
  border-radius: 6px;
}
.ela-quality-slider {
  width: 100%;
  height: 5px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 5px;
  outline: none;
  -webkit-appearance: none;
  cursor: pointer;
}
.ela-quality-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: #38bdf8;
  cursor: pointer;
  transition: transform 0.1s;
}
.ela-quality-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}
.ela-quality-info {
  font-size: 0.7rem;
  color: #64748b;
  margin-top: 6px;
  line-height: 1.3;
}

/* Tabs Navigation */
.result-tabs {
  display: flex;
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid rgba(255, 255, 255, 0.03);
  padding: 4px;
  border-radius: 10px;
  margin-bottom: 20px;
  gap: 5px;
  width: 100%;
}
.tab-btn {
  flex: 1;
  background: transparent;
  border: none;
  padding: 10px;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.3s;
}
.tab-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.02);
}
.tab-btn.active {
  background: rgba(56, 189, 248, 0.08);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.12);
}

/* ELA Content Styling */
.ela-details-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  animation: fadeIn 0.3s ease;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}

.ela-verdict-card {
  display: flex;
  gap: 15px;
  padding: 16px;
  border-radius: 12px;
  align-items: flex-start;
  text-align: right;
  width: 100%;
}
.rtl-mode .ela-verdict-card {
  text-align: right;
}
.ela-clean {
  background: rgba(16, 185, 129, 0.04);
  border: 1px solid rgba(16, 185, 129, 0.15);
  border-left: 3px solid #10b981;
}
.rtl-mode .ela-clean {
  border-left: 1px solid rgba(16, 185, 129, 0.15);
  border-right: 3px solid #10b981;
}
.ela-suspicious {
  background: rgba(245, 158, 11, 0.04);
  border: 1px solid rgba(245, 158, 11, 0.15);
  border-left: 3px solid #f59e0b;
}
.rtl-mode .ela-suspicious {
  border-left: 1px solid rgba(245, 158, 11, 0.15);
  border-right: 3px solid #f59e0b;
}
.ela-tampered {
  background: rgba(239, 68, 68, 0.04);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-left: 3px solid #ef4444;
}
.rtl-mode .ela-tampered {
  border-left: 1px solid rgba(239, 68, 68, 0.15);
  border-right: 3px solid #ef4444;
}

.ela-verdict-icon {
  font-size: 1.4rem;
  margin-top: 2px;
}
.ela-clean .ela-verdict-icon { color: #10b981; }
.ela-suspicious .ela-verdict-icon { color: #f59e0b; }
.ela-tampered .ela-verdict-icon { color: #ef4444; }

.ela-verdict-title {
  margin: 0 0 4px 0;
  font-size: 0.95rem;
  font-weight: 800;
  color: #ffffff;
}
.ela-verdict-desc {
  margin: 0;
  font-size: 0.8rem;
  color: #94a3b8;
  line-height: 1.4;
}

.ela-stats-box, .ela-visuals-box {
  background: rgba(255, 255, 255, 0.005);
  border: 1px solid rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  padding: 16px;
  text-align: right;
  width: 100%;
}
.rtl-mode .ela-stats-box, .rtl-mode .ela-visuals-box {
  text-align: right;
}
.section-title {
  margin: 0 0 15px 0;
  font-size: 0.85rem;
  color: #fff;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  padding-bottom: 8px;
}
.section-title i {
  color: #38bdf8;
}

.metric-progress-item {
  margin-bottom: 14px;
}
.metric-progress-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #94a3b8;
  margin-bottom: 6px;
}
.metric-val {
  font-weight: 700;
}
.progress-bar-bg {
  height: 6px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  border-radius: 10px;
  transition: width 0.5s ease;
}
.overall-suspect {
  border-top: 1px dashed rgba(255, 255, 255, 0.05);
  padding-top: 12px;
  margin-top: 15px;
  margin-bottom: 0;
}
.overall-suspect .metric-progress-header {
  font-size: 0.85rem;
}
.suspect-pct {
  font-size: 1.1rem;
}

.ela-warning-alert {
  background: rgba(245, 158, 11, 0.06);
  border: 1px solid rgba(245, 158, 11, 0.2);
  border-radius: 10px;
  padding: 12px 15px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: #fde047;
  text-align: right;
  width: 100%;
}
.rtl-mode .ela-warning-alert {
  text-align: right;
}
.ela-warning-alert i {
  color: #f59e0b;
  font-size: 1.1rem;
  margin-top: 2px;
}
.ela-warning-content {
  font-size: 0.78rem;
  line-height: 1.4;
}

.ela-images-comparison {
  display: flex;
  gap: 12px;
}
.comparison-panel-img {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
}
.panel-label {
  position: absolute;
  top: 8px;
  left: 8px;
  background: rgba(3, 6, 18, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 700;
  color: #fff;
  z-index: 5;
}
.rtl-mode .panel-label {
  left: auto;
  right: 8px;
}
.ELA-label {
  border-color: rgba(56, 189, 248, 0.25);
  color: #38bdf8;
}
.comp-img {
  width: 100%;
  height: auto;
  max-height: 250px;
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.03);
  background: #030612;
}

.no-face-error-card {
  background: rgba(239, 68, 68, 0.05);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  color: #f87171;
  margin: 20px 0;
}
.no-face-error-card i {
  font-size: 3rem;
  margin-bottom: 15px;
}
.no-face-error-card h3 {
  margin: 0 0 10px 0;
  color: #fff;
}
.no-face-error-card p {
  color: #94a3b8;
  font-size: 0.9rem;
  line-height: 1.5;
  margin: 0;
}

.ela-report-box {
  background: #060b19;
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  overflow: hidden;
  text-align: left;
  width: 100%;
}
.ela-report-header {
  background: #0c1429;
  padding: 8px 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.72rem;
  color: #64748b;
  font-family: monospace;
}
.ela-report-content {
  margin: 0;
  padding: 12px 15px;
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  color: #c9d1d9;
  background: #060b19;
  overflow-x: auto;
  white-space: pre-wrap;
  line-height: 1.4;
  max-height: 250px;
  overflow-y: auto;
  text-align: left;
  direction: ltr !important;
}
.copy-report-btn {
  background: transparent;
  border: none;
  color: #64748b;
  cursor: pointer;
  font-size: 0.85rem;
  padding: 2px 6px;
  display: flex;
  align-items: center;
  gap: 4px;
  position: relative;
  transition: color 0.2s;
}
.copy-report-btn:hover {
  color: #38bdf8;
}
.copy-tooltip {
  font-size: 0.65rem;
  color: #10b981;
  font-weight: bold;
}
.warning-txt {
  color: #ef4444;
}
.info-txt {
  color: #38bdf8;
}

/* Metadata Tab Content Styling */
.metadata-details-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  animation: fadeIn 0.3s ease;
  width: 100%;
}
.metadata-grid-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}
.metadata-section-card {
  background: rgba(255, 255, 255, 0.005);
  border: 1px solid rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  padding: 16px;
  text-align: right;
  width: 100%;
}
.rtl-mode .metadata-section-card {
  text-align: right;
}
.details-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.details-row-cell {
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.cell-label {
  font-size: 0.7rem;
  color: #64748b;
  font-weight: 600;
}
.cell-val {
  font-size: 0.85rem;
  color: #ffffff;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* GPS Location Styling */
.gps-data-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.maps-redirect-banner {
  background: rgba(56, 189, 248, 0.04);
  border: 1px solid rgba(56, 189, 248, 0.15);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 5px;
}
.maps-redirect-banner i {
  font-size: 1.5rem;
  color: #38bdf8;
}
.banner-text {
  flex-grow: 1;
  text-align: right;
}
.rtl-mode .banner-text {
  text-align: right;
}
.banner-text strong {
  font-size: 0.82rem;
  color: #ffffff;
}
.banner-text p {
  margin: 3px 0 0 0;
  font-size: 0.72rem;
  color: #94a3b8;
}
.maps-btn {
  background: #38bdf8;
  color: #030612;
  text-decoration: none;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: opacity 0.2s;
}
.maps-btn:hover {
  opacity: 0.9;
}
.gps-unavailable-block {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #64748b;
  font-size: 0.8rem;
  padding: 10px;
  background: rgba(255, 255, 255, 0.005);
  border: 1px dashed rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  justify-content: center;
}
.gps-unavailable-block i {
  font-size: 1rem;
}
.metadata-error-card {
  background: rgba(255, 255, 255, 0.005);
  border: 1px dashed rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  color: #64748b;
  font-size: 0.8rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.metadata-error-card i {
  font-size: 1.5rem;
}
.face-result-bars-container {
  display: flex;
  flex-direction: column;
  gap: 15px;
  width: 100%;
}
.face-result-bar {
  background: #191415;
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.face-result-bar.is-real {
  background: #141916;
  border: 1px solid rgba(16, 185, 129, 0.2);
}
.bar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.bar-verdict {
  font-weight: 800;
  font-size: 1.1rem;
  letter-spacing: 1px;
}
.bar-face-label {
  color: #ffffff;
  font-weight: 700;
  font-size: 1rem;
}
.bar-track {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 1s ease-in-out;
}
.bar-footer {
  display: flex;
  justify-content: flex-end;
}
.bar-percentage {
  color: #8b949e;
  font-size: 0.85rem;
}
.text-red { color: #ef4444; }
.text-green { color: #10b981; }
.bg-red { background-color: #ef4444; }
.bg-green { background-color: #10b981; }
</style>