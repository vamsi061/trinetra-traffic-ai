"""Generate the TRINETRA AI presentation with all new features, comparisons, violation types, and image showcases."""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
import os

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

RED = RGBColor(0xC0, 0x39, 0x2B)
DARK = RGBColor(0x0D, 0x12, 0x25)
DARK2 = RGBColor(0x1A, 0x20, 0x40)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x9C, 0xA3, 0xAF)
BLUE = RGBColor(0x3B, 0x82, 0xF6)
GREEN = RGBColor(0x34, 0xD3, 0x99)
AMBER = RGBColor(0xF5, 0x9E, 0x0B)
PURPLE = RGBColor(0xA7, 0x8B, 0xFA)
ORANGE = RGBColor(0xF9, 0x73, 0x16)
YELLOW = RGBColor(0xE8, 0xC5, 0x47)

# ─── Helpers ───

def add_bg(slide, color=DARK):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_rect(slide, left, top, width, height, color):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape

def add_rounded_rect(slide, left, top, width, height, color, border=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    if border:
        shape.line.color.rgb = border
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape

def add_text_box(slide, left, top, width, height, text, font_size=18, bold=False, color=WHITE, align=PP_ALIGN.LEFT):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.alignment = align
    return txBox

def add_multi_text(slide, left, top, width, height, lines, font_size=14, color=MUTED):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.space_after = Pt(4)
    return txBox

def add_image_safe(slide, path, left, top, width, height=None):
    if os.path.exists(path):
        if height:
            slide.shapes.add_picture(path, left, top, width, height)
        else:
            slide.shapes.add_picture(path, left, top, width)
        return True
    return False

def add_decorated_title(slide, title, subtitle=None):
    add_rect(slide, Inches(0), Inches(0), Inches(0.15), Inches(7.5), RED)
    add_rect(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.04), RED)
    add_text_box(slide, Inches(1.0), Inches(1.2), Inches(11), Inches(0.8), title, font_size=36, bold=True, color=WHITE)
    if subtitle:
        add_text_box(slide, Inches(1.0), Inches(2.0), Inches(11), Inches(0.5), subtitle, font_size=18, color=MUTED)

def add_callout(slide, x, y, text, color=RED):
    shape = add_rounded_rect(slide, x, y, Inches(1.8), Inches(0.3), DARK2, color)
    tf = shape.text_frame
    tf.paragraphs[0].text = text
    tf.paragraphs[0].font.size = Pt(9)
    tf.paragraphs[0].font.color.rgb = color
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    return shape

SAMPLE_DIR = '/tmp/opencode/trinetra-ai-v2/backend/tests/samples'
EVIDENCE_DIR = '/tmp/opencode/trinetra-ai-v2/data/evidence'

def find_evidence(source_name):
    """Find most recent evidence file for a given source image."""
    if not os.path.isdir(EVIDENCE_DIR):
        return None
    base = os.path.splitext(source_name)[0]
    candidates = [f for f in os.listdir(EVIDENCE_DIR) if f.startswith(base)]
    if candidates:
        return os.path.join(EVIDENCE_DIR, sorted(candidates)[-1])
    return None

# ═══════════════════════════════════════════════════════════════
# SLIDE 1: Title
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_text_box(slide, Inches(1.0), Inches(1.5), Inches(11), Inches(1.2), 'TRINETRA AI', font_size=56, bold=True, color=RED)
add_text_box(slide, Inches(1.0), Inches(2.8), Inches(11), Inches(0.8), 'Transforming Traffic Images into Actionable Enforcement Intelligence', font_size=26, color=WHITE)
add_rect(slide, Inches(1.0), Inches(3.8), Inches(3), Inches(0.06), RED)
add_text_box(slide, Inches(1.0), Inches(4.2), Inches(11), Inches(0.5), 'AI-Powered Traffic Enforcement Intelligence Platform', font_size=18, color=MUTED)
add_text_box(slide, Inches(1.0), Inches(5.0), Inches(11), Inches(0.5), 'Bengaluru Traffic Police  |  v3.0.0', font_size=15, color=MUTED)
add_rect(slide, Inches(10), Inches(6.5), Inches(3), Inches(0.04), RED)

# ═══════════════════════════════════════════════════════════════
# SLIDE 2: The Problem
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'The Problem')
lines = [
    'Bengaluru — millions of daily commuters, complex urban road network',
    'Traffic personnel manually inspect thousands of CCTV images and video feeds',
    'Violations must be identified, assessed, and prioritized — manually',
    'This process is: time-consuming, resource-intensive, difficult to scale',
    'Manual monitoring alone cannot provide smart-city responsiveness',
    'As traffic volume grows, the gap between capacity and demand widens',
]
add_multi_text(slide, Inches(1.0), Inches(2.4), Inches(11), Inches(4.0), lines, font_size=16)

