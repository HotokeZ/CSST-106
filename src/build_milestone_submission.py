"""Build current, evidence-based checkpoint hand-in folders (no invented history)."""
from pathlib import Path
import csv
import hashlib
import io
import json
import shutil
import struct
import sys
import textwrap
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image, ImageDraw, ImageFont
from bigascheck.runner import run_path
from package_repo import prepare

OUT = ROOT / 'milestone submission'
DATE = '19 November 2026'
TEAM = ['Zyril Dela Paz', 'Axcel Andrei Delos Reyes', 'Jhed Aeron Lachano']
GREEN, INK, MUTED = '#38614b', '#17352e', '#53645e'
FOLDERS = {
    'p2': '02_Phase_2_50_Percent', 'p3': '03_Phase_3_Core',
    'p4': '04_Phase_4_80_Percent', 'p5': '05_Phase_5_Final',
    'individual': '06_Individual_Defense',
}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + '\n', encoding='utf-8')


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, str):
        return value.replace(str(ROOT), '<project-root>')
    return value


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == '.json':
        write(target, json.dumps(clean(json.loads(source.read_text(encoding='utf-8'))), indent=2))
    elif source.suffix.lower() in {'.md', '.csv', '.txt', '.ps1'}:
        write(target, source.read_text(encoding='utf-8').replace(str(ROOT), '<project-root>'))
    else:
        shutil.copy2(source, target)


class PDF:
    """Small vector-text PDF layout with bounded text and image slots."""
    def __init__(self, path, title, slide=False):
        self.path, self.title, self.slide = path, title, slide
        path.parent.mkdir(parents=True, exist_ok=True)
        self.pdf, self.pages = PdfPages(path), []
        self.n = 0

    def page(self, title, blocks, images=None, table=None, footer=None):
        self.n += 1
        wide = self.slide
        fig = plt.figure(figsize=(13.333, 7.5) if wide else (8.27, 11.69), facecolor='white')
        fig.text(.07, .955, 'BIGASCHECK  /  CSST 106', fontsize=10, color=GREEN, weight='bold')
        fig.text(.07, .905, title, fontsize=30 if wide else 20, color=INK, weight='bold', va='top')
        y = .825
        text_export = [title]
        for heading, content in blocks:
            if heading:
                fig.text(.07, y, heading, fontsize=18 if wide else 11.5, color=GREEN, weight='bold', va='top')
                y -= .047 if wide else .032
            if isinstance(content, str):
                content = [content]
            for paragraph in content:
                wrapped = textwrap.fill(paragraph, width=88 if wide else 93, break_long_words=True, break_on_hyphens=False)
                lines = wrapped.count('\n') + 1
                fig.text(.07, y, wrapped, fontsize=18 if wide else 10.5, color=INK, va='top', linespacing=1.4)
                y -= lines * (.045 if wide else .0205) + (.025 if wide else .018)
                text_export.append(paragraph)
        if table:
            columns, rows, box = table
            ax = fig.add_axes(box)
            ax.axis('off')
            widths = [.46, .18, .18, .18] if columns[0] == 'Split / method' else None
            tab = ax.table(cellText=rows, colLabels=columns, loc='center', cellLoc='left', colWidths=widths)
            tab.auto_set_font_size(False)
            tab.set_fontsize(15 if wide else 9)
            tab.scale(1, 1.8 if wide else 1.6)
            for (r, c), cell in tab.get_celld().items():
                cell.set_edgecolor('#d7e2da')
                cell.set_facecolor('#eaf1e8' if r == 0 else 'white')
                cell.get_text().set_color(INK)
            text_export.extend([' | '.join(map(str, row)) for row in [columns] + rows])
        for image, box, caption in images or []:
            ax = fig.add_axes(box)
            ax.imshow(Image.open(image))
            ax.axis('off')
            if caption:
                fig.text(box[0], box[1] - .018, caption, fontsize=9, color=MUTED, va='top')
        foot = footer or 'Current evidence package - prepared ' + DATE + ' | Independent local evaluation pending'
        fig.text(.07, .035, foot, fontsize=8, color=MUTED)
        fig.text(.94, .035, str(self.n), fontsize=9, color=MUTED, ha='right')
        self.pdf.savefig(fig)
        plt.close(fig)
        self.pages.append('\n\n'.join(text_export))

    def close(self):
        self.pdf.close()
        write(self.path.with_suffix('.md'), '\n\n---\n\n'.join(self.pages))


