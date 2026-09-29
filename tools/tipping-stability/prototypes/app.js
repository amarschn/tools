import { caseView, sectionScene, smallMultiples, svgMarkup, renderCanvas, renderBoard, fmt, escape } from './diagrams.js';

const $=(id)=>document.getElementById(id);
const query=new URLSearchParams(location.search);
let cases=[],current,view,board,assembly,threeError=null;
const state={case:query.get('case')||'slope',edge:query.get('edge'),force:query.get('force')||'all',study:query.get('view')||'all',anchors:query.get('anchors')==='1',arrowScale:query.get('scale')==='proportional'?'proportional':'schematic'};
const validStudies=['a','b','c','d','e','f'];
if(!validStudies.includes(state.study))state.study='all';
const scenes={};

function saveUrl() {
    const params=new URLSearchParams({case:state.case,edge:state.edge,view:state.study});
    if(state.force!=='all')params.set('force',state.force);
    if(state.anchors)params.set('anchors','1');
    if(state.arrowScale==='proportional')params.set('scale','proportional');
    history.replaceState(null,'',`${location.pathname}?${params}`);
}

function selectForce(id) {
    state.force=state.force===id?'all':id;
    $('force-select').value=state.force;
    render();
}

function render() {
    if(!current)return;
    view=caseView(current,state.edge);
    const options={anchors:state.anchors,selected:state.force,arrowScale:state.arrowScale};
    scenes.a=sectionScene(view,options);
    scenes.b=sectionScene(view,{...options,world:true});
    scenes.c=smallMultiples(view,options);
    scenes.d=sectionScene(view,{...options,moment:true});
    for(const id of ['a','c','d'])$('scene-'+id).innerHTML=svgMarkup(scenes[id],{title:document.querySelector(`[data-study="${id}"] h2`).textContent});
    renderCanvas($('scene-b').querySelector('canvas'),scenes.b);
    if(board){window.JXG.JSXGraph.freeBoard(board);board=null;}
    if($('scene-f').clientWidth) {
        try{board=renderBoard($('jsx-board'),scenes.a,selectForce);}
        catch(error){$('jsx-board').textContent=`Geometry board unavailable: ${error.message}`;}
    }
    if(assembly)assembly.update(view,options);
    const moment=scenes.d.momentForce;
    $('moment-note').textContent=`${moment.id}: ${fmt(moment.restoring_moment,1)} N·m in the restoring convention about ${view.edge.id}. ${Math.hypot(...moment.vector)<1e-7?'This force lies along the edge, so its projected tipping moment is zero.':'Lever arm refers to the in-plane force component.'}`;
    $('mass-value').textContent=`${fmt(view.e.mass,0)} kg`;
    $('height-value').textContent=`${fmt(view.e.center[2])} m`;
    $('margin-value').textContent=`${fmt(view.section.reaction[0],3)} m`;
    const status=$('case-status'),minimum=Math.min(...view.e.edges.map((edge)=>edge.distance));
    status.dataset.status=minimum<-1e-7?'outside':minimum<1e-7?'boundary':'inside';
    status.textContent=minimum<-1e-7?'Beyond tipping: required reaction is outside the support polygon.':minimum<1e-7?'At the tipping threshold.':'Required reaction is inside the support polygon.';
    const out=view.forces.filter((f)=>Math.abs(f.out_of_plane)>1e-7);
    const scaleNote=state.arrowScale==='schematic'?'Arrow lengths are schematic; read the force values for magnitudes.':'Arrow lengths are proportional to the displayed vector magnitude within each study. Small forces may be hard to see.';
    $('projection-note').textContent=(out.length?`Along-edge components for ${out.map((f)=>f.id).join(', ')} are outside the 2D section. Study C lists them; E shows the full vectors. `:'Every active force lies in this section. ')+scaleNote;
    document.querySelectorAll('.scale-copy').forEach((label)=>{label.textContent=state.arrowScale==='schematic'?'schematic arrow lengths':'proportional arrow lengths';});
    const vector=(v,places)=>`(${v.map((x)=>fmt(x,places)).join(', ')})`;
    $('force-data').innerHTML=view.forces.map((f)=>{
        const raw=current.result.free_body.forces.find((r)=>r.id===f.id);
        return `<tr><td>${escape(f.id)}</td><td>${vector(raw.vector,1)}</td><td>${vector(raw.point,3)}</td><td>${vector(f.vector,1)}</td><td>${fmt(f.out_of_plane,1)}</td></tr>`;
    }).join('');
    $('yaw-note').textContent=`Required ground yaw couple: ${fmt(current.result.free_body.contact_couple[2],2)} N·m about +z. It is listed separately from the arrows. Individual contact loads, traction and yaw capacity are outside this model.`;
    saveUrl();
    window.FbdStudies={state,view,scenes,get board(){return board;},get assembly(){return assembly;},threeError};
}

