/* Local crop editor. The original upload stays intact; the API crops before resizing. */
(() => {
  'use strict';
  const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
  const full = () => ({x:0, y:0, width:1, height:1});
  function normalize(rect) {
    const x = clamp(rect.x, 0, .99999), y = clamp(rect.y, 0, .99999);
    return {x, y, width:clamp(rect.width, .00001, 1-x), height:clamp(rect.height, .00001, 1-y)};
  }
  function fromPoints(a, b) {
    return normalize({x:Math.min(a.x,b.x), y:Math.min(a.y,b.y), width:Math.abs(a.x-b.x), height:Math.abs(a.y-b.y)});
  }
  function move(rect, dx, dy) {
    return {...rect, x:clamp(rect.x+dx,0,1-rect.width), y:clamp(rect.y+dy,0,1-rect.height)};
  }
  function pixels(rect, width, height) {
    const left = Math.floor(rect.x*width), top = Math.floor(rect.y*height);
    return {x:left, y:top, width:Math.min(width,Math.ceil((rect.x+rect.width)*width))-left,
            height:Math.min(height,Math.ceil((rect.y+rect.height)*height))-top};
  }
  class Editor {
    constructor(onApply) {
      this.dialog = document.querySelector('#crop-dialog');
      this.canvas = document.querySelector('#crop-canvas');
      this.fields = Object.fromEntries(['x','y','width','height'].map(k => [k,document.querySelector('#crop-'+k)]));
      this.onApply = onApply; this.generation = 0; this.file = null; this.image = null;
      this.rect = full(); this.forceDraw = false;
      for (const id of ['crop-close','crop-cancel']) document.querySelector('#'+id).addEventListener('click', () => this.dialog.close());
      document.querySelector('#crop-all').addEventListener('click', () => {this.rect=full(); this.forceDraw=false; this.render();});
      document.querySelector('#crop-redraw').addEventListener('click', () => {
        this.forceDraw=true; this.canvas.style.cursor='crosshair';
        document.querySelector('#crop-size').textContent='Drag across the photo to draw a new selection';
      });
      for (const field of Object.values(this.fields)) field.addEventListener('change', () => {
        const values = Object.fromEntries(Object.entries(this.fields).map(([k,e]) => [k,Number(e.value)/100]));
        if (Object.values(values).some(v => !Number.isFinite(v))) return;
        this.rect=normalize(values); this.render();
      });
      this.canvas.addEventListener('pointerdown', e => this.pointerDown(e));
      this.canvas.addEventListener('pointermove', e => this.pointerMove(e));
      for (const event of ['pointerup','pointercancel','lostpointercapture']) this.canvas.addEventListener(event, () => {
        this.drag=null; this.forceDraw=false; this.canvas.style.cursor='crosshair';
      });
      this.dialog.addEventListener('close', () => {this.drag=null; this.generation++;});
      document.querySelector('#crop-apply').addEventListener('click', () => this.apply());
    }
    setSource(file) {
      this.generation++; this.file=file; this.image=null; this.drag=null;
      if (this.dialog.open) this.dialog.close();
    }
    async open(selection) {
      const generation=++this.generation, file=this.file;
      if (!file) return;
      if (file.size>15*1024*1024) throw new Error('Choose an image smaller than 15 MB.');
      if (!this.image) {
        const url=URL.createObjectURL(file);
        try {
          const image=await new Promise((resolve,reject) => {
            const im=new Image(); im.onload=()=>resolve(im);
            im.onerror=()=>reject(new Error('This photo could not be opened for cropping. Try JPG, PNG or WEBP.'));
            im.src=url;
          });
          if (generation!==this.generation) return;
          if (image.naturalWidth*image.naturalHeight>20000000) throw new Error('Use a photograph with at most 20 megapixels.');
          this.image=image;
        } finally {URL.revokeObjectURL(url);}
      }
      if (generation!==this.generation) return;
      this.rect=selection ? normalize({...selection}) : full(); this.forceDraw=false;
      document.querySelector('#crop-error').hidden=true;
      this.dialog.showModal();
      const scale=Math.min(800/this.image.naturalWidth,Math.max(180,Math.min(540,window.innerHeight*.48))/this.image.naturalHeight,
                           Math.max(160,this.dialog.clientWidth-48)/this.image.naturalWidth,1);
      this.canvas.width=Math.max(1,Math.round(this.image.naturalWidth*scale));
      this.canvas.height=Math.max(1,Math.round(this.image.naturalHeight*scale));
      this.render();
    }
    point(event) {
      const box=this.canvas.getBoundingClientRect();
      return {x:clamp((event.clientX-box.left)/box.width,0,1), y:clamp((event.clientY-box.top)/box.height,0,1)};
    }
    corners() {
      const r=this.rect;
      return [{x:r.x,y:r.y},{x:r.x+r.width,y:r.y},{x:r.x+r.width,y:r.y+r.height},{x:r.x,y:r.y+r.height}];
    }
    pointerDown(event) {
      if (!this.image || !event.isPrimary || event.button!==0) return;
      event.preventDefault();
      const p=this.point(event), box=this.canvas.getBoundingClientRect(), corners=this.corners();
      const corner=this.forceDraw ? -1 : corners.findIndex(c => Math.hypot((p.x-c.x)*box.width,(p.y-c.y)*box.height)<12);
      const r=this.rect, isFull=r.width>.999 && r.height>.999;
      const inside=p.x>=r.x && p.x<=r.x+r.width && p.y>=r.y && p.y<=r.y+r.height;
      this.drag={start:p, rect:{...r}, mode:corner>=0?'resize':inside&&!isFull&&!this.forceDraw?'move':'draw',
                 opposite:corner>=0?corners[(corner+2)%4]:null};
      this.canvas.setPointerCapture(event.pointerId);
    }
    pointerMove(event) {
      if (!this.drag) return;
      event.preventDefault(); const p=this.point(event), d=this.drag;
      this.rect=d.mode==='move' ? move(d.rect,p.x-d.start.x,p.y-d.start.y) : fromPoints(d.mode==='resize'?d.opposite:d.start,p);
      this.render();
    }
    render() {
      if (!this.image) return;
      const ctx=this.canvas.getContext('2d'), w=this.canvas.width, h=this.canvas.height, r=this.rect;
      ctx.clearRect(0,0,w,h); ctx.drawImage(this.image,0,0,w,h);
      ctx.fillStyle='rgba(12,27,18,.58)';ctx.fillRect(0,0,w,h);
      const source=pixels(r,this.image.naturalWidth,this.image.naturalHeight);
      ctx.drawImage(this.image,source.x,source.y,source.width,source.height,r.x*w,r.y*h,r.width*w,r.height*h);
      ctx.strokeStyle='#edf8d7';ctx.lineWidth=2;ctx.strokeRect(r.x*w,r.y*h,r.width*w,r.height*h);
      ctx.strokeStyle='rgba(255,255,255,.45)';ctx.lineWidth=1;
      for (const fraction of [1/3,2/3]) {
        ctx.beginPath();ctx.moveTo((r.x+r.width*fraction)*w,r.y*h);ctx.lineTo((r.x+r.width*fraction)*w,(r.y+r.height)*h);ctx.stroke();
        ctx.beginPath();ctx.moveTo(r.x*w,(r.y+r.height*fraction)*h);ctx.lineTo((r.x+r.width)*w,(r.y+r.height*fraction)*h);ctx.stroke();
      }
      ctx.fillStyle='#fff';for (const c of this.corners()) ctx.fillRect(c.x*w-4,c.y*h-4,8,8);
      for (const [key,field] of Object.entries(this.fields)) field.value=(r[key]*100).toFixed(1);
      const small=source.width<8||source.height<8;
      document.querySelector('#crop-size').textContent=`${source.width} × ${source.height} px${small?' · Choose a larger area':''}`;
      document.querySelector('#crop-apply').disabled=small;
    }
    async apply() {
      const generation=this.generation, rect={...this.rect}, source=pixels(rect,this.image.naturalWidth,this.image.naturalHeight);
      const button=document.querySelector('#crop-apply'); button.disabled=true;
      try {
        if (source.width<8||source.height<8) throw new Error('Choose an area at least 8 pixels wide and high.');
        const canvas=document.createElement('canvas'), scale=Math.min(1200/source.width,1200/source.height,1);
        canvas.width=Math.max(1,Math.round(source.width*scale)); canvas.height=Math.max(1,Math.round(source.height*scale));
        canvas.getContext('2d').drawImage(this.image,source.x,source.y,source.width,source.height,0,0,canvas.width,canvas.height);
        const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
        if (!blob) throw new Error('Could not create the crop preview. Please try again.');
        if (generation!==this.generation) return;
        await this.onApply(rect,blob,source);
        this.dialog.close();
      } catch (error) {
        if (generation!==this.generation) return;
        document.querySelector('#crop-error').textContent=error.message; document.querySelector('#crop-error').hidden=false;
      } finally {button.disabled=false;}
    }
  }
  const api={clamp,full,normalize,fromPoints,move,pixels,Editor};
  if (typeof module!=='undefined') module.exports=api;
  if (typeof window!=='undefined') window.BigasCrop=api;
})();