def avi(path, scenes, fps=1, seconds=8):
    """Write standard MJPEG AVI using real output frames; no external encoder."""
    frames = []
    for scene in scenes:
        buf = io.BytesIO()
        scene.convert('RGB').save(buf, 'JPEG', quality=80)
        frames.extend([buf.getvalue()] * (fps * seconds))
    w, h = scenes[0].size
    def chunk(tag, data):
        return tag + struct.pack('<I', len(data)) + data + (b'\0' if len(data) % 2 else b'')
    def listing(tag, data):
        return chunk(b'LIST', tag + data)
    avih = struct.pack('<14I', 1000000 // fps, max(map(len, frames)) * fps, 0, 16, len(frames), 0, 1, max(map(len, frames)), w, h, 0, 0, 0, 0)
    strh = struct.pack('<4s4sIHH8I4h', b'vids', b'MJPG', 0, 0, 0, 0, 1, fps, 0, len(frames), max(map(len, frames)), 0xffffffff, 0, 0, 0, w, h)
    strf = struct.pack('<IiiHH4sIiiII', 40, w, h, 1, 24, b'MJPG', w*h*3, 0, 0, 0, 0)
    hdrl = listing(b'hdrl', chunk(b'avih', avih) + listing(b'strl', chunk(b'strh', strh) + chunk(b'strf', strf)))
    data, indices, offset = [], [], 4
    for frame in frames:
        encoded = chunk(b'00dc', frame)
        data.append(encoded)
        indices.append(struct.pack('<4sIII', b'00dc', 16, offset, len(frame)))
        offset += len(encoded)
    body = b'AVI ' + hdrl + listing(b'movi', b''.join(data)) + chunk(b'idx1', b''.join(indices))
    path.write_bytes(b'RIFF' + struct.pack('<I', len(body)) + body)
    return len(frames) / fps


def font(size):
    for p in [Path('C:/Windows/Fonts/segoeui.ttf'), Path('C:/Windows/Fonts/arial.ttf')]:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def main():
    OUT.mkdir(exist_ok=True)
    paths = {k: OUT / v for k, v in FOLDERS.items()}
    for p in paths.values():
        p.mkdir(exist_ok=True)
    shared = OUT / 'shared'
    val = json.loads((shared / 'evaluation/validation/metrics.json').read_text())
    test = json.loads((shared / 'evaluation/development_test/metrics.json').read_text())
    cases = list(csv.DictReader((ROOT / 'outputs/checkpoints/test_cases/results.csv').open()))
    failures = json.loads((shared / 'evaluation/development_test/failure_log.json').read_text())
    metrics_rows = []
    for label, m in [('Validation', val), ('Development test', test)]:
        for method, key in [('Baseline', 'baseline'), ('Decision Tree', 'decision_tree')]:
            s = m[key]
            metrics_rows.append([label + ' / ' + method, f'{s["accuracy"]:.4f}', f'{s["macro_f1"]:.4f}', f'{s["broken_f1"]:.4f}'])
    matrix = shared / 'evaluation/development_test/decision_tree_confusion_matrix.png'
    prep = shared / 'evaluation/validation/preprocessing_strip.png'

    # Six real CLI outputs, including both classes and composites. Source hashes
    # let a reviewer check that every constituent belongs to the saved test split.
    catalog = json.loads((ROOT / 'data/splits/catalog.json').read_text())
    selected = [next(s for s in catalog['samples'] if s['kind'] == 'single' and s['label'] == lab) for lab in ['whole', 'broken']]
    selected += [s for s in catalog['samples'] if s['kind'] == 'composite'][:3]
    selected += [next(s for s in catalog['samples'] if s['kind'] == 'single' and s['label'] == 'whole' and s['id'] != selected[0]['id'])]
    sample_dir = shared / 'sample_inputs'
    sample_dir.mkdir(exist_ok=True)
    provenance = []
    for i, s in enumerate(selected, 1):
        name = f'{i:02d}_{s["kind"]}_{s["label"]}.png'
        copy(ROOT / 'data/splits' / s['image'], sample_dir / name)
        provenance.append({**s, 'image': name})
    write(sample_dir / 'SOURCE_AND_LICENSE.md', 'Source: Cristhian Sempertegui, Dataset de arroz peruano, Kaggle.\nhttps://www.kaggle.com/datasets/cristhiansempertegui/dataset-de-arroz-peruano\nKaggle lists MIT and links to https://www.mit.edu/~amini/LICENSE.md (checked 19 November 2026). See LICENSE.txt.\nSingles are test-split images; composites assemble six test grains and are not independent photographs. Source labels have not been independently reviewed.')
    copy(ROOT / 'docs/USER_PROVIDED_LICENSE.txt', sample_dir / 'LICENSE.txt')
    write(sample_dir / 'provenance.json', json.dumps(provenance, indent=2))
    rows = run_path(sample_dir, shared / 'sample_outputs', ROOT / 'artifacts/model.joblib', 'dark', False)
    if len(rows) != 6 or any(r['status'] != 'ok' for r in rows):
        raise RuntimeError('Six successful CLI executions are required.')
    annotations = [Path(r['output']) / 'annotated.png' for r in rows]
    # Runner logs are made portable after the actual inference has completed.
    copy(shared / 'sample_outputs/batch_results.json', shared / 'sample_outputs/batch_results.json')

    for src in (ROOT / 'outputs/checkpoints/test_cases').glob('*'):
        if src.is_file():
            copy(src, shared / 'test_cases' / src.name)
    for src in (ROOT / 'outputs/checkpoints/test_cases/inputs').glob('*'):
        copy(src, shared / 'test_cases/inputs' / src.name)
    for src in [ROOT/'requirements.txt', ROOT/'docs/USER_PROVIDED_LICENSE.txt', ROOT/'THIRD_PARTY_NOTICES.md']:
        copy(src, shared / src.name)
    for src in (shared / 'evaluation').rglob('*'):
        if src.is_file() and src.suffix.lower() in {'.json', '.csv', '.md'}:
            copy(src, src)
    copy(ROOT/'docs/LOCAL_PHOTO_COLLECTION.md', shared/'LOCAL_PHOTO_COLLECTION.md')
    write(shared/'local_ground_truth_template.csv', 'image,group_id,actual_whole,actual_broken')
    with (shared/'test_cases/test_cases_complete.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['ID','input','condition','expected','actual','pass_fail']
        writer=csv.DictWriter(f,fields);writer.writeheader()
        plans=json.loads((ROOT/'outputs/checkpoints/test_cases/case_plan.json').read_text())
        for r,p in zip(cases,plans):
            writer.writerow({'ID':r['id'],'input':p.get('image',p.get('sample_id','invalid image bytes')),
              'condition':r['condition'],'expected':f"HTTP {400 if r['id']=='TC10' else 200}; count {r['count'] or 'n/a'}, whole {r['whole'] or 'n/a'}, broken {r['broken'] or 'n/a'}",
              'actual':f"HTTP {r['actual_status']}; count {r['actual_detected']}, whole {r['actual_whole']}, broken {r['actual_broken']}",'pass_fail':'PASS' if r['pass']=='True' else 'FAIL'})

    # Data card, one page, copied into each relevant hand-in.
    card=PDF(shared/'Data_Card.pdf','BigasCheck data card')
    card.page('Dataset data card',[
      ('Source and license','Cristhian Sempertegui, Dataset de arroz peruano (Kaggle). Captured at a Lambayeque rice mill, August-September 2023, according to the archive README. Kaggle lists MIT and links to the supplied Mark Otto / Andrew Fong notice. Retain that notice and dataset credit.'),
      ('Labels and exclusions','Folder entero = whole; quebrado = broken. Mancha/stained and tiza/chalky are outside this classifier. Source integrity classes contain 4,219 images; 3,879 unique nonconflicting candidates remained, with 3,877 accepted. No independent per-image label review or capture-session IDs.'),
      ('Preparation','EXIF orientation, RGB conversion, foreground thresholding, morphology, grain-region filtering and geometric features. No augmentation. Approximate source resolution: 399-400 pixels per side. Baseline uses aspect ratio; tree adds solidity and ellipse fill.'),
      ('Split and evaluation limits','Seed 42; approximately 70/15/15 by image after exact duplicate/conflict removal. The exposed development-test gallery is not an untouched final evaluation. Reencoded duplicates and shared capture sessions may remain. Fresh local photos with manual counts are still needed.')],
      table=(['Split','Whole','Broken','Total'],[['Train','2,161','552','2,713'],['Validation','463','119','582'],['Development test','463','119','582'],['Accepted total','3,087','790','3,877']], [.07,.15,.86,.18]))
    card.close()

    # Checkpoint 2: exactly two report pages, with an explicit present-day date.
    p=PDF(paths['p2']/'Progress_Report.pdf','Phase 2 progress report')
    p.page('Phase 2 | progress report',[
      ('Prepared now; no retrospective claim',f'{DATE}. This package describes the implementation available now. It is not evidence of what existed at the original 22 October deadline. Team: '+', '.join(TEAM)+'.'),
      ('Implementation estimate: 80%','An evidence-based planning estimate, not a teacher-certified mark. Ten equal implementation work packages were used: eight implemented (80%) and two pending (20%). Implementation completion does not imply that every submission gate is met.'),
      ('Completed packages','1. Dataset audit/import. 2. Image split/sample catalog. 3. Preprocessing and grain features. 4. Aspect-ratio baseline. 5. Decision Tree. 6. Single-image/folder CLI and exports. 7. Upload/replace/sample web interface. 8. Metric and test-case tooling.'),
      ('Pending packages','9. Independent real-photo ground truth and target verification. 10. Robust pale/crowded-scene behavior supported by evidence. Final media, fresh installation and contribution statements are additional submission gates.'),
      ('Measured validation result',f"582 validation grains: baseline accuracy {val['baseline']['accuracy']:.4f}; Decision Tree accuracy {val['decision_tree']['accuracy']:.4f}, macro-F1 {val['decision_tree']['macro_f1']:.4f}. This is isolated-grain classification from saved features, not multi-grain counting accuracy.")])
    p.page('Phase 2 | blockers and revised plan',[
      ('Against the proposal sequence','Data acquisition/preparation, preprocessing, baseline, primary model, CLI and interface are implemented. Independent local evaluation and final hand-in preparation remain. No missing historical timeline or member ownership has been invented.'),
      ('Blockers','Original capture groups are absent; labels have not been independently reviewed. Development-test images have been exposed. Pale-background/composite tests retain false detections and classification errors. A fresh-clone dependency installation has not been verified; network package access was unavailable in this preparation session.'),
      ('Revised plan','First, inspect the six bundled outputs and rehearse the CLI. Next, obtain 30 labeled local development/validation photographs and ideally 10 untouched photographs from new physical samples or capture sessions. Have two reviewers resolve label/count disagreements. Assign actual owners before work.'),
      ('After independent data collection','Improve low-contrast segmentation and look-alike classification on development data. Freeze settings, evaluate the untouched local set once, export count MAE and percentage-point MAE, and update the report. Then verify a clean clone and rehearse with the exact demo laptop.'),
      ('Evidence and hand-in','Requirements and setup commands are in the shared source snapshot; Data_Card.pdf records preparation; six sample inputs and annotated outputs are included. The requested cp2-50 tag is still pending. Do not backdate it or describe this reconstruction as an October submission.')])
    p.close()

    # Checkpoint 3 results, four pages with actual failure images.
    p=PDF(paths['p3']/'Core_Results.pdf','Phase 3 results')
    p.page('Phase 3 | integrated method',[
      ('One-command pipeline','python src/run.py --input sample_inputs --output outputs/demo --background dark --connected-regions'),
      ('Shared implementation','RGB input -> foreground thresholding -> morphology/filtering -> optional watershed -> shape features -> Decision Tree -> annotated image, binary mask, JSON and grain CSV. src/run.py delegates to bigascheck/runner.py; bigascheck/vision.py and model.py implement the core.'),
      ('Primary model and baseline','The main classifier is a depth-5 Decision Tree with minimum leaf size 10. It uses aspect ratio, solidity and ellipse fill. The baseline thresholds aspect ratio. Training/validation/test assignments are preserved; no training images were moved into the test gallery.'),
      ('Required fixed untouched set: not yet satisfied','The 582 development-test images were excluded from training, but have since been exposed for demos/development. The 12 fixtures are software checks. Neither qualifies as a new set never used for training or tuning. Fresh lighting, blur, angle, occlusion and clutter photographs remain necessary.')],images=[(prep,[.08,.13,.84,.25],'Actual preprocessing evidence from the validation evaluation')])
    p.page('Phase 3 | preliminary measurements',[
      ('Classification scope','All rows measure isolated-grain classification from the saved extracted feature table. Baseline is stronger on validation; a small tree advantage on development test does not establish general superiority.'),
      ('CPU speed',f"Current run: validation mean {val['speed']['mean_ms']:.2f} ms/image; development-test mean {test['speed']['mean_ms']:.2f} ms/image. Each uses 3 warm-ups and 20 measured images, model loaded once. Image loading, segmentation, extraction and classification are included; rendering/web/output writing are excluded."),
      ('Reproduction','python src/evaluate.py --split validation --output outputs/validation\npython src/evaluate.py --split test --output outputs/development_test. Exact hashes, dependencies and hardware are in shared/evaluation/*/metrics.json. Runtime depends on laptop load.')],table=(['Split / method','Accuracy','Macro-F1','Broken F1'],metrics_rows,[.07,.24,.86,.23]))
    p.page('Phase 3 | failure analysis',[
      ('23 observed classification errors','16 whole references were predicted broken; 7 broken references were predicted whole. Short/low-elongation whole silhouettes and elongated broken look-alikes are hypotheses, not independently verified causes. Review source labels and contours before changing the model.'),
      ('Evidence','The grouped gallery on the following page contains at least 10 actual errors, and all 23 are copied under shared/evaluation/development_test/failures. The CSV/JSON logs identify references, predictions and source files.')],images=[(matrix,[.18,.12,.64,.46],'Rows: source reference. Columns: tree prediction.')])
    failure_sheet=shared/'evaluation/development_test/failure_contact_sheet.png'
    p.page('Phase 3 | failures and improvement plan',[
      ('Top 3 planned changes',[
       '1. Review short-whole / long-broken errors and add verified hard development examples; expected result: fewer false broken labels without reducing broken recall. Confirm using validation F1.',
       '2. Collect contrast/lighting fixtures and improve pale-background segmentation; expected result: lower false region count and count MAE on local development photos.',
       '3. Add manually labeled touching/overlapping grains and refine watershed markers; expected result: fewer merges/splits, checked with count MAE and reviewed masks. Targets are plans, not achieved results.'])],images=[(failure_sheet,[.06,.08,.88,.49],'Actual grouped error gallery; cause labels are hypotheses.')])
    p.close()

    # Final report includes all requested sections, limitations and explicit gaps.
    p=PDF(paths['p5']/'Final_Technical_Report.pdf','BigasCheck technical report')
    abstract=(ROOT/'docs/REPORT_DRAFT.md').read_text(encoding='utf-8').split('## Abstract')[1].split('## 1.')[0].strip()
    p.page('BigasCheck',[
      ('Experimental rice grain integrity inspection','Final-format technical report | '+DATE+'\n'+', '.join(TEAM)),
      ('Submission status','Runnable development prototype with measured source-grain results. Independent local evaluation, actual contributions, fresh installation verification and release tags remain pending. This report documents those limitations explicitly.'),
      ('Abstract',abstract)])
    p.page('1 | Problem and objectives',[
      ('Problem','Rice photographs contain variations in grain shape, illumination and contact between grains. BigasCheck explores a transparent computer vision workflow for detecting candidate grains, classifying visible integrity and estimating broken grains by count.'),
      ('Objectives',[
        'Provide a repeatable image-to-output application and source-grain whole/broken classifier.',
        'Compare a geometric baseline with a Decision Tree using separate training, validation and development-test image assignments.',
        'Proposal targets: broken-grain F1 >= 0.80, count MAE <= 5 grains, and broken-percentage MAE <= 5 percentage points. Independent local count and percentage targets are not yet measured.']),
      ('Scope','Static photographs and a local Flask demonstration. Outputs use pixel measurements. No physical calibration, official grading, mass-based broken fraction, cultivar identification or validated visible-defect grading is claimed.')])
    p.page('2 | Related approaches',[
      ('Global thresholding [1]','Otsu selects a grayscale threshold through between-class separation. It provides a simple foreground stage for rice on a contrasting background, but low contrast and uneven lighting motivate separate handling.'),
      ('Watershed separation [2]','Vincent and Soille describe watershed segmentation in digital spaces. BigasCheck uses distance-based markers to separate touching foreground regions. The implementation is not claimed to reproduce their exact algorithm; marker quality and overlap still affect outputs.'),
      ('Interpretable classifiers [3, 4]','Scikit-learn provides supervised classifiers, including Decision Trees. Shape descriptors allow compact, inspectable rules, but similar whole/broken silhouettes limit separability. Depth and leaf-size constraints restrict complexity.'),
      ('Rice transfer learning [5]','Perez Vera and colleagues compare pretrained CNNs on four Peruvian rice defect classes. Their four-class task and experimental protocol differ from this two-class shape prototype, so their reported scores cannot be ranked directly against our results. Learned appearance models are a future alternative, not part of this implementation.')])
    p.page('3 | Dataset and preparation',[
      ('Acquisition and license [6]','Public dataset: Cristhian Sempertegui, Dataset de arroz peruano. The archive contains 6,599 categorized PNGs plus four viewer images. Kaggle lists MIT and links to the preserved notice. The archive credits a Lambayeque rice mill and capture during August-September 2023.'),
      ('Labels and cleaning','Source folder labels entero and quebrado become whole and broken. Mancha and tiza are excluded. Exact duplicates and conflicting labels are removed; readability and single-region screening retain 3,877 grain images. Source labels have not received independent human review.'),
      ('Leakage controls and limits','Seed 42; approximately 70/15/15 by image, with exact byte hashes disjoint across splits. Original capture-session IDs are unknown. Exposed development-test images cannot support an untouched final-evaluation claim. No training augmentation was used.')],table=(['Split','Whole','Broken','Total'],[['Train','2,161','552','2,713'],['Validation','463','119','582'],['Development test','463','119','582']],[.07,.15,.86,.16]))
    p.page('4 | Methodology and algorithms',[
      ('Preprocessing','Apply EXIF orientation and RGB conversion. A dark-background path uses grayscale Otsu; pale-background mode combines foreground thresholding and local contrast. Morphology removes noise and fills small holes. Region size and border checks remove incomplete or implausible regions.'),
      ('Separation and descriptors','Optional distance-transform watershed partitions connected foreground. The shape classifier uses major/minor-axis aspect ratio, area/convex-hull area (solidity), and area/(major-axis x minor-axis), called ellipse fill in the code. Uniform scaling approximately preserves these descriptors; segmentation errors do not disappear.'),
      ('Classification and aggregation','An aspect-ratio threshold forms the baseline; the current tree has maximum depth 5 and minimum leaf size 10. Predicted whole/broken regions are counted. Broken percentage = 100 x predicted broken / detected grains. Zero-region inputs do not produce a fabricated zero-percent quality result.'),
      ('Scores and units','The interface shows a Decision Tree leaf-vote score, not calibrated certainty. Pixel measurements are not millimeters. Candidate regions should be visually checked.')],images=[(prep,[.07,.10,.86,.24],'Source image, foreground processing and output evidence')])
    p.page('5 | Software and reproducibility',[
      ('Environment','Pinned Python package versions are in requirements.txt; the measured environment uses Python 3.13.3 on Windows, CPU/SciPy segmentation. OpenCV is optional and changes backend behavior; keep the tested default environment for these weights.'),
      ('Commands',[
        'Setup: .\\setup.ps1. Web demonstration: .\\start.ps1.',
        'Single image: python src/predict.py --input sample_inputs/01_single_whole.png --output outputs/demo --background dark --connected-regions.',
        'Folder: python src/run.py --input sample_inputs --output outputs/batch --background dark --connected-regions.',
        'Evaluation: python src/evaluate.py --split test --output outputs/evaluation. The complete source PNG dataset is required for speed/failure rendering; the included feature table supports metric reproduction.']),
      ('Saved assets','The source snapshot includes model.joblib, the portable feature/split table and six sample inputs. Full raw data and personal photographs are excluded. The gallery is rebuilt from the Kaggle ZIP with extract and prepare-samples commands in README.md.'),
      ('Verification status','Current-environment software checks and pipeline runs are logged. A clean source copy is checked separately from a fresh dependency installation. Network package access was unavailable, so a new dependency installation is not certified.')])
    p.page('6 | Experiments and results',[
      ('Protocol','Validation guides model selection. Development-test metrics are descriptive because those images have been exposed in the gallery. Feature-table classification and image pipeline timing are different measurements; neither directly measures detection precision or segmentation IoU.'),
      ('Interpretation','The baseline wins on validation. The tree is slightly higher on development test. These results do not establish a general tree advantage. Class imbalance makes macro-F1 and broken-class F1 useful alongside accuracy.'),
      ('Speed',f"Current CPU means: {val['speed']['mean_ms']:.2f} ms/image (validation), {test['speed']['mean_ms']:.2f} ms/image (development test). Twenty images after three warm-ups, model loaded once; output rendering, browser transport and file writing excluded. Logs retain hardware and exact model/data hashes.")],table=(['Split / method','Accuracy','Macro-F1','Broken F1'],metrics_rows,[.07,.20,.86,.23]))
    p.page('7 | Error analysis and test cases',[
      ('Classification errors','The tree makes 23 errors among 582 development-test grains: 16 whole -> broken and 7 broken -> whole. Broken precision is 0.8750 and recall 0.9412. Gallery cause assignments are hypotheses pending label and contour review.'),
      ('12 demonstration cases','The recorded log contains 9 PASS and 3 FAIL. All-whole and all-broken six-grain composites each have one integrity error. A pale-background six-whole composite yields 37 candidate regions, including 6 predicted broken. These failures are retained rather than hidden.'),
      ('Hard/edge cases','Cases include half-resolution, dim lighting, frame-cut grain, invalid upload, blank input, pale background and touching synthetic ellipses. These are repeatable software fixtures, not independent natural-camera accuracy evidence.')],images=[(matrix,[.24,.10,.52,.40],'Development-test confusion matrix; source-reference labels')])
    p.page('8 | Limitations and conclusion',[
      ('Limitations','No independent local whole/broken annotations, manually verified multi-grain counts, detection boxes or masks are available. Count MAE, percentage-point MAE, mAP and IoU are therefore unreported. Pale/crowded scenes remain unreliable; source capture groups and manual label review are missing.'),
      ('Research objectives status','The development broken F1 exceeds the numeric proposal threshold on isolated source grains, but does not verify local-grain performance. Multi-grain count and broken-percentage objectives remain unverified. Larger detected counts do not demonstrate correctness.'),
      ('Conclusion','The project implements an interpretable local pipeline, web interface, split-preserving sample gallery and reproducible development metrics. It is suitable for demonstrating the method and its failure modes. Reliable field or rice-quality claims require fresh capture-level evaluation and stronger segmentation evidence.'),
      ('Next steps','Review reference labels; collect 30 local development/validation photos plus ideally 10 untouched new sample/session photos; improve segmentation and ambiguous shapes on development data; freeze settings and evaluate once; verify a clean installation, complete individual statements and rehearse before release.')])
    p.page('9 | Contributions and hand-in status',[
      ('Team details','Names are supplied by the team. Contribution assignments and commit links were deliberately deferred and are not inferred from repository account ownership.'),
      ('Contribution table - awaiting member confirmation','Each member must supply actual modules, 3-5 genuine commits, a technical decision, a solved problem and two learned concepts. The individual PDFs are visibly marked drafts. Do not submit them as completed personal statements.'),
      ('Release history','Requested tags are cp2-50, cp3-core, cp4-80 and v1.0. No past checkpoint work or teacher assessment has been reconstructed as historical fact. Tags are not created by this package builder. Tag only reviewed real commits and describe any present-day reconstruction honestly.'),
      ('Still required','Independent local evaluation; real contribution table/statements; fresh dependency installation verification; teacher acceptance of the captioned output-walkthrough backup versus a live UI screen recording; tag/repository artifact upload verification.')],table=(['Member','Confirmed contribution'],[[n,'Pending member confirmation'] for n in TEAM],[.07,.13,.86,.18]))
    p.page('10 | References',[
      ('[1] Otsu (1979)','A Threshold Selection Method from Gray-Level Histograms. IEEE Transactions on Systems, Man, and Cybernetics, 9(1). DOI: 10.1109/TSMC.1979.4310076.'),
      ('[2] Vincent and Soille (1991)','Watersheds in Digital Spaces: An Efficient Algorithm Based on Immersion Simulations. IEEE Transactions on Pattern Analysis and Machine Intelligence. Author-hosted paper: people.cmm.minesparis.psl.eu/users/marcoteg/cv/publi_pdf/MM_refs/vincent/1991_PAMI_VincentSoille_watershed.pdf'),
      ('[3] Pedregosa et al. (2011)','Scikit-learn: Machine Learning in Python. Journal of Machine Learning Research, 12, 2825-2830. https://www.jmlr.org/papers/v12/pedregosa11a.html'),
      ('[4] scikit-learn documentation','Decision Trees. https://scikit-learn.org/stable/modules/tree.html (accessed 19 November 2026). The experiment uses pinned version 1.7.2; current online documentation may describe a later version.'),
      ('[5] Perez Vera et al. (2026)','Deep Learning Models for Defect Identification in Oryza sativa Rice Grains: A Comparative Study. AgriEngineering, 8(6), 252. https://doi.org/10.3390/agriengineering8060252'),
      ('[6] Sempertegui (2023)','Dataset de arroz peruano. https://www.kaggle.com/datasets/cristhiansempertegui/dataset-de-arroz-peruano. Publisher lists MIT; linked notice: https://www.mit.edu/~amini/LICENSE.md. Course checkpoint requirements supplied by the team are the submission specification.')])
    p.page('Appendix A | six actual sample outputs',[
      ('How to inspect','Each image below is an actual annotated output generated by the saved model. Inputs, masks, grain CSV and JSON are in shared/sample_inputs and shared/sample_outputs. Source labels/composite counts are references, not independently reviewed local ground truth.')],images=[(im,[.07+(i%2)*.46,.51-(i//2)*.22,.40,.17],Path(rows[i]['image']).stem) for i,im in enumerate(annotations)])
    p.close()

    # Captioned backup video from actual inference outputs, with no simulated UI.
    scenes=[]
    for i, (im, row) in enumerate(zip(annotations,rows)):
        scene=Image.new('RGB',(1280,720),'#f5f7f2');d=ImageDraw.Draw(scene)
        d.text((45,30),'BigasCheck | actual pipeline output',font=font(34),fill=INK)
        picture=Image.open(im).convert('RGB');picture.thumbnail((760,530))
        scene.paste(picture,(45,110))
        lines=[f'Sample {i+1} of 6',Path(row['image']).stem,f"Detected: {row.get('detected')}",f"Whole: {row.get('whole')}",f"Broken: {row.get('broken')}",'Composite labels are references.','Independent local evaluation pending.']
        y=120
        for line in lines:
            for part in textwrap.wrap(line,31):
                d.text((840,y),part,font=font(22),fill=INK);y+=38
        d.text((45,660),'CPU pipeline: input > segmentation > features > Decision Tree > output',font=font(23),fill=GREEN)
        scenes.append(scene)
    title=Image.new('RGB',(1280,720),'#f5f7f2');d=ImageDraw.Draw(title)
    title_lines=['BigasCheck - pipeline demonstration',*TEAM,'Command: python src/run.py --input sample_inputs','--output outputs/demo --background dark --connected-regions','Captioned walkthrough of actual saved outputs; no audio.','This is not a live web-interface screen recording.']
    for i,line in enumerate(title_lines):d.text((50,70+i*75),line,font=font(28 if i else 38),fill=INK)
    scenes.insert(0,title)
    end=Image.new('RGB',(1280,720),'#f5f7f2');d=ImageDraw.Draw(end)
    ending=['Measured development evidence','Decision Tree: 96.05% accuracy; macro-F1 0.9409','12 demo cases: 9 pass, 3 fail','Pale-background and look-alike failures remain.','Not verified: local count MAE or broken-percentage MAE.','Live rehearsal: upload/replace, sample picker, mask, CSV/JSON.','See report and logs for scope, timing and source/license.']
    for i,line in enumerate(ending):d.text((50,70+i*78),line,font=font(29),fill=INK)
    scenes.append(end)
    duration=avi(shared/'Demo_Backup.avi',scenes)
    write(shared/'VIDEO_README.md',f'Captioned actual-output walkthrough: {duration:.0f} seconds, Motion JPEG AVI, 1280x720, no audio. It is generated from actual current CLI output images; it is not a live UI screen recording. Play the file on the demo laptop. If the teacher requires a screen recording, record the real interface using Demo_Script.md instead. This file cannot demonstrate upload gestures or arbitrary teacher input.')
    write(shared/'Demo_Script.md','''# Live demo / screen recording script (under 5 minutes)
0:00-0:25 Introduce scope and team. Experimental broken percentage by count, not official grade.
0:25-1:15 Run start.ps1. Choose a whole source sample and analyze; show mask, count and tree vote.
1:15-2:00 Choose mixed composite; explain it is assembled from test grains. Show input preview and replacement.
2:00-2:45 Download CSV/JSON and run python src/run.py --input sample_inputs --output outputs/demo --background dark --connected-regions.
2:45-3:30 Show a recorded failure; explain pale-background false regions and short-whole confusion.
3:30-4:15 Show evaluate.py output, matrix and 12-case log; distinguish per-grain F1 from count MAE.
4:15-4:50 Show remaining local-evaluation work and conclude. Accept a teacher-provided image in the live demo.
Record the actual screen if required; do not present the automated output walkthrough as a screen capture.
''')

    # Two rendered 12-slide decks, with editable text sources.
    slide_content=[
      ('BigasCheck', [('Purpose','Experimental rice grain integrity and broken proportion by count.'),('Team',', '.join(TEAM))],None),
      ('Problem and objectives',[('Goals','Interpretable image-to-output inspection. Proposal targets: broken F1 >= 0.80; count MAE <= 5; percentage-point MAE <= 5.'),('Evidence boundary','Only isolated source-grain classification has measured development evidence. Independent local counting is pending.')],None),
      ('Dataset and license',[('Source','Cristhian Sempertegui, Peruvian rice dataset. Kaggle lists MIT; notice preserved.'),('Prepared split','3,877 accepted: 2,713 train, 582 validation, 582 development test. Two integrity classes; exact duplicate/conflict exclusion.'),('Limits','Unknown capture groups, source labels not independently reviewed, development-test gallery exposed.')],None),
      ('Integrated pipeline',[('Processing','RGB input -> thresholding -> morphology -> optional watershed -> shape features -> tree -> output.'),('Features','Aspect ratio, solidity and ellipse fill. Shared vision/model code supports CLI and Flask.')],None),
      ('Preprocessing evidence',[('Inspect the regions','Incorrect segmentation changes the shape features and grain count. Pale and touching scenes remain experimental.')],(prep,[.07,.16,.86,.42],'Actual validation preprocessing output')),
      ('Baseline versus Decision Tree',[('Reading the table','Baseline is stronger on validation. The development-test tree advantage is small; no general superiority claim.')], 'metrics'),
      ('Errors and CPU speed',[('Observed errors',f"23 development-test errors: 16 whole -> broken; 7 broken -> whole. Mean CPU pipeline {test['speed']['mean_ms']:.2f} ms/image, 20 images after 3 warm-ups; excludes rendering/output/web.")],(matrix,[.30,.10,.40,.47],'Rows reference; columns predicted')),
      ('Actual sample output',[('Composite demonstration','Six test-source grains assembled into one image. A successful example is not an independent camera photograph.')],(annotations[2],[.18,.10,.64,.45],'Actual current output; inspect accompanying JSON')),
      ('Testing includes failures',[('12 repeatable cases','9 PASS / 3 FAIL. Hard cases: scale, dim lighting, pale background, border, invalid upload and touching synthetic shapes.'),('Retained failures','All-whole and all-broken composites each misclassify one grain. Pale composite detects 37 regions for 6 reference grains.')],None),
      ('Live demonstration',[('Run','start.ps1 for the web interface; src/run.py for one image or a folder.'),('Show','Upload and replace preview; select a sample; inspect overlay/mask; export CSV/JSON; accept an unseen image.'),('Backup','64-second captioned actual-output AVI. Record the real screen if the teacher requires a screen capture.')],None),
      ('Limitations and next work',[('Unverified','Independent local count/percentage MAE, segmentation IoU, capture isolation and source-label review.'),('Priority changes','Review look-alikes; improve pale contrast; refine touching-grain markers using development data. Freeze before a fresh final evaluation.'),('Readiness','Current-format documents do not certify past milestone completion. Fresh installation, tags and real contributions remain pending.')],None),
      ('References and team defense',[('Research basis','Otsu (1979), DOI 10.1109/TSMC.1979.4310076; Vincent & Soille (1991), watershed; Pedregosa et al. (2011), JMLR 12:2825-2830; Perez Vera et al. (2026), DOI 10.3390/agriengineering8060252.'),('Team defense','Each member must explain actual work and link 3-5 genuine commits. Contributions are deferred; account ownership is not authorship evidence.')],None),
    ]
    for key,name in [('p4','Draft_Presentation.pdf'),('p5','Final_Presentation.pdf')]:
        deck=PDF(paths[key]/name,'BigasCheck presentation',slide=True)
        for title,blocks,visual in slide_content:
            if visual=='metrics':deck.page(title,blocks,table=(['Split / method','Accuracy','Macro-F1','Broken F1'],metrics_rows,[.07,.15,.86,.35]))
            else:deck.page(title,blocks,images=[visual] if visual else None)
        deck.close()

    # Phase 4: compact checkpoint status, differences stated honestly.
    p=PDF(paths['p4']/'Application_Testing_Report.pdf','Phase 4 application testing')
    p.page('Phase 4 | application and testing',[
      ('Implemented','Flask upload/replace preview, test gallery, overlay, mask, grain counts, per-grain leaf vote, core time, CSV/JSON downloads, shared CLI/batch core and reproducible evaluation. Image-based student demonstration; no video/webcam or official quality certification is claimed.'),
      ('Metrics since checkpoint 3','This package reconstructs both checkpoints from current evidence. No independently preserved checkpoint-3 code/metric snapshot establishes a historical improvement. Current results are unchanged in classification when rerun; a historical performance delta is not available.'),
      ('Test cases and limitations','See Test_Cases.csv for 12 cases with input, condition, expected, actual and PASS/FAIL. Nine passed and three failed. Hard/edge fixtures are included. Independent local-photo evaluation remains pending.'),
      ('Documentation and media','Draft_Technical_Report.pdf, 12-slide Draft_Presentation.pdf, sample outputs, and a 64-second actual-output walkthrough are included. The walkthrough is not a live interface capture; use the script to record the UI if required.'),
      ('Teacher sign-off remaining tasks','Collect/review fresh local photos; measure count and percentage-point MAE; review labels/capture groups; verify clean install; confirm actual member work and commits; review release readiness. The cp4-80 tag has not been created by this builder.')])
    p.close()
    copy(paths['p5']/'Final_Technical_Report.pdf',paths['p4']/'Draft_Technical_Report.pdf')
    copy(paths['p5']/'Final_Technical_Report.md',paths['p4']/'Draft_Technical_Report.md')

    # Genuine contributions must come from members; create explicitly draft forms.
    for name,surname in zip(TEAM,['Dela Paz','Delos Reyes','Lachano']):
        p=PDF(paths['individual']/(surname+' - Contribution.pdf'),name+' contribution DRAFT')
        p.page('DRAFT | individual contribution',[
          ('Member',name+' | Not a completed contribution statement. Fill with actual work before hand-in.'),
          ('1. Modules and functions written','List the precise file paths, functions and what you personally implemented. Separate edits you wrote from code you only reviewed. Contributions have not been assigned or inferred in this package.'),
          ('2. Three to five key commits','Insert real GitHub commit links and explain each change. Do not invent commits, backdate work or claim another member\'s authorship.'),
          ('3. Technical decision','Describe one decision you personally made, the alternative considered, the tradeoff and the code/evidence that supports it.'),
          ('4. Problem solved','Describe the symptom, how you isolated its cause, the actual change, and the check showing the result.'),
          ('5. Lessons learned','Explain two computer vision concepts you understand better, connect each to your actual code, and state what you would change next time.'),
          ('Defense preparation','Rehearse your own code walkthrough, a what-if question and a concept question. Submit only after you can explain every claimed change.')],footer='DRAFT - MEMBER INPUT REQUIRED - DO NOT SUBMIT AS A COMPLETED PERSONAL STATEMENT')
        p.close()

    # Per-phase checklists map every requested item to actual evidence or a gap.
    checklist={
      'p2': [('Pinned requirements + fresh-clone README','Included in shared source snapshot; fresh dependency install UNVERIFIED'),('Prepared dataset + data card','Data_Card.pdf and split table; full raw dataset fetched separately'),('src preprocessing/features','src/preprocess.py wrapper and bigascheck/vision.py in source snapshot'),('Baseline and validation measurement','Progress_Report.pdf; shared/evaluation/validation'),('One-command prototype','shared/How_to_Run.md; six actual CLI executions'),('6 outputs or <=2 minute recording','sample_outputs folder: six annotated PNGs plus masks/CSV/JSON'),('1-2 page progress report','Progress_Report.pdf, 2 pages'),('cp2-50 tag','PENDING; use actual reviewed commit, no backdating')],
      'p3': [('Primary model and integrated pipeline','Shared source snapshot, trained shape tree and CLI'),('End-to-end one command','shared/How_to_Run.md and six executed sample outputs'),('Fixed never-trained/tuned representative set','MISSING: exposed development-test set and fixtures do not meet this condition'),('Baseline/main + laptop speed','Core_Results.pdf and metrics JSON; development scope disclosed'),('10+ failures grouped + confusion matrix','23-image failure gallery, logs and confusion matrices'),('Top 3 improvements','Core_Results.pdf page 4'),('2-4 page PDF and cp3-core tag','Core_Results.pdf is 4 pages; tag PENDING')],
      'p4': [('Nearly complete application','Shared source snapshot; 80% implementation estimate only'),('Upload interface with clear outputs','Flask app; UI still needs live rehearsal/screen capture'),('evaluate.py test/speed + change since cp3','Reproduced development evidence; historical cp3 delta unavailable'),('Performance/limitations','Application_Testing_Report.pdf and report sections 7-8'),('10+ test cases including 3 hard','Test_Cases.csv: 12 cases, 9 pass / 3 fail'),('Draft report and 8+ slides','Draft_Technical_Report.pdf and 12-slide Draft_Presentation.pdf'),('<=5 minute backup','Demo_Backup.avi: 64 sec captioned actual-output walkthrough; screen capture if required'),('cp4-80 tag and teacher remaining list','Tag and teacher sign-off PENDING; remaining list included')],
      'p5': [('Working application tagged v1.0','Application included; release tag PENDING readiness review'),('Source/setup/run/evaluation/weights/samples','Shared source snapshot with model and six sample inputs'),('Final report PDF + contribution table','Final_Technical_Report.pdf; table explicitly pending genuine member input'),('Screenshots or outputs + appendix','Six sample outputs and report Appendix A'),('Presentation PDF','12-slide Final_Presentation.pdf'),('<=5 minute backup video','64-second Demo_Backup.avi; captioned actual-output walkthrough'),('Research result completeness','Independent local count/percentage evaluation and source review MISSING')],
      'individual': [('Each member 1-2 pages named Surname - Contribution.pdf','Three one-page DRAFT forms created; member completion REQUIRED'),('Files + 3-5 commits','Not supplied; must be real personal evidence'),('Decision + rejected alternative','Member input REQUIRED'),('Bug + cause + fix','Member input REQUIRED'),('Two CV lessons and reflection','Member input REQUIRED'),('2-3 minute code defense','Each member rehearses own actual code')],
    }
    for key,items in checklist.items():
        lines=['# '+FOLDERS[key].replace('_',' '),'Prepared '+DATE+'. Current-state package; no historical submission or teacher approval is claimed.','| Required item | File / status |','|---|---|']
        lines += ['| '+a+' | '+b+' |' for a,b in items]
        lines += ['','Shared source, sample inputs/outputs, license, evaluation, video and run guide: `../shared/`. Submit this phase folder with the shared folder, or use its complete ZIP.','Repository: https://github.com/HotokeZ/CSST-106']
        write(paths[key]/'SUBMISSION_CHECKLIST.md','\n'.join(lines))
        if key!='individual':
            copy(shared/'Data_Card.pdf',paths[key]/'Data_Card.pdf')
            copy(shared/'test_cases/test_cases_complete.csv',paths[key]/'Test_Cases.csv')
            copy(shared/'Demo_Script.md',paths[key]/'Demo_Script.md')
    write(shared/'How_to_Run.md','''# Run the included source snapshot
Extract BigasCheck_Source.zip to a new directory. Open PowerShell in that directory.
Python 3.13 is the tested version. Run .\\setup.ps1, then .\\start.ps1 for the web interface.
One-command image run after setup:
.\\.venv\\Scripts\\python.exe src/predict.py --input sample_inputs/01_single_whole.png --output outputs/demo --background dark --connected-regions
Batch: .\\.venv\\Scripts\\python.exe src/run.py --input sample_inputs --output outputs/demo --background dark --connected-regions
Outputs: annotated.png, mask.png, results.json, grains.csv and batch_results.json.
Software checks: .\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v
Evaluation: .\\.venv\\Scripts\\python.exe src/evaluate.py --split test --output outputs/evaluation
The full original source PNGs must be obtained from Kaggle to reproduce timing and all failure images. Save ZIP as inputs/archive.zip, then run:
.\\.venv\\Scripts\\python.exe -m bigascheck extract inputs/archive.zip data/raw
.\\.venv\\Scripts\\python.exe -m bigascheck prepare-samples
The model and portable feature/split table are included; source images are excluded except for six test examples/composites.
Fresh dependency installation needs network access and remains unverified. A source-copy check using existing installed packages does not establish fresh-install success.
''')
    write(shared/'Release_Tags.md','''# Tags and repository hand-in
Repository: https://github.com/HotokeZ/CSST-106
Requested names: cp2-50, cp3-core, cp4-80, v1.0.
No tags are created automatically by this packaging script. These packages were generated on 19 November 2026 from current evidence, not from preserved October/early-November snapshots.
Review the remaining gaps and upload the current artifact folders before tagging the relevant actual commit. Do not backdate work or represent current tags as historical checkpoint submissions. The teacher must determine how a reconstructed submission is accepted.
Create v1.0 only after team readiness review, genuine contributions, independent evaluation and fresh-install verification. Use annotated Git tags and push the actual tags to GitHub.
''')
    # Include real wrapper under src for phase-2 code discovery; core is shared.
    write(ROOT/'src/preprocess.py','''"""Expose the real shared preprocessing stage for checkpoint review."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bigascheck.vision import Settings, load_rgb, segment

if __name__ == '__main__':
    import argparse
    from PIL import Image
    parser = argparse.ArgumentParser(description='Apply the same preprocessing used by BigasCheck')
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--background', choices=['auto','dark','pale','light'], default='auto')
    args = parser.parse_args()
    grains, rejected, mask = segment(load_rgb(args.input), Settings(background=args.background))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask).save(target)
''')
    snapshot=OUT/'_source_snapshot'
    prepare(snapshot)
    for src in sample_dir.iterdir():copy(src,snapshot/'sample_inputs'/src.name)
    for name in ['validation','development_test']:
        copy(shared/'evaluation'/name/'metrics.json',snapshot/'docs/evidence'/(name+'_current_metrics.json'))
    with zipfile.ZipFile(shared/'BigasCheck_Source.zip','w',zipfile.ZIP_DEFLATED) as z:
        for src in snapshot.rglob('*'):
            if src.is_file() and not any(part in {'__pycache__', 'outputs', '.pytest_cache'} for part in src.relative_to(snapshot).parts):
                z.write(src,src.relative_to(snapshot))
    # Keep a single clean source snapshot alongside ZIPs for inspection.
    write(OUT/'README.md','''# BigasCheck milestone submission
Prepared 19 November 2026 from the current project. Separate checkpoint folders map each hand-in item to its evidence.

- 02_Phase_2_50_Percent: two-page progress report, one-page data card and checklist.
- 03_Phase_3_Core: four-page results PDF, failure analysis, improvement plan and checklist.
- 04_Phase_4_80_Percent: application/testing report, technical report draft, 12-slide draft and test cases.
- 05_Phase_5_Final: 12-page final-format report with six-output appendix, 12-slide PDF, test cases and checklist.
- 06_Individual_Defense: three one-page draft contribution forms. Each member must complete their own real evidence.
- shared: source snapshot ZIP, six input/output examples, evaluation matrices/failures/logs, sample license, test log, 64-second captioned backup AVI and demo script.

Each *_Complete_Package.zip contains the phase folder and the shared evidence needed to review it. These are submission packages with explicitly documented gaps, not certifications that every rubric gate is passed.

Outstanding: untouched representative local evaluation and manual labels/counts; actual member contributions/commit links; fresh dependency installation; release tags; confirm whether a live UI screen recording is required instead of the automated actual-output walkthrough.
The current reports do not establish past checkpoint dates, historical improvement, or a teacher mark. No past work, authorship, metric, or Git tag is fabricated.
Repository publication of these new packages must still be verified; existing project repository: https://github.com/HotokeZ/CSST-106.
''')
    for key,path in paths.items():
        archive=OUT/(path.name+'_Complete_Package.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for base in [path,shared] if key!='individual' else [path]:
                for src in base.rglob('*'):
                    if src.is_file() and 'matplotlib_cache' not in src.parts:
                        z.write(src,src.relative_to(OUT))
    files=[p for p in OUT.rglob('*') if p.is_file() and p != OUT/'MANIFEST.json' and '_source_snapshot' not in p.parts and 'matplotlib_cache' not in p.parts]
    write(OUT/'MANIFEST.json',json.dumps([{'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],indent=2))
    print(json.dumps({'directory':str(OUT),'files':len(files),'demo_seconds':duration,'reports':'Phase2 2 pages; Phase3 4; final 12; slides 12 each; individual 1 each','sample_outputs':len(rows)},indent=2))


if __name__ == '__main__':
    main()