function changeCase(resetEdge=true) {
    current=cases.find((c)=>c.id===state.case)||cases[0];state.case=current.id;
    $('case-select').value=state.case;
    const e=current.result.equilibrium;
    if(resetEdge||!e.edges.some((edge)=>edge.id===state.edge))state.edge=e.governing_edge;
    $('edge-select').innerHTML=e.edges.map((edge)=>`<option value="${edge.id}">${escape(edge.label)}${edge.id===e.governing_edge?' · limiting':''}</option>`).join('');
    $('edge-select').value=state.edge;
    const forces=current.result.free_body.forces.filter((f)=>Math.hypot(...f.vector)>1e-7);
    if(!forces.some((f)=>f.id===state.force))state.force='all';
    $('force-select').innerHTML='<option value="all">All forces</option>'+forces.map((f)=>`<option value="${f.id}">${f.id} · ${escape(f.name)}</option>`).join('');
    $('force-select').value=state.force;
    $('case-description').textContent=current.description;
    render();
}

function focusStudy(id,scroll=true) {
    state.study=id;
    $('studies').classList.toggle('focus',id!=='all');
    document.querySelectorAll('[data-study]').forEach((card)=>{card.hidden=id!=='all'&&card.dataset.study!==id;});
    document.querySelectorAll('[data-expand]').forEach((button)=>{button.hidden=id!=='all';});
    $('show-all').hidden=id==='all';
    $('view-description').textContent=id==='all'?'Compare all six. Expand a study for a closer look.':`Study ${id.toUpperCase()} · Shared controls apply to this view.`;
    render();
    if(scroll)$('view-description').scrollIntoView({block:'start',behavior:'instant'});
}

$('case-select').addEventListener('change',(event)=>{state.case=event.target.value;changeCase();});
$('edge-select').addEventListener('change',(event)=>{state.edge=event.target.value;render();});
$('force-select').addEventListener('change',(event)=>{state.force=event.target.value;render();});
$('scale-select').value=state.arrowScale;
$('scale-select').addEventListener('change',(event)=>{state.arrowScale=event.target.value;render();});
$('anchor-guides').checked=state.anchors;
$('anchor-guides').addEventListener('change',(event)=>{state.anchors=event.target.checked;render();});
$('studies').addEventListener('click',(event)=>{
    const expand=event.target.closest('[data-expand]'),force=event.target.closest('[data-force]');
    if(expand)focusStudy(expand.dataset.expand);
    else if(force)selectForce(force.dataset.force);
});
$('studies').addEventListener('keydown',(event)=>{
    if((event.key==='Enter'||event.key===' ')&&event.target.matches('[data-force]')){event.preventDefault();selectForce(event.target.dataset.force);}
});
$('show-all').addEventListener('click',()=>focusStudy('all'));
$('settings-open').addEventListener('click',()=>$('settings-panel').showModal());
$('settings-close').addEventListener('click',()=>$('settings-panel').close());
$('theme-select').value=document.body.dataset.theme;
$('theme-select').addEventListener('change',(event)=>{
    document.body.dataset.theme=event.target.value;
    try{localStorage.setItem('tipping-fbd-theme',event.target.value);}catch(_){}
    render();
});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(document.body.dataset.theme==='system')render();});
$('copy-link').addEventListener('click',async()=>{
    try {await navigator.clipboard.writeText(location.href);$('copy-status').textContent='Link copied';}
    catch(_) {$('copy-status').textContent='Copy the URL from the address bar.';}
});
$('camera-left').addEventListener('click',()=>assembly?.rotate(-Math.PI/8));
$('camera-right').addEventListener('click',()=>assembly?.rotate(Math.PI/8));
$('camera-reset').addEventListener('click',()=>assembly?.reset());
$('board-in').addEventListener('click',()=>board?.zoomIn());
$('board-out').addEventListener('click',()=>board?.zoomOut());
$('board-reset').addEventListener('click',()=>board?.setBoundingBox([0,420,680,0],true));
let lastWidth=0,resizeFrame;
new ResizeObserver(([entry])=>{
    if(Math.abs(entry.contentRect.width-lastWidth)<1)return;
    lastWidth=entry.contentRect.width;cancelAnimationFrame(resizeFrame);
    resizeFrame=requestAnimationFrame(()=>render());
}).observe($('studies'));

try {
    const response=await fetch('cases.json');
    if(!response.ok)throw new Error(`Cases could not load (${response.status}).`);
    cases=(await response.json()).cases;
    $('case-select').innerHTML=cases.map((c)=>`<option value="${c.id}">${escape(c.title)}</option>`).join('');
    try{
        const {AssemblyView}=await import('./three-view.js');
        assembly=new AssemblyView($('three-scene'));
    }catch(error){
        threeError=error.message;
        const message=document.createElement('p');message.textContent=`3D view unavailable: ${error.message}`;$('three-scene').prepend(message);
    }
    changeCase(false);focusStudy(state.study,false);
    $('prototype-main').dataset.state='ready';
    $('loading-overlay').hidden=true;
}catch(error){
    $('loading-overlay').innerHTML=`<p>${escape(error.message)} Reload the page to try again.</p>`;
    $('prototype-main').dataset.state='error';
}
