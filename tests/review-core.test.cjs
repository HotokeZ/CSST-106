const test=require('node:test');
const assert=require('node:assert/strict');
const R=require('../static/review-core.js');
const input={grains:[{grain_id:1,bbox:[2,2,12,8],prediction:'whole'},{grain_id:2,bbox:[12,2,12,8],prediction:'broken'}]};
const outline=[[2,2],[24,2],[24,10],[2,10]];
test('broken-factor comparison uses inclusive bands without claiming a grade',()=>{assert.equal(R.gradeBand(5),'Premium');assert.equal(R.gradeBand(5.01),'Grade no. 1');assert.equal(R.gradeBand(15),'Grade no. 2');assert.equal(R.gradeBand(null),null);assert.match(R.gradeBand(46),/Above/);});
test('merge produces one reviewed object without changing automatic result',()=>{
 const initial=R.initial(input), before=R.clone(input);const merged=R.apply(initial,'merge',['1','2'],[outline],'whole',100,100);
 assert.equal(merged.length,1);assert.equal(merged[0].reviewed,true);assert.deepEqual(merged[0].source_ids,['1','2']);assert.deepEqual(input,before);assert.equal(initial.length,2);
});
test('split labels are separate instances and cannot be applied with one outline',()=>{
 const initial=R.initial(input);const child=[[2,2],[8,2],[8,8],[2,8]];
 assert.throws(()=>R.apply(initial,'split',['1'],[child],'whole',100,100));
 const split=R.apply(initial,'split',['1'],[child,[[9,2],[13,2],[13,8],[9,8]]],'whole',100,100);
 assert.equal(split.length,3);assert.equal(new Set(split.map(i=>i.id)).size,3);assert.deepEqual(R.summary(split),{detected:3,whole:2,broken:1,unclassified:0,impurities:0,rice_candidates:3,broken_percentage:100/3});
});
test('automatic boxes cannot be exported as instance masks; unknown labels withhold percentage',()=>{
 const initial=R.initial(input);assert.throws(()=>R.annotation(initial,100,100,'data','capture','train',true));
 const unknown=R.apply(initial,'label',['1'],[],'unclassified',100,100);assert.equal(R.summary(unknown).broken_percentage,null);
 const traced=R.apply([], 'add',[],[outline],'broken',100,100,'none');
 assert.throws(()=>R.annotation(traced,100,100,'data','','train',true));assert.throws(()=>R.annotation(traced,100,100,'data','capture','train',false));
 const exported=R.annotation(traced,100,100,'data','capture','validation',true);assert.equal(exported.shapes[0].shape_type,'polygon');assert.equal(exported.bigascheck.capture_group,'capture');
});
test('unassessed defects never imply clean quality; impurities are excluded from broken denominator',()=>{
 assert.equal(R.quality(R.initial(input),true).classification,'review_incomplete');
 let items=R.apply([], 'add',[],[outline],'whole',100,100,'none');
 assert.equal(R.quality(items,false).classification,'review_incomplete');
 assert.equal(R.quality(items,true).classification,'no_reviewed_visible_defects');
 items=R.apply(items,'add',[],[outline],'impurity',100,100);
 assert.equal(R.summary(items).rice_candidates,1);assert.equal(R.summary(items).impurities,1);assert.equal(R.summary(items).broken_percentage,0);
 assert.equal(R.quality(items,true).classification,'visible_defects_reported');
});
test('discoloration keeps whole/broken identity in the training export',()=>{
 const items=R.apply([], 'add',[],[outline],'whole',100,100,'present');
 assert.equal(R.quality(items,true).discolored_grains,1);
 const exported=R.annotation(items,100,100,'data','group','train',true);
 assert.equal(exported.shapes[0].label,'discolored_whole');
 const unknown=R.apply(items,'quality',[items[0].id],[],'whole',100,100,'unassessed');
 assert.equal(R.quality(unknown,true).classification,'review_incomplete');
 assert.throws(()=>R.annotation(unknown,100,100,'data','group','train',true));
});
test('reject invalid geometry, stale selections and duplicate selections',()=>{
 assert.throws(()=>R.polygon([[0,0],[10,10],[0,10],[10,0]],100,100));assert.throws(()=>R.polygon([[0,0],[Infinity,5],[5,10]],100,100));
 assert.throws(()=>R.apply(R.initial(input),'delete',['missing'],[],'whole',100,100));assert.throws(()=>R.apply(R.initial(input),'merge',['1','1'],[outline],'whole',100,100));
});