# ═══════════════════════════════════════════════════════════════
# SLIDE 3: Our Vision
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'Our Vision')
add_text_box(slide, Inches(1.0), Inches(2.4), Inches(11), Inches(0.8),
    'What if every traffic image could become an actionable intelligence report?', font_size=24, color=WHITE)
lines = [
    'Instead of merely detecting vehicles, we envisioned a system capable of:',
    '  ',
    '  - Understanding traffic scenes and identifying potential risks',
    '  - Generating annotated evidence with confidence scores',
    '  - Prioritizing cases by severity and repeat-offender history',
    '  - Supporting informed officer decisions with explainable AI',
    '  ',
    'This vision led to TRINETRA AI — built specifically for Bengaluru Traffic Police.',
]
add_multi_text(slide, Inches(1.0), Inches(3.4), Inches(11), Inches(3.5), lines, font_size=16)

# ═══════════════════════════════════════════════════════════════
# SLIDE 4: What is TRINETRA AI
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'What is TRINETRA AI?', 'An AI-powered Traffic Enforcement Intelligence Platform')
caps = [
    ('Computer Vision', 'YOLOv8s + OwlViT: vehicle, motorcycle, person, bus, truck, auto-rickshaw detection'),
    ('Explainable AI', 'Every detection: confidence, reliability, reason, recommendation'),
    ('Risk Assessment', 'Severity scoring, officer priority, repeat-offender multipliers'),
    ('Evidence Generation', 'Annotated images + downloadable PDF evidence packages'),
    ('Human Review', '3-stage: auto-confirmed / review recommended / manual verification'),
    ('Traffic Intelligence', 'Hotspots, repeat offenders, trends, forecasts, watchlist'),
]
for i, (title, desc) in enumerate(caps):
    row = i // 2; col = i % 2
    x = Inches(0.8) + col * Inches(6.2)
    y = Inches(2.4) + row * Inches(1.5)
    add_rounded_rect(slide, x, y, Inches(5.8), Inches(1.3), DARK2, RED)
    add_text_box(slide, x + Inches(0.2), y + Inches(0.1), Inches(5.4), Inches(0.4), title, font_size=16, bold=True, color=WHITE)
    add_text_box(slide, x + Inches(0.2), y + Inches(0.5), Inches(5.4), Inches(0.7), desc, font_size=12, color=MUTED)

# ═══════════════════════════════════════════════════════════════
# SLIDE 5: Processing Pipeline
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'How It Works — Processing Pipeline')
steps = [
    ('01', 'Traffic Camera', 'Image Capture'),
    ('02', 'Image Quality', 'Assessment'),
    ('03', 'Detection Engine', 'YOLO / OwlViT / Gradio'),
    ('04', 'Violation Checks', '7 Violation Types Scanned'),
    ('05', 'OCR Engine', 'License Plate Recognition'),
    ('06', 'Evidence Generator', 'Images + PDF Report'),
    ('07', 'Risk Assessment', 'Severity + Priority'),
    ('08', 'Human Review', '3-Stage Workflow'),
    ('09', 'Intel Center', 'Dashboard & Analytics'),
    ('10', 'Officer Action', 'Decision Support'),
]
for i, (num, title, sub) in enumerate(steps):
    row = i // 2; col = i % 2
    x = Inches(0.6) + col * Inches(6.3)
    y = Inches(2.2) + row * Inches(0.95)
    add_rounded_rect(slide, x, y, Inches(5.9), Inches(0.75), DARK2, RED)
    add_text_box(slide, x + Inches(0.15), y + Inches(0.12), Inches(0.5), Inches(0.4), num, font_size=16, bold=True, color=RED)
    add_text_box(slide, x + Inches(0.6), y + Inches(0.05), Inches(3.0), Inches(0.35), title, font_size=14, bold=True, color=WHITE)
    add_text_box(slide, x + Inches(0.6), y + Inches(0.4), Inches(3.0), Inches(0.3), sub, font_size=11, color=MUTED)

