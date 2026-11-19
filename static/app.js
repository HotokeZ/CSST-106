"use strict";
const form = document.querySelector('#analysis-form');
const input = document.querySelector('#image-input');
const zone = document.querySelector('#dropzone');
const error = document.querySelector('#error');
let result = null;
let showMask = false;
let selectedSample = null;
let samplePage = 1;
let sampleFilter = 'all';
let galleryRequest = 0;
let uploadPreviewUrl = null;
let previewVersion = 0;
let sourceRevision = 0;
function setUploadPreview(source, description = 'Selected rice photograph') {
  const image = document.querySelector('#upload-preview');
  const version = ++previewVersion;
  if (uploadPreviewUrl) { URL.revokeObjectURL(uploadPreviewUrl); uploadPreviewUrl = null; }
  image.onload = null; image.onerror = null;
  if (!source) {
    image.hidden = true; image.removeAttribute('src');
    zone.classList.remove('has-preview');
    return;
  }
  const url = typeof source === 'string' ? source : (uploadPreviewUrl = URL.createObjectURL(source));
  image.alt = description;
  image.onerror = () => {
    if (version !== previewVersion) return;
    image.hidden = true; zone.classList.remove('has-preview');
    if (uploadPreviewUrl) {URL.revokeObjectURL(uploadPreviewUrl); uploadPreviewUrl = null;}
    error.textContent = 'This image could not be previewed. Click the upload box to choose another photo.';
    error.hidden = false;
  };
  image.src = url; image.hidden = false;
  zone.classList.add('has-preview');
}
function resetResults() {
  sourceRevision++;
  result = null; showMask = false;
  for (const key of ['detected', 'whole', 'broken', 'percentage']) document.querySelector('#'+key).textContent = '—';
  document.querySelector('#result-status').textContent = 'AWAITING SAMPLE';
  document.querySelector('#result-image').hidden = true;
  document.querySelector('#empty-preview').hidden = false;
  document.querySelector('#results-detail').hidden = true;
  document.querySelector('#sample-reference').hidden = true;
  document.querySelector('#mask-toggle').disabled = true;
  document.querySelector('#mask-toggle').textContent = 'Show mask';
  document.querySelector('#processing-time').textContent = '';
  error.hidden = true;
}
function markSampleSelection() {
  for (const card of document.querySelectorAll('[data-sample-id]')) {
    card.setAttribute('aria-pressed', String(card.dataset.sampleId === selectedSample?.id));
  }
}
function showFile() {
  selectedSample = null; input.required = true;
  document.querySelector('#sample-selection').hidden = true;
  markSampleSelection(); resetResults();
  document.querySelector('#file-info').textContent = input.files[0]?.name || 'No image selected';
  setUploadPreview(input.files[0], input.files[0] ? 'Uploaded photograph: '+input.files[0].name : undefined);
}
function showReference(sample) {
  const reference = document.querySelector('#sample-reference');
  reference.hidden = !sample;
  if (!sample) return;
  reference.textContent = `Dataset reference: ${sample.expected_whole} whole + ${sample.expected_broken} broken. ${sample.note}`;
}
function selectSample(sample) {
  selectedSample = sample; input.value = ''; input.required = false;
  resetResults(); markSampleSelection();
  document.querySelector('#file-info').textContent = 'Test sample: '+sample.title;
  document.querySelector('#sample-selection').hidden = false;
  document.querySelector('#selected-sample-label').textContent = sample.title+' selected';
  setUploadPreview('/api/samples/'+encodeURIComponent(sample.id)+'/image', 'Selected test sample: '+sample.title);
  const image = document.querySelector('#result-image');
  image.src = '/api/samples/'+encodeURIComponent(sample.id)+'/image';
  image.hidden = false; image.alt = 'Selected held-out test sample: '+sample.title;
  document.querySelector('#empty-preview').hidden = true;
  document.querySelector('#result-status').textContent = 'READY TO ANALYZE';
  showReference(sample);
}
async function loadSamples() {
  const version = ++galleryRequest;
  const message = document.querySelector('#sample-message');
  message.textContent = 'Loading test samples...';
  document.querySelector('#sample-prev').disabled = true;
  document.querySelector('#sample-next').disabled = true;
  try {
    const response = await fetch(`/api/samples?label=${sampleFilter}&page=${samplePage}&page_size=6`);
    if (!(response.headers.get('content-type') || '').includes('application/json')) throw new Error('Restart the app to load the test sample gallery.');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Test samples are unavailable.');
    if (version !== galleryRequest) return;
    const grid = document.querySelector('#sample-grid'); grid.replaceChildren();
    for (const sample of data.items) {
      const card = document.createElement('button'); card.type = 'button'; card.className = 'sample-card';
      card.dataset.sampleId = sample.id;
      card.setAttribute('aria-pressed', String(sample.id === selectedSample?.id));
      card.setAttribute('aria-label', 'Use '+sample.title);
      const image = document.createElement('img'); image.loading = 'lazy'; image.alt = sample.title;
      image.src = '/api/samples/'+encodeURIComponent(sample.id)+'/image?thumbnail=1';
      const title = document.createElement('strong'); title.textContent = sample.title;
      const detail = document.createElement('span');
      detail.textContent = sample.kind === 'composite' ? '6 grains · composite' : '1 grain · test image';
      card.append(image, title, detail); card.addEventListener('click', () => selectSample(sample)); grid.append(card);
    }
    const pages = Math.max(1, Math.ceil(data.total/data.page_size));
    document.querySelector('#sample-page').textContent = `Page ${data.page} of ${pages}`;
    document.querySelector('#sample-total').textContent = data.total+' samples';
    document.querySelector('#sample-prev').disabled = data.page <= 1;
    document.querySelector('#sample-next').disabled = data.page >= pages;
    message.textContent = data.items.length ? 'Choose a sample, then click Analyze sample.' : 'No samples match this filter.';
  } catch (err) { if(version === galleryRequest) message.textContent = err.message; }
}
document.querySelector('#clear-sample').addEventListener('click', showFile);
document.querySelector('#sample-prev').addEventListener('click', () => {samplePage--; loadSamples();});
document.querySelector('#sample-next').addEventListener('click', () => {samplePage++; loadSamples();});
for (const button of document.querySelectorAll('[data-sample-filter]')) button.addEventListener('click', () => {
  sampleFilter = button.dataset.sampleFilter; samplePage = 1;
  for (const filter of document.querySelectorAll('[data-sample-filter]')) filter.setAttribute('aria-pressed', String(filter === button));
  loadSamples();
});
loadSamples();
input.addEventListener('change', showFile);
for (const event of ['dragenter', 'dragover']) zone.addEventListener(event, e => {e.preventDefault(); zone.classList.add('dragging');});
for (const event of ['dragleave', 'drop']) zone.addEventListener(event, e => {e.preventDefault(); zone.classList.remove('dragging');});
zone.addEventListener('drop', e => {if(e.dataTransfer.files.length) {input.files = e.dataTransfer.files; showFile();}});
function download(name, data, type) {
  const blob = new Blob([data], {type}); const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
form.addEventListener('submit', async e => {
  e.preventDefault(); error.hidden = true;
  const revision = sourceRevision;
  const button = document.querySelector('#analyze-button'); button.disabled = true; button.textContent = 'Analyzing sample…';
  try {
    if (!selectedSample && !input.files.length) throw new Error('Upload a photo or choose a test sample first.');
    if (input.files[0]?.size > 15 * 1024 * 1024) throw new Error('Choose an image smaller than 15 MB.');
    const body = new FormData(form);
    if (selectedSample) {body.delete('image'); body.set('sample_id', selectedSample.id);}
    const response = await fetch('/api/analyze', {method:'POST', body});
    const data = await response.json(); if(!response.ok) throw new Error(data.error || 'Analysis failed.');
    if (revision !== sourceRevision) return;
    result = data; showMask = false;
    showReference(result.sample);
    const s = result.summary;
    document.querySelector('#processing-time').textContent = Number.isFinite(s.processing_ms) ? s.processing_ms.toFixed(1)+' ms' : '';
    for (const key of ['detected', 'whole', 'broken']) document.querySelector('#'+key).textContent = s[key] ?? '—';
    document.querySelector('#percentage').textContent = s.broken_percentage == null ? '—' : s.broken_percentage.toFixed(1)+'%';
    document.querySelector('#result-status').textContent = s.classified ? 'CLASSIFIED' : 'DETECTED · UNCLASSIFIED';
    if (s.classified && s.classification_experimental) document.querySelector('#result-status').textContent = 'EXPERIMENTAL PREDICTIONS';
    document.querySelector('#empty-preview').hidden = true;
    const image = document.querySelector('#result-image'); image.src = 'data:image/png;base64,'+result.annotated_png; image.hidden = false;
    image.alt = 'Rice sample with detected grain regions and predictions';
    document.querySelector('#mask-toggle').disabled = false; document.querySelector('#mask-toggle').textContent = 'Show mask';
    document.querySelector('#results-detail').hidden = false;
    const warnings = document.querySelector('#warnings'); warnings.replaceChildren();
    for(const warning of result.warnings) {const p = document.createElement('p'); p.textContent = warning; warnings.append(p);}
    const rows = document.querySelector('#grain-rows'); rows.replaceChildren();
    for (const g of result.grains) {
      const row = document.createElement('tr');
      for (const v of [g.grain_id, g.prediction || 'unclassified', g.model_score == null ? '—' : (g.model_score*100).toFixed(1)+'%', g.features.area.toFixed(0), g.features.major_axis.toFixed(1), g.features.aspect_ratio.toFixed(2)]) {
        const cell = document.createElement('td'); cell.textContent = v; row.append(cell);
      } rows.append(row);
    }
  } catch(err) {if (revision === sourceRevision) {error.textContent = err.message; error.hidden = false;}}
  finally {button.disabled = false; button.innerHTML = 'Analyze sample <span>↗</span>';}
});
document.querySelector('#mask-toggle').addEventListener('click', e => {
  if(!result) return; showMask = !showMask;
  document.querySelector('#result-image').src = 'data:image/png;base64,'+(showMask ? result.mask_png : result.annotated_png);
  e.target.textContent = showMask ? 'Show annotations' : 'Show mask';
});
document.querySelector('#download-json').addEventListener('click', () => {
  if(!result) return; const {annotated_png, mask_png, ...report} = result;
  download('bigascheck_report.json', JSON.stringify(report, null, 2), 'application/json');
});
document.querySelector('#download-csv').addEventListener('click', () => {
  if(!result) return;
  const features = Object.keys(result.grains[0]?.features || {});
  const names = ['grain_id', 'prediction', 'model_score', ...features];
  const lines = [names.join(','), ...result.grains.map(g => [g.grain_id, g.prediction || 'unclassified',
                g.model_score ?? '', ...features.map(name => g.features[name])].join(','))];
  download('bigascheck_grains.csv', lines.join('\r\n'), 'text/csv');
});
document.querySelector('#download-image').addEventListener('click', () => {
  if(!result) return; const a = document.createElement('a'); a.href = 'data:image/png;base64,'+result.annotated_png; a.download = 'bigascheck_annotated.png'; a.click();
});
