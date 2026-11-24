/* Pure review operations shared by the browser and software tests. */
(function (root) {
  'use strict';
  const clone = value => JSON.parse(JSON.stringify(value));
  function polygon(points, width, height) {
    if (!Array.isArray(points) || points.length < 3 || points.length > 1000) throw Error('Trace at least three points around the grain.');
    if (points.some(p => !Array.isArray(p) || p.length !== 2 || p.some(v => !Number.isFinite(v)) || p[0] < 0 || p[1] < 0 || p[0] >= width || p[1] >= height)) throw Error('Outline must stay inside the image.');
    let area = 0;
    for (let i=0;i<points.length;i++) {const a=points[i],b=points[(i+1)%points.length];area+=a[0]*b[1]-b[0]*a[1];}
    if (Math.abs(area)/2 < 4) throw Error('The outline is too small.');
    const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
    const on=(a,b,p)=>cross(a,b,p)===0 && p[0]>=Math.min(a[0],b[0]) && p[0]<=Math.max(a[0],b[0]) && p[1]>=Math.min(a[1],b[1]) && p[1]<=Math.max(a[1],b[1]);
    for(let i=0;i<points.length;i++) for(let j=i+1;j<points.length;j++) {
      if(j===i+1 || (i===0 && j===points.length-1)) continue;
      const a=points[i],b=points[(i+1)%points.length],c=points[j],d=points[(j+1)%points.length];
      if ((cross(a,b,c)*cross(a,b,d)<0 && cross(c,d,a)*cross(c,d,b)<0) || on(a,b,c)||on(a,b,d)||on(c,d,a)||on(c,d,b)) throw Error('Outline edges must not cross or touch.');
    }
    return clone(points);
  }
  function initial(result) {
    return result.grains.map(g=>{const [x,y,w,h]=g.bbox;return {id:String(g.grain_id),label:g.prediction||'unclassified',discoloration:'unassessed',points:[[x,y],[x+w-1,y],[x+w-1,y+h-1],[x,y+h-1]],reviewed:false,origin:'automatic_box',source_ids:[String(g.grain_id)]};});
  }
  function summary(items) {
    const whole=items.filter(i=>i.label==='whole').length,broken=items.filter(i=>i.label==='broken').length;
    const impurities=items.filter(i=>i.label==='impurity').length;
    const rice_candidates=items.length-impurities,unclassified=rice_candidates-whole-broken;
    return {detected:items.length,whole,broken,unclassified,impurities,rice_candidates,broken_percentage:rice_candidates && !unclassified ? 100*broken/rice_candidates:null};
  }
  function quality(items, confirmed=false) {
    const s=summary(items), rice=items.filter(i=>i.label!=='impurity');
    const discolored=rice.filter(i=>i.discoloration==='present').length;
    const unknown=rice.filter(i=>!['none','present'].includes(i.discoloration)).length;
    const complete=confirmed && items.length>0 && !s.unclassified && !unknown && items.every(i=>i.reviewed);
    return {classification:!complete?'review_incomplete':s.impurities||discolored?'visible_defects_reported':s.broken?'broken_grains_present':'no_reviewed_visible_defects',
      basis:'manual_review',review_complete:complete,whole:s.whole,broken:s.broken,impurities:s.impurities,
      discolored_grains:unknown && !discolored?null:discolored,discoloration_unassessed:unknown,
      broken_percentage_by_rice_count:s.broken_percentage,scope:'Visual inspection only; not an official grade or food-safety assessment.'};
  }
  function apply(items, operation, ids, outlines, label, width, height, discoloration='unassessed') {
    if (!['whole','broken','unclassified','impurity'].includes(label)) throw Error('Choose a valid label.');
    if (!['unassessed','none','present'].includes(discoloration)) throw Error('Choose a discoloration status.');
    if (!['replace','merge','split','add','delete','label','quality'].includes(operation)) throw Error('Unknown operation.');
    if(new Set(ids).size!==ids.length || ids.some(id=>!items.some(i=>i.id===id))) throw Error('Select existing grains.');
    if (['replace','split'].includes(operation) && ids.length!==1) throw Error('Select exactly one grain.');
    if (operation==='merge' && ids.length<2) throw Error('Select at least two fragments.');
    if (['delete','label','quality'].includes(operation) && !ids.length) throw Error('Select at least one object.');
    if(operation==='add' && ids.length) throw Error('Clear the selection before adding.');
    if(operation==='quality') return items.map(i=>ids.includes(i.id)?{...clone(i),discoloration:i.label==='impurity'?'unassessed':discoloration}:clone(i));
    if(operation==='label') return items.map(i=>ids.includes(i.id)?{...clone(i),label,discoloration}:clone(i));
    if(operation==='delete') return items.filter(i=>!ids.includes(i.id)).map(clone);
    if(operation==='split' ? outlines.length<2 : outlines.length!==1) throw Error(operation==='split'?'Trace each child grain; at least two are required.':'Trace one complete outline.');
    const originals=items.filter(i=>ids.includes(i.id));
    const source_ids=[...new Set(originals.flatMap(i=>i.source_ids))];
    const kept=items.filter(i=>!ids.includes(i.id)).map(clone);
    let serial=1;const occupied=new Set(items.map(i=>i.id));
    for(const points of outlines) {while(occupied.has('manual-'+serial))serial++;const id='manual-'+serial++;occupied.add(id);kept.push({id,label,discoloration,points:polygon(points,width,height),reviewed:true,origin:'manual_outline',source_ids});}
    return kept;
  }
  function annotation(items, width, height, imageData, group, split, confirmed) {
    if(!confirmed) throw Error('Confirm that every grain and outline was reviewed.');
    if(!items.length || items.some(i=>!i.reviewed || i.origin!=='manual_outline' || !['whole','broken','impurity'].includes(i.label) || (i.label!=='impurity' && !['none','present'].includes(i.discoloration)))) throw Error('Trace every grain/impurity and review its class and discoloration. Automatic boxes are not segmentation labels.');
    if(!group.trim()) throw Error('Enter a capture group shared by related photographs.');
    if(!['train','validation','test'].includes(split)) throw Error('Invalid partition.');
    return {version:'5.0.0',flags:{},shapes:items.map(i=>({label:i.discoloration==='present' && i.label!=='impurity'?'discolored_'+i.label:i.label,points:polygon(i.points,width,height),group_id:null,shape_type:'polygon',flags:{manually_reviewed:true,discoloration_reviewed:i.label!=='impurity'}})),imagePath:'reviewed_rice.png',imageData,imageHeight:height,imageWidth:width,
      bigascheck:{capture_group:group.trim(),split,coordinate_frame:'processed_image_or_crop',reviewed_complete:true,evaluation_status:'User-reviewed annotation; independence must be established from capture history.'}};
  }
  const api={clone,polygon,initial,summary,quality,apply,annotation};
  if(typeof module!=='undefined' && module.exports) module.exports=api;
  root.BigasReview=api;
})(typeof globalThis!=='undefined'?globalThis:this);