# ═══════════════════════════════════════════════════════════════
# SLIDE 6: Detection Engine Architecture
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'Detection Engine — 4-Tier Architecture', 'Multiple engines, automatic fallback, user-selectable')
engines_data = [
    ('1. YOLOv8 (COCO)', 'Built-in', 'Fast, always available', 'Car, motorcycle, person, bus, truck\nLimited to 80 COCO classes', GREEN),
    ('2. OwlViT HF API', 'Serverless cloud', 'Needs HF token', 'Any object by name (zero-shot)\nNo GPU needed, fast API calls', BLUE),
    ('3. OwlViT Local', 'On-device', 'Needs PyTorch + model download', 'Offline zero-shot detection\nGPU acceleration supported', PURPLE),
    ('4. Gradio Spaces', 'Cloud GPU', 'NVIDIA HF space', 'Zero-shot via cloud GPU\nMay fail if GPU quota exceeded', AMBER),
]
for i, (name, deploy, req, desc, accent) in enumerate(engines_data):
    y = Inches(2.1) + i * Inches(1.25)
    add_rounded_rect(slide, Inches(0.8), y, Inches(5.5), Inches(1.1), DARK2, accent)
    add_text_box(slide, Inches(1.0), y + Inches(0.05), Inches(5.0), Inches(0.35), name, font_size=15, bold=True, color=accent)
    add_text_box(slide, Inches(1.0), y + Inches(0.4), Inches(5.0), Inches(0.3), f'Deployment: {deploy}  |  {req}', font_size=11, color=MUTED)
    add_text_box(slide, Inches(1.0), y + Inches(0.7), Inches(5.0), Inches(0.3), desc.replace('\n', '  |  '), font_size=10, color=MUTED)
    # Status badge
    status = '✓ Always Ready' if i == 0 else ('✓ Configurable' if i < 3 else '⚠️ Best Effort')
    add_rounded_rect(slide, Inches(6.8), y + Inches(0.2), Inches(2.2), Inches(0.45), DARK2, accent)
    add_text_box(slide, Inches(6.8), y + Inches(0.25), Inches(2.2), Inches(0.35), status, font_size=10, bold=True, color=accent, align=PP_ALIGN.CENTER)
    # Arrow showing fallback order
    if i < 3:
        arr = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(8.0), y + Inches(1.05), Inches(0.35), Inches(0.2))
        arr.fill.solid(); arr.fill.fore_color.rgb = MUTED; arr.line.fill.background()

# ═══════════════════════════════════════════════════════════════
# SLIDE 7: Engine Configuration (UI Screenshot Placeholder)
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'Engine Configuration — Sidebar Modal', 'Configure engines, set tokens, download models — all from the UI')
items = [
    'HF Token: Set your HuggingFace API token for OwlViT zero-shot detection',
    'OwlViT Download: One-click model download (~380MB), auto GPU/CPU detection',
    'Engine Status Panel: Live indicators for all 4 engines (Ready / Not Ready + reasons)',
    'Persistent Configuration: Token stored server-side, automatically applied to all requests',
]
for i, item in enumerate(items):
    y = Inches(2.3) + i * Inches(0.85)
    add_rounded_rect(slide, Inches(0.8), y, Inches(11.5), Inches(0.7), DARK2, RED)
    add_text_box(slide, Inches(1.0), y + Inches(0.1), Inches(11.2), Inches(0.5), f'  {i+1}.  {item}', font_size=14, color=WHITE)

# Add image placeholder boxes with descriptive instructions
add_rounded_rect(slide, Inches(0.8), Inches(5.8), Inches(5.5), Inches(1.3), DARK2, MUTED)
add_text_box(slide, Inches(1.0), Inches(5.9), Inches(5.0), Inches(1.1),
    'CAPTURE: Engine Configuration Modal\n'
    '1. Open TRINETRA AI in browser\n'
    '2. Click "Engine Configuration" button in sidebar\n'
    '3. Screenshot the modal showing 4 engine cards',
    font_size=10, color=MUTED)
add_rounded_rect(slide, Inches(6.8), Inches(5.8), Inches(5.7), Inches(1.3), DARK2, MUTED)
add_text_box(slide, Inches(7.0), Inches(5.9), Inches(5.2), Inches(1.1),
    'CAPTURE: Upload Page Engine Selector\n'
    '1. Navigate to Upload & Analyze page\n'
    '2. Note the Detection Engine card shows active engine\n'
    '3. Screenshot the engine card with badge',
    font_size=10, color=MUTED)

# ═══════════════════════════════════════════════════════════════
# SLIDE 8: Engine Comparison Table
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'Detection Engine Comparison', 'Choose the right engine for your scenario')
cols_x = [Inches(0.6), Inches(3.3), Inches(5.6), Inches(7.9), Inches(10.2)]
col_w = [Inches(2.5), Inches(2.1), Inches(2.1), Inches(2.1), Inches(2.1)]
headers = ['Capability', 'YOLOv8', 'HF API', 'OwlViT Local', 'Gradio']
for j, h in enumerate(headers):
    add_rounded_rect(slide, cols_x[j], Inches(2.0), col_w[j] - Inches(0.04), Inches(0.45), DARK2, RED)
    add_text_box(slide, cols_x[j] + Inches(0.05), Inches(2.05), col_w[j] - Inches(0.1), Inches(0.35), h, font_size=11, bold=(j==0), color=RED if j==0 else WHITE, align=PP_ALIGN.CENTER)

