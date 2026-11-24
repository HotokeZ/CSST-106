/* Edits stay in this browser until explicitly downloaded. */
(() => {
  'use strict';
  const panel=document.querySelector('#review-panel'), canvas=document.querySelector('#review-canvas'), ctx=canvas.getContext('2d');
  const list=document.querySelector('#review-list'), status=document.querySelector('#review-status'), mode=document.querySelector('#review-mode'), label=document.querySelector('#review-label');
  let original=null,items=[],history=[],actions=[],points=[],outlines=[],image=null,revision=0;
  const selected=()=>Array.from(list.selectedOptions).map(o=>o.value);
  function reset(){revision++;original=null;items=[];history=[];actions=[];points=[];outlines=[];image=null;panel.hidden=true;document.querySelector('#review-confirm').checked=false;document.querySelector('#quality-panel').hidden=true;}
  window.addEventListener('bigascheck:reset',reset);
  window.addEventListener('bigascheck:result',event=>{
    reset();original=event.detail;items=BigasReview.initial(original);const version=revision;
    document.querySelector('#quality-panel').hidden=false;
    document.querySelector('#quality-automatic').textContent='Automatic: whole/broken estimate only. Discoloration and impurities are not assessed by the installed model.';
    image=new Image();image.onload=()=>{if(version!==revision)return;canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;panel.hidden=false;render();};
    image.src='data:image/png;base64,'+original.original_png;
  });
  function render(){
    const ids=selected();list.replaceChildren();
    for(const i of items){const option=document.createElement('option');option.value=i.id;option.textContent=`${i.id}: ${i.label}, discoloration ${i.label==='impurity'?'n/a':i.discoloration||'unassessed'} (${i.reviewed?'traced':'box proposal'})`;option.selected=ids.includes(i.id);list.append(option);}
    ctx.clearRect(0,0,canvas.width,canvas.height);if(image)ctx.drawImage(image,0,0);
    function draw(p,color,text){if(!p.length)return;ctx.beginPath();p.forEach((v,j)=>j?ctx.lineTo(...v):ctx.moveTo(...v));if(p.length>2)ctx.closePath();ctx.strokeStyle=color;ctx.lineWidth=Math.max(1,canvas.width/500);ctx.stroke();if(text){ctx.fillStyle=color;ctx.font=`${Math.max(10,canvas.width/70)}px sans-serif`;ctx.fillText(text,p[0][0],Math.max(12,p[0][1]-3));}}
    for(const i of items)draw(i.points,ids.includes(i.id)?'#00b8ff':i.label==='whole'?'#34d399':i.label==='broken'?'#fb7185':'#e0a500',i.id);
    outlines.forEach(p=>draw(p,'#00b8ff','staged'));draw(points,'#00b8ff','drawing');
    const s=BigasReview.summary(items);document.querySelector('#review-counts').textContent=`Review: ${s.rice_candidates} rice candidates · ${s.whole} whole · ${s.broken} broken · ${s.impurities} impurities · ${s.unclassified} unclassified · broken ${s.broken_percentage==null?'—':s.broken_percentage.toFixed(1)+'%'}`;
    const q=BigasReview.quality(items,document.querySelector('#review-confirm').checked);
    const title={review_incomplete:'Review incomplete',visible_defects_reported:'Visible defects reported',broken_grains_present:'Broken grains present',no_reviewed_visible_defects:'No reviewed visible defects'};
    document.querySelector('#quality-review').textContent=`Manual quality: ${title[q.classification]}. Discolored grains: ${q.discolored_grains??'not assessed'}; discoloration unassessed: ${q.discoloration_unassessed}; marked impurities: ${q.impurities}.`;
    document.querySelector('#review-pending').textContent=`${outlines.length} completed outline(s), ${points.length} points in current outline. ${items.filter(i=>i.reviewed).length}/${items.length} grains traced.`;
    document.querySelector('#review-undo').disabled=!history.length;
  }
  list.addEventListener('change',()=>{points=[];outlines=[];render();});
  mode.addEventListener('change',()=>{points=[];outlines=[];render();});
  canvas.addEventListener('pointerdown',event=>{
    if(!original)return;const box=canvas.getBoundingClientRect();points.push([Math.min(canvas.width-1,Math.max(0,(event.clientX-box.left)*canvas.width/box.width)),Math.min(canvas.height-1,Math.max(0,(event.clientY-box.top)*canvas.height/box.height))]);render();
  });
  document.querySelector('#review-point-undo').onclick=()=>{points.pop();render();};
  document.querySelector('#review-clear-drawing').onclick=()=>{points=[];outlines=[];render();};
  document.querySelector('#review-finish-outline').onclick=()=>{try{outlines.push(BigasReview.polygon(points,canvas.width,canvas.height));points=[];status.textContent='Outline staged. For a split, trace the next grain, then apply.';render();}catch(e){status.textContent=e.message;}};
  document.querySelector('#review-apply').onclick=()=>{
    try{if(points.length)throw Error('Finish or clear the current outline first.');const ids=selected(),discoloration=document.querySelector('#review-discoloration').value;const next=BigasReview.apply(items,mode.value,ids,outlines,label.value,canvas.width,canvas.height,discoloration);history.push({items:BigasReview.clone(items),actions:BigasReview.clone(actions)});actions.push({operation:mode.value,selected_ids:ids,label:label.value,discoloration,outlines:BigasReview.clone(outlines)});items=next;points=[];outlines=[];document.querySelector('#review-confirm').checked=false;status.textContent='Correction applied. Automatic results above are unchanged.';render();}catch(e){status.textContent=e.message;}
  };
  document.querySelector('#review-undo').onclick=()=>{const previous=history.pop();if(!previous)return;items=previous.items;actions=previous.actions;points=[];outlines=[];document.querySelector('#review-confirm').checked=false;render();};
  document.querySelector('#review-reset').onclick=()=>{if(!original)return;items=BigasReview.initial(original);actions=[];history=[];points=[];outlines=[];document.querySelector('#review-confirm').checked=false;render();};
  document.querySelector('#review-confirm').onchange=render;
  document.querySelector('#review-download').onclick=()=>{if(!original)return;const {annotated_png,mask_png,original_png,...automatic}=original;download('bigascheck_review.json',JSON.stringify({version:1,automatic,reviewed_summary:BigasReview.summary(items),reviewed_quality:BigasReview.quality(items,document.querySelector('#review-confirm').checked),reviewed_grains:items,actions,coordinate_frame:original.preprocessing,counts_source:'manual_review',imageData:original_png},null,2),'application/json');};
  document.querySelector('#review-image').onclick=()=>{if(!original)return;if(points.length||outlines.length){status.textContent='Apply or clear staged outlines before downloading the corrected image.';return;}const a=document.createElement('a');a.download='bigascheck_manually_corrected.png';a.href=canvas.toDataURL('image/png');a.click();};
  document.querySelector('#review-resume').onchange=async event=>{
    const file=event.target.files[0],version=revision;
    try{if(!file||!original)return;if(file.size>50*1024*1024)throw Error('Review file is too large.');const data=JSON.parse(await file.text());if(version!==revision)return;
      if(data.version!==1 || data.counts_source!=='manual_review' || data.imageData!==original.original_png || !Array.isArray(data.reviewed_grains))throw Error('This review does not match the analyzed image/crop.');
      const ids=new Set();const restored=data.reviewed_grains.map(i=>{if(!i.id||ids.has(i.id)||!['whole','broken','unclassified','impurity'].includes(i.label)||!['none','present','unassessed'].includes(i.discoloration||'unassessed')||!Array.isArray(i.source_ids)||!['manual_outline','automatic_box'].includes(i.origin)||i.reviewed!==(i.origin==='manual_outline'))throw Error('Invalid saved grain.');ids.add(i.id);return {...i,discoloration:i.discoloration||'unassessed',points:BigasReview.polygon(i.points,canvas.width,canvas.height)};});
      history.push({items:BigasReview.clone(items),actions:BigasReview.clone(actions)});items=restored;actions=Array.isArray(data.actions)?data.actions:[];points=[];outlines=[];document.querySelector('#review-confirm').checked=false;status.textContent='Review restored. Check all outlines before training export.';render();
    }catch(e){status.textContent=e.message;}finally{event.target.value='';}
  };
  document.querySelector('#review-annotations').onclick=()=>{try{const data=BigasReview.annotation(items,canvas.width,canvas.height,original.original_png,document.querySelector('#review-group').value,document.querySelector('#review-split').value,document.querySelector('#review-confirm').checked);data.bigascheck.preprocessing=original.preprocessing;download('reviewed_rice.json',JSON.stringify(data,null,2),'application/json');status.textContent='Annotation downloaded with the processed image embedded. Save different photos with unique names.';}catch(e){status.textContent=e.message;}};
})();
