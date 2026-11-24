// DOM harness exercises editor wiring; it does not replace a visual browser test.
const test=require('node:test'), assert=require('node:assert/strict'), fs=require('node:fs'), vm=require('node:vm'), path=require('node:path');
const R=require('../static/review-core.js');
function editor(){
 const elements={};
 class Element{
  constructor(){this.children=[];this.handlers={};this.value='';this.checked=false;this.hidden=true;this.width=100;this.height=100;}
  addEventListener(type,fn){(this.handlers[type]??=[]).push(fn);}
  append(child){this.children.push(child);}
  replaceChildren(){this.children=[];}
  get selectedOptions(){return this.children.filter(i=>i.selected);}
  getContext(){return new Proxy({}, {get:()=>()=>{}});}
  getBoundingClientRect(){return {left:0,top:0,width:100,height:100};}
  toDataURL(){return 'data:image/png;base64,abc';}
  click(){}
 }
 const template=fs.readFileSync(path.join(__dirname,'../templates/index.html'),'utf8');
 for(const match of template.matchAll(/id="([^"]+)"/g))elements[match[1]]=new Element();
 const window=new EventTarget(), downloads=[];
 const context={window,document:{querySelector:s=>elements[s.slice(1)],createElement:()=>new Element()},
  BigasReview:R,Image:class{constructor(){this.naturalWidth=100;this.naturalHeight=100;}set src(value){this.onload?.();}},
  download:(name,text)=>downloads.push({name,data:JSON.parse(text)}),console};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/review.js'),'utf8'),context);
 function event(type,detail){const e=new Event(type);e.detail=detail;window.dispatchEvent(e);}
 async function fire(id,type='click',data={}){const el=elements[id];for(const fn of el.handlers[type]??[])await fn(data);if(el['on'+type])await el['on'+type](data);}
 const result={original_png:'abc',grains:[{grain_id:1,bbox:[2,2,20,10],prediction:'whole'},{grain_id:2,bbox:[20,2,20,10],prediction:'broken'}],summary:{detected:2},preprocessing:{width:100,height:100}};
 event('bigascheck:result',result);
 elements['review-mode'].value='merge';elements['review-label'].value='whole';elements['review-discoloration'].value='none';elements['review-split'].value='train';
 return {elements,downloads,event,fire,result};
}
test('UI merge, manual quality, export and undo preserve automatic counts',async()=>{
 const e=editor();assert.equal(e.elements['review-panel'].hidden,false);
 e.elements['review-list'].children.forEach(i=>i.selected=true);
 for(const [clientX,clientY] of [[2,2],[40,2],[40,12],[2,12]])await e.fire('review-canvas','pointerdown',{clientX,clientY});
 await e.fire('review-finish-outline');await e.fire('review-apply');
 assert.match(e.elements['review-counts'].textContent,/1 rice candidates/);assert.equal(e.result.summary.detected,2);
 e.elements['review-confirm'].checked=true;await e.fire('review-confirm','change');
 e.elements['review-group'].value='session-A';await e.fire('review-annotations');
 assert.equal(e.downloads.at(-1).data.shapes.length,1);assert.equal(e.downloads.at(-1).data.shapes[0].label,'whole');
 await e.fire('review-download');assert.equal(e.downloads.at(-1).data.reviewed_quality.classification,'no_reviewed_visible_defects');
 await e.fire('review-undo');assert.match(e.elements['review-counts'].textContent,/2 rice candidates/);assert.equal(e.elements['review-confirm'].checked,false);
});
test('UI reset clears stale review and blocks mismatched imports',async()=>{
 const e=editor();await e.fire('review-resume','change',{target:{files:[{size:20,text:async()=>JSON.stringify({version:1,counts_source:'manual_review',imageData:'different',reviewed_grains:[]})}],value:'file'}});
 assert.match(e.elements['review-status'].textContent,/does not match/);
 e.event('bigascheck:reset');assert.equal(e.elements['review-panel'].hidden,true);assert.equal(e.elements['quality-panel'].hidden,true);
});