rows = [
    ('Zero-shot', 'Limited (80 classes)', 'Any object', 'Any object', 'Any object'),
    ('Speed', '<1s', '3-10s', '5-15s', '30-60s'),
    ('Internet', 'No', 'Yes', 'No (after download)', 'Yes'),
    ('GPU Required', 'Optional', 'No (serverless)', 'Optional', 'Yes (cloud)'),
    ('Setup', 'None', 'HF token', '380MB download', 'None'),
    ('Auto-Rickshaw', 'Misclass as car', 'Yes', 'Yes', 'Yes'),
    ('License Plate', 'No', 'Yes (via prompt)', 'Yes', 'Yes'),
    ('Helmet', 'Yes', 'Yes', 'Yes', 'Yes'),
    ('Reliability', 'Very High', 'High', 'Moderate', 'Low'),
]
accent_col = [GREEN, BLUE, PURPLE, AMBER]
for i, row_data in enumerate(rows):
    y = Inches(2.5) + i * Inches(0.45)
    bg = DARK if i % 2 == 0 else DARK2
    for j, val in enumerate(row_data):
        if j == 0:
            add_rounded_rect(slide, cols_x[j], y, col_w[j] - Inches(0.04), Inches(0.4), bg, MUTED)
            add_text_box(slide, cols_x[j] + Inches(0.05), y + Inches(0.02), col_w[j] - Inches(0.1), Inches(0.35), val, font_size=10, bold=True, color=WHITE)
        else:
            c = GREEN if 'Yes' in str(val) and j == 1 else (RED if 'No' in str(val) else MUTED)
            if j == 4 and i == len(rows)-1: c = accent_col[j-1]
            add_text_box(slide, cols_x[j] + Inches(0.05), y + Inches(0.02), col_w[j] - Inches(0.1), Inches(0.35), val, font_size=9, color=c, align=PP_ALIGN.CENTER)

add_text_box(slide, Inches(0.8), Inches(6.6), Inches(11), Inches(0.4),
    'Auto mode tries engines in order: HF API → YOLO → OwlViT Local → Gradio. First with results wins.',
    font_size=12, color=MUTED, align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════
# SLIDE 9: 7 Violation Types — Overview
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, '7 Violation Types — Comprehensive Detection', 'Every violation includes confidence, reason, severity & priority')
violations = [
    ('1. No Helmet', 'Detects motorcycle riders without helmets.\nUses helmet-trained YOLO + color analysis.\nConfidence-based with auto/filter assessment.', RED, '80-98'),
    ('2. Triple Riding', 'Counts riders per motorcycle via\ndistance-based rider association.\nFilters out pedestrians, flags 3+ riders.', AMBER, '75-85'),
    ('3. Overloading', 'Aggressive overloading detection.\nClassifies 4-5 as Overloading,\n10-12 as Extreme Overloading.', ORANGE, '95-98'),
    ('4. Seatbelt', 'Detects drivers without seatbelts in cars.\nFilters auto-rickshaw false positives\nusing size/shape heuristics.', YELLOW, '30-60'),
    ('5. Wrong Side', 'Detects vehicles driving on wrong side.\nUses lane-angle analysis.\nIncludes confidence band & severity.', PURPLE, '60-85'),
    ('6. Red Light', 'Detects vehicles crossing during red.\nUses traffic light bounding box +\nvehicle position relative to stop line.', BLUE, '70-90'),
    ('7. Stop Line', 'Detects vehicles crossing the stop line.\nUses stop line Y-coordinate +\nvehicle bbox overlap analysis.', GREEN, '50-80'),
]
for i, (name, desc, accent, risk) in enumerate(violations):
    col = i % 4; row = i // 4
    x = Inches(0.4) + col * Inches(3.2)
    y = Inches(2.1) + row * Inches(2.5)
    w = Inches(3.0); h = Inches(2.2)
    cr = DARK2 if col < 3 else DARK
    add_rounded_rect(slide, x, y, w, h, cr, accent)
    add_rect(slide, x, y + Inches(0.0), w, Inches(0.04), accent)
    add_text_box(slide, x + Inches(0.1), y + Inches(0.15), Inches(2.8), Inches(0.35), name, font_size=14, bold=True, color=accent)
    add_text_box(slide, x + Inches(0.1), y + Inches(0.5), Inches(2.8), Inches(1.2), desc, font_size=9, color=MUTED)
    add_text_box(slide, x + Inches(0.1), y + Inches(1.75), Inches(2.8), Inches(0.3), f'Risk Range: {risk}', font_size=9, bold=True, color=accent)

# ═══════════════════════════════════════════════════════════════
# SLIDE 10-16: Before/After Image Comparisons (one per violation)
# ═══════════════════════════════════════════════════════════════
violation_samples = [
    ('No Helmet Detection', 'HELMET_MISSING_001.png', 'Motorcycle rider without helmet.\nRed bounding box + callout.\nConfidence: 87%, Risk: 30', RED),
    ('Triple Riding Detection', 'TRIPLE_RIDING_001.jpeg', 'Three riders on a motorcycle.\nRider count: 3, Association scores shown.\nRisk: 75, Priority: HIGH', AMBER),
    ('Motorcycle Overloading', 'OVERLOADING_001.jpg', '4+ occupants on single motorcycle.\nOverloading classification.\nRisk: 95, Priority: URGENT', ORANGE),
    ('Seatbelt Violation', 'BikesHelmets01.png', 'Driver without seatbelt in car.\nAuto-rickshaw filter applied.\nRisk: 40, Priority: MEDIUM', YELLOW),
    ('Wrong Side Driving', 'HELMET_MISSING_002.png', 'Vehicle on wrong side of road.\nLane angle > threshold.\nRisk: 85, Priority: HIGH', PURPLE),
    ('Red Light Violation', 'HELMET_MISSING_003.png', 'Vehicle crossing during red signal.\nTraffic light + stop line analysis.\nRisk: 90, Priority: HIGH', BLUE),
    ('Stop Line Violation', 'ILLEGAL PARKING_001.png', 'Vehicle crossed stop line.\nOverlap with stop line region.\nRisk: 60, Priority: MEDIUM', GREEN),
]

for vi, (vname, sample, desc, accent) in enumerate(violation_samples):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide)
    add_decorated_title(slide, f'Violation Showcase: {vname}', 'Input Image (left) → AI Analysis / Evidence (right)')

    # Source image
    src_path = os.path.join(SAMPLE_DIR, sample)
    img_added = add_image_safe(slide, src_path, Inches(0.5), Inches(2.2), Inches(5.8), Inches(4.5))
    if not img_added:
        add_rounded_rect(slide, Inches(0.5), Inches(2.2), Inches(5.8), Inches(4.5), DARK2, MUTED)
        add_text_box(slide, Inches(0.5), Inches(3.5), Inches(5.8), Inches(1.0), '[ Source Image ]', font_size=16, color=MUTED, align=PP_ALIGN.CENTER)
    add_callout(slide, Inches(0.5), Inches(6.8), 'Input', RED)

    # Evidence image
    ev_path = find_evidence(sample)
    img_added2 = add_image_safe(slide, ev_path, Inches(6.8), Inches(2.2), Inches(5.8), Inches(4.5)) if ev_path else False
    if not img_added2:
        add_rounded_rect(slide, Inches(6.8), Inches(2.2), Inches(5.8), Inches(4.5), DARK2, GREEN)
        add_text_box(slide, Inches(6.8), Inches(3.5), Inches(5.8), Inches(1.0),
            '[ AI Evidence Image ]\n\nAnnotated with violation callouts,\nconfidence scores, vehicle halos,\nand legend panel.', font_size=11, color=MUTED, align=PP_ALIGN.CENTER)
    add_callout(slide, Inches(6.8), Inches(6.8), 'AI Analysis', GREEN)

    # Description overlay
    add_rounded_rect(slide, Inches(8.5), Inches(2.3), Inches(3.8), Inches(1.4), DARK2, accent)
    lines = desc.split('\n')
    for i, line in enumerate(lines):
        add_text_box(slide, Inches(8.6), Inches(2.35) + i * Inches(0.35), Inches(3.6), Inches(0.3),
            line, font_size=10, color=WHITE if i == 0 else MUTED, bold=(i == 0))

    # Evidence features callout
    features = [
        '• Numbered callout circles',
        '• Violation legend panel',
        '• Vehicle instance IDs',
        '• Colored halos per vehicle',
        '• Confidence scores',
    ]
    for i, feat in enumerate(features):
        add_text_box(slide, Inches(8.6), Inches(4.0) + i * Inches(0.25), Inches(3.6), Inches(0.25),
            feat, font_size=9, color=MUTED)

# ═══════════════════════════════════════════════════════════════
# SLIDE 17: Evidence Generation
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'Evidence Generation — Full Package', 'Each violation generates annotated images + PDF reports')
ev_features = [
    ('Annotated Evidence Image', 'Numbered callout circles (①②③) on each violating vehicle\nColored halos matching vehicle type\nViolation legend panel (top-right)\nFooter summary bar with counts\nScene-specific markers (stop line, traffic light)'),
    ('PDF Evidence Report', 'Vehicle column with instance_id\nViolation type, confidence, vehicle info\nTimestamp and location metadata\nProfessional table layout for officer use'),
    ('Explainable AI Reason', 'Natural-language explanation per violation\nConfidence band and reliability score\nOccupancy estimate for motorcycles\nHuman review status and officer priority'),
    ('Repeat Offender Context', 'Vehicle history lookup\nRisk profile and watchlist status\nPrior violation count and severity trend\nRecommended enforcement action'),
]
for i, (title, desc) in enumerate(ev_features):
    col = i % 2; row = i // 2
    x = Inches(0.6) + col * Inches(6.3)
    y = Inches(2.2) + row * Inches(2.4)
    add_rounded_rect(slide, x, y, Inches(5.9), Inches(2.1), DARK2, RED)
    add_text_box(slide, x + Inches(0.2), y + Inches(0.1), Inches(5.5), Inches(0.4), title, font_size=16, bold=True, color=WHITE)
    add_text_box(slide, x + Inches(0.2), y + Inches(0.55), Inches(5.5), Inches(1.4), desc, font_size=12, color=MUTED)

# ═══════════════════════════════════════════════════════════════
# SLIDE 18: Competitive Differentiation
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'Why TRINETRA AI?', 'Competitive Differentiation')
cols_x2 = [Inches(0.6), Inches(4.0), Inches(7.2), Inches(10.4)]
col_w2 = [Inches(3.2), Inches(3.0), Inches(3.0), Inches(2.0)]
headers2 = ['Capability', 'Traditional CCTV', 'Basic Detector', 'TRINETRA AI']
for j, h in enumerate(headers2):
    add_rounded_rect(slide, cols_x2[j], Inches(2.0), col_w2[j] - Inches(0.04), Inches(0.45), DARK2, RED)
    c = RED if j == 3 else MUTED
    add_text_box(slide, cols_x2[j] + Inches(0.05), Inches(2.05), col_w2[j] - Inches(0.1), Inches(0.35),
        h, font_size=11, bold=(j==3), color=c, align=PP_ALIGN.CENTER)

rows2 = [
    ('Vehicle Detection', 'Manual', 'Yes (limited)', 'Yes + Multi-class + Zero-shot'),
    ('License Plate OCR', 'Manual', 'Some', 'Yes + Visibility Score'),
    ('Detection Engines', 'N/A', '1 (YOLO)', '4 (YOLO/HF/Local/Gradio)'),
    ('Explainable AI', 'No', 'No', 'Yes (Full)'),
    ('Human Review Workflow', 'No', 'No', '3-Stage System'),
    ('Risk Scoring', 'Subjective', 'Basic', 'Severity + Priority'),
    ('Hotspot Analytics', 'Manual', 'No', 'Automated + Heatmap'),
    ('Repeat Offender Tracking', 'Manual logs', 'No', 'Watchlist + Risk Profile'),
    ('Officer Prioritization', 'No', 'No', 'URGENT / HIGH / MEDIUM / LOW'),
    ('Evidence Package', 'Manual', 'No', 'PDF + Annotations'),
    ('Engine Configuration UI', 'N/A', 'No', 'Modal with status + token mgmt'),
    ('Traffic Intel Center', 'No', 'No', 'Full Dashboard'),
]
for i, row_data in enumerate(rows2):
    y = Inches(2.5) + i * Inches(0.4)
    bg = DARK if i % 2 == 0 else DARK2
    for j, val in enumerate(row_data):
        c = RED if j == 3 and ('Yes' in val or '4' in val or 'Full' in val or '3-Stage' in val or 'Severity' in val or 'Automated' in val or 'Watchlist' in val or 'URGENT' in val or 'PDF' in val or 'Modal' in val or 'Full' in val) else MUTED
        b = j == 3 and c == RED
        add_text_box(slide, cols_x2[j] + Inches(0.05), y, col_w2[j] - Inches(0.1), Inches(0.35),
            val, font_size=9, bold=b, color=c, align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════
# SLIDE 19: UI Screenshots Showcase
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'TRINETRA AI — User Interface', 'Clean, modern, dark-themed dashboard')
uis = [
    ('Upload & Analyze', 'Drop image → Select engine →\nView results with source + evidence\nside-by-side. Judge Mode available.'),
    ('Executive Summary', '10-panel KPI summary:\nMotorcycles, Pedestrians, Occupants,\nQuality, Violations, Helmet, Risk,\nReview, Reliability, Recommendation'),
    ('Violation Cards', 'Each violation shows: type badge,\nconfidence, priority, explainable\nreason, enforcement recommendation.'),
    ('Detection Engine Card', 'Shows which engine ran the analysis.\nActive mode with color-coded badge.\nHelmet model info also displayed.'),
    ('Engine Config Modal', 'Configure HF token, download OwlViT,\nview engine status with Ready/\nNot Ready badges + reasons.'),
    ('Validation Page', 'Review flagged violations with\nApprove/Reject workflow.\nSide-by-side image comparison.'),
]
for i, (title, desc) in enumerate(uis):
    col = i % 3; row = i // 3
    x = Inches(0.4) + col * Inches(4.2)
    y = Inches(2.1) + row * Inches(2.5)
    add_rounded_rect(slide, x, y, Inches(3.9), Inches(2.2), DARK2, BLUE)
    add_rounded_rect(slide, x + Inches(0.1), y + Inches(0.1), Inches(3.7), Inches(0.4), DARK2, RED)
    add_text_box(slide, x + Inches(0.15), y + Inches(0.15), Inches(3.6), Inches(0.3), title, font_size=13, bold=True, color=WHITE)
    add_text_box(slide, x + Inches(0.15), y + Inches(0.55), Inches(3.6), Inches(1.5), desc, font_size=10, color=MUTED)

# ═══════════════════════════════════════════════════════════════
# SLIDE 20: System Validation
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'System Validation', 'Prototype metrics based on test dataset')
metrics = [
    ('30', 'Images Tested'),
    ('92%', 'Vehicle Detection'),
    ('89%', 'OCR Success Rate'),
    ('84%', 'Helmet Assessment'),
    ('91%', 'Reviewed Flagged'),
    ('87%', 'Violation Detection'),
]
for i, (val, label) in enumerate(metrics):
    col = i % 3; row = i // 3
    x = Inches(0.8) + col * Inches(4.0)
    y = Inches(2.5) + row * Inches(1.8)
    add_rounded_rect(slide, x, y, Inches(3.6), Inches(1.5), DARK2, GREEN)
    add_text_box(slide, x, y + Inches(0.2), Inches(3.6), Inches(0.7), val, font_size=36, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
    add_text_box(slide, x, y + Inches(0.9), Inches(3.6), Inches(0.4), label, font_size=13, color=MUTED, align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════
# SLIDE 21: Responsible AI
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'Responsible AI & Human Oversight')
principles = [
    ('Confidence Scoring', 'Every detection includes a numerical confidence value — no binary decisions.', GREEN),
    ('Reliability Assessment', 'High / Medium / Low / Limited based on crowding, clarity, and occlusion.', BLUE),
    ('Explainable Decisions', 'Every violation has a natural-language reason (confidence, occupancy, review status).', PURPLE),
    ('Human Verification', '3-stage workflow: auto-confirmed, review recommended, manual verification required.', AMBER),
    ('No Automated Enforcement', 'AI is a decision-support tool, NOT an enforcement authority.', RED),
    ('Officer Control', 'All enforcement decisions remain under human control. AI recommends, officers decide.', WHITE),
]
for i, (title, desc, accent) in enumerate(principles):
    row = i // 2; col = i % 2
    x = Inches(0.8) + col * Inches(6.2)
    y = Inches(2.3) + row * Inches(1.5)
    add_rounded_rect(slide, x, y, Inches(5.8), Inches(1.3), DARK2, accent)
    add_text_box(slide, x + Inches(0.2), y + Inches(0.1), Inches(5.4), Inches(0.35), title, font_size=16, bold=True, color=accent)
    add_text_box(slide, x + Inches(0.2), y + Inches(0.5), Inches(5.4), Inches(0.7), desc, font_size=12, color=MUTED)

# ═══════════════════════════════════════════════════════════════
# SLIDE 22: Officer Workflow
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'Officer Workflow — Human-in-the-Loop')
wf_steps = ['Traffic Camera', 'TRINETRA AI', 'Violation Detection', 'Risk Assessment', 'Evidence Package', 'Human Review', 'Intel Center', 'Officer Action']
icons = ['📷', '🤖', '⚠️', '📊', '📄', '👁️', '📈', '👮']
for i, (step, icon) in enumerate(zip(wf_steps, icons)):
    x = Inches(0.5) + i * Inches(1.6)
    y = Inches(2.5)
    add_rounded_rect(slide, x, y, Inches(1.4), Inches(1.6), DARK2, RED)
    add_text_box(slide, x, y + Inches(0.1), Inches(1.4), Inches(0.5), icon, font_size=24, color=WHITE, align=PP_ALIGN.CENTER)
    add_text_box(slide, x, y + Inches(0.6), Inches(1.4), Inches(0.9), step, font_size=11, color=WHITE, align=PP_ALIGN.CENTER)
    if i < len(wf_steps) - 1:
        arr = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + Inches(1.4), y + Inches(0.6), Inches(0.2), Inches(0.3))
        arr.fill.solid(); arr.fill.fore_color.rgb = RED; arr.line.fill.background()

# ═══════════════════════════════════════════════════════════════
# SLIDE 23: System Architecture
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'System Architecture')
arch_steps = [
    ('📷', 'Traffic\nCamera'), ('🔍', 'Quality\nCheck'),
    ('🧠', 'Detection\nEngine'), ('⚠️', 'Violation\nChecks'),
    ('🔤', 'OCR\nEngine'), ('📄', 'Evidence\nGenerator'),
    ('📊', 'Risk\nAssessment'), ('👁️', 'Human\nReview'), ('📈', 'Intel\nCenter'),
]
for i, (icon, label) in enumerate(arch_steps):
    x = Inches(0.4) + i * Inches(1.4)
    y = Inches(2.5)
    add_rounded_rect(slide, x, y, Inches(1.2), Inches(1.4), DARK2, RED)
    add_text_box(slide, x, y + Inches(0.05), Inches(1.2), Inches(0.5), icon, font_size=22, color=WHITE, align=PP_ALIGN.CENTER)
    add_text_box(slide, x, y + Inches(0.55), Inches(1.2), Inches(0.8), label, font_size=10, color=WHITE, align=PP_ALIGN.CENTER)
    if i < len(arch_steps) - 1:
        arr = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + Inches(1.2), y + Inches(0.55), Inches(0.2), Inches(0.25))
        arr.fill.solid(); arr.fill.fore_color.rgb = RED; arr.line.fill.background()

# ═══════════════════════════════════════════════════════════════
# SLIDE 24: Potential Impact
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'Potential Impact for Bengaluru')
impacts = [
    ('Current Challenge', 'TRINETRA Impact'),
    ('Manual monitoring of thousands of traffic images daily', 'AI-assisted pre-screening reduces manual review workload'),
    ('Slow violation identification across officer shifts', 'Real-time detection with URGENT / HIGH priority flags'),
    ('Inconsistent enforcement prioritization', 'Standardized risk scoring and officer priority engine'),
    ('Paper-based evidence documentation', 'Automated PDF evidence packages with all case details'),
    ('No centralized violation intelligence', 'Traffic Intelligence Center with hotspots, trends, forecasts'),
    ('Difficult to track repeat offenders', 'Vehicle Risk Profiles + Watchlist for targeted enforcement'),
    ('Limited data for deployment decisions', 'Analytics-driven hotspot awareness and resource planning'),
]
for i, (left_col, right_col) in enumerate(impacts):
    y = Inches(2.2) + i * Inches(0.6)
    bg = DARK if i % 2 == 0 else DARK2
    add_rounded_rect(slide, Inches(0.8), y, Inches(5.8), Inches(0.5), bg, RED if i == 0 else None)
    add_rounded_rect(slide, Inches(6.8), y, Inches(5.8), Inches(0.5), bg, GREEN if i == 0 else None)
    c1 = WHITE if i == 0 else MUTED
    c2 = WHITE if i == 0 else GREEN
    add_text_box(slide, Inches(0.9), y + Inches(0.05), Inches(5.6), Inches(0.4), left_col, font_size=13, bold=(i==0), color=c1)
    add_text_box(slide, Inches(6.9), y + Inches(0.05), Inches(5.6), Inches(0.4), right_col, font_size=13, bold=(i==0), color=c2)

# ═══════════════════════════════════════════════════════════════
# SLIDE 25: Future Roadmap
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'Future Roadmap')
items = [
    'Live CCTV Streams — Real-time processing from existing camera feeds',
    'Edge AI Deployment — On-device inference at camera nodes for low latency',
    'Smart City Platform Integration — API-first design for municipal systems',
    'E-Challan Integration — Automated challan generation after officer approval',
    'Traffic Command Centers — Centralized monitoring with real-time dashboards',
    'Predictive Congestion Analytics — Forecasting high-risk periods and locations',
    'Multi-City Scale — Designed for deployment across Indian metropolitan cities',
]
add_multi_text(slide, Inches(1.0), Inches(2.4), Inches(11), Inches(4.0), items, font_size=16)

# ═══════════════════════════════════════════════════════════════
# SLIDE 26: Why TRINETRA AI? — Final
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_decorated_title(slide, 'Why TRINETRA AI?')
add_text_box(slide, Inches(1.0), Inches(2.2), Inches(11), Inches(0.8),
    'TRINETRA AI is not merely a traffic violation detector.\n'
    'It is an AI-powered Traffic Enforcement Intelligence Platform.',
    font_size=22, color=WHITE)

caps_final = [
    '✓ Explainable AI', '✓ Human Review', '✓ Evidence Generation',
    '✓ Risk Assessment', '✓ Repeat Offender Intelligence', '✓ Hotspot Analytics',
    '✓ Officer Prioritization', '✓ Smart City Readiness', '✓ OCR with Visibility',
    '✓ 4 Detection Engines', '✓ Engine Configuration UI', '✓ 7 Violation Types',
]
cols3 = 4
for i, cap in enumerate(caps_final):
    row = i // cols3; col = i % cols3
    x = Inches(0.6) + col * Inches(3.1)
    y = Inches(3.3) + row * Inches(0.65)
    add_rounded_rect(slide, x, y, Inches(2.8), Inches(0.5), DARK2, PURPLE)
    add_text_box(slide, x, y + Inches(0.05), Inches(2.8), Inches(0.4), cap, font_size=12, color=WHITE, align=PP_ALIGN.CENTER)

add_text_box(slide, Inches(1.0), Inches(5.6), Inches(11), Inches(0.8),
    'Designed to support Bengaluru Traffic Police in building safer, smarter,\n'
    'and more efficient urban mobility systems.',
    font_size=18, color=MUTED, align=PP_ALIGN.CENTER)

add_rect(slide, Inches(4.5), Inches(6.6), Inches(4.3), Inches(0.04), RED)
add_text_box(slide, Inches(1.0), Inches(6.8), Inches(11), Inches(0.3),
    'TRINETRA AI  |  v3.0.0  |  AI-Powered Traffic Enforcement Intelligence Platform',
    font_size=10, color=MUTED, align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════════════
output_dir = '/tmp/opencode'
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, 'TRINETRA_AI_Presentation.pptx')
prs.save(output_path)
print(f'Presentation saved: {output_path}')
print(f'Total slides: {len(prs.slides)}')
