import {palette, fmt} from './diagrams.js';

const $ = (id) => document.getElementById(id);
const query = new URLSearchParams(location.search);
const DEFAULTS = {height:.85, angle:165, force:300, crowded:false, auto:true, construction:true};
const bounded = (value, fallback, min, max) => {
    const number = value === null ? NaN : Number(value);
    return Number.isFinite(number) ? Math.max(min, Math.min(max, number)) : fallback;
};
const state = {
    height:bounded(query.get('height'), DEFAULTS.height, .15, 1.2),
    angle:bounded(query.get('angle'), DEFAULTS.angle, 0, 360),
    force:bounded(query.get('force'), DEFAULTS.force, 25, 600),
    crowded:query.get('crowded') === '1',
    auto:query.get('auto') !== '0',
    construction:query.get('construction') !== '0',
};
const MODEL = {mass:100, track:.8, wheelbase:1.2, center:[0,0,.6]};
const MAST_U = MODEL.track / 2;
const HANDLE_RADIUS = .38;
const ARROW_LENGTH = .27;
let board, application, direction, forceTip, pivot, foot, arm, primaryArrow, reactionPoint;
let labeledObjects = [], forceArrows = [];
let result = null, revision = 0, solvedRevision = -1, workerReady = false, busy = false, timer;
let programmaticMove = false;
const worker = new Worker(new URL('./jsxgraph-solver.worker.js', import.meta.url));

function saveUrl() {
    const parameters = new URLSearchParams({
        height:state.height.toFixed(4), angle:state.angle.toFixed(4), force:String(state.force),
        crowded:state.crowded?'1':'0', auto:state.auto?'1':'0', construction:state.construction?'1':'0',
    });
    history.replaceState(null, '', location.pathname + '?' + parameters);
}

function syncControls() {
    $('load-height').value = state.height;
    $('load-angle').value = state.angle;
    $('load-force').value = state.force;
    $('height-value').textContent = fmt(state.height,2) + ' m';
    $('angle-value').textContent = fmt(state.angle,1) + '°';
    $('force-value').textContent = fmt(state.force,0) + ' N';
    $('auto-labels').checked = state.auto;
    $('crowded-loads').checked = state.crowded;
    $('show-construction').checked = state.construction;
}

function section() { return result?.free_body.sections.E3; }
function forceById(id) { return section()?.forces.find((force) => force.id === id); }
function currentResult() { return solvedRevision === revision && !!result; }
function updateArm() {
    if (pivot && foot) $('arm-value').textContent = fmt(pivot.Dist(foot),3) + ' m';
}

function markPending() {
    solvedRevision = -1;
    $('moment-value').textContent = '…';
    $('reaction-value').textContent = '…';
    $('moment-kind').textContent = 'Updating…';
    $('force-table').replaceChildren();
    $('solve-status').dataset.status = 'pending';
    $('solve-status').textContent = 'Updating forces and reactions…';
    $('lab-main').dataset.solveState = 'pending';
}

function physicalInputs() {
    const angle = state.angle * Math.PI / 180;
    // Input-coordinate conversion only: +u points toward -y at the left edge.
    const forces = [{
        name:'Draggable force',
        vector:[0, -state.force * Math.cos(angle), state.force * Math.sin(angle)],
        point:[0, 0, state.height],
    }];
    if (state.crowded) {
        const otherAngle = 175 * Math.PI / 180;
        forces.push({name:'Crowded force', vector:[0,-160*Math.cos(otherAngle),160*Math.sin(otherAngle)], point:[...MODEL.center]});
    }
    return {
        contacts:[[-.5*MODEL.wheelbase,-.5*MODEL.track],[.5*MODEL.wheelbase,-.5*MODEL.track],[.5*MODEL.wheelbase,.5*MODEL.track],[-.5*MODEL.wheelbase,.5*MODEL.track]],
        mass:MODEL.mass, center_of_mass:MODEL.center,
        acceleration:state.crowded?[0,-.8]:[0,0], forces,
    };
}

function requestSolve() {
    if (!workerReady || busy || currentResult()) return;
    busy = true;
    worker.postMessage({type:'solve', revision, inputs:physicalInputs()});
}

function changed() {
    revision++;
    markPending();
    syncControls();
    saveUrl();
    board?.update();
    updateArm();
    clearTimeout(timer);
    timer = setTimeout(requestSolve, 80);
}

function syncFromGeometry(source) {
    if (programmaticMove) return;
    state.height = Math.max(.15, Math.min(1.2, application.Y()));
    if(source==='application') {
        // Keep the direction's relative circle position when its center moves.
        direction.setGliderPosition(state.angle/360);
    } else {
        state.angle = (Math.atan2(direction.Y()-application.Y(), direction.X()-application.X())*180/Math.PI+360)%360;
    }
    changed();
}

function moveHandles() {
    if (!board) return;
    programmaticMove = true;
    application.moveTo([MAST_U, state.height]);
    board.update();
    const angle = state.angle*Math.PI/180;
    direction.moveTo([MAST_U+HANDLE_RADIUS*Math.cos(angle), state.height+HANDLE_RADIUS*Math.sin(angle)]);
    board.update();
    programmaticMove = false;
    updateArm();
}

function fitBoard() {
    // Equal horizontal and vertical scales on wide and narrow screens.
    const box = $('lab-board').getBoundingClientRect();
    const reaction = currentResult()?section().reaction[0]:MAST_U;
    const left = Math.min(-.4,reaction-ARROW_LENGTH-.12);
    const right = Math.max(1.22,reaction+ARROW_LENGTH+.12);
    const centerX = (left+right)/2;
    const spanX = Math.max(right-left,1.65,2.1*box.width/box.height);
    const spanY = spanX*box.height/box.width;
    board.setBoundingBox([centerX-spanX/2,.62+spanY/2,centerX+spanX/2,.62-spanY/2], true);
}

function buildBoard() {
    if (board) window.JXG.JSXGraph.freeBoard(board);
    const colors = palette();
    board = window.JXG.JSXGraph.initBoard('lab-board', {
        boundingbox:[-.8,1.7,1.6,-.5], keepaspectratio:true, axis:false,
        showCopyright:false, showNavigation:false, showInfobox:false, renderer:'svg',
        pan:{enabled:true,needShift:true}, zoom:{enabled:true,wheel:false},
        resize:{enabled:false}, keyboard:{enabled:false},
    });
    labeledObjects = []; forceArrows = [];
    const base = {fixed:true,highlight:false,strokeColor:colors.ink,fillColor:colors.paper,strokeWidth:1.5};
    const hiddenPoint = (coordinates) => board.create('point', coordinates, {visible:false,fixed:true,name:''});
    const labelStyle = (offset=[10,12]) => ({
        autoPosition:state.auto, autoPositionMinDistance:14, autoPositionMaxDistance:46,
        offset, fontSize:14, strokeColor:colors.ink, display:'internal',
        cssStyle:'font-family:Helvetica Neue,Arial,sans-serif;font-weight:600;',
    });
    const registerLabel = (object, offset=[10,12]) => {
        labeledObjects.push({object,offset});
        return object;
    };
    board.suspendUpdate();
    board.create('polygon', [[0,0],[MODEL.track,0],[MODEL.track,1.26],[0,1.26]], {
        ...base, fillColor:colors.fill, fillOpacity:.7, vertices:{visible:false},
        borders:{strokeColor:colors.soft,strokeWidth:1,highlight:false,ignoreForLabelAutoposition:true},
        hasInnerPoints:false, ignoreForLabelAutoposition:true,
    });
    board.create('segment', [[-.2,0],[1,0]], {...base,strokeColor:colors.soft,ignoreForLabelAutoposition:true});
    board.create('segment', [[0,0],[MODEL.track,0]], {...base,strokeWidth:2.5});
    pivot = registerLabel(board.create('point', [0,0], {...base,name:'edge',size:3,face:'o',fillColor:colors.ink,label:labelStyle([-36,-17])}),[-36,-17]);
    const massCenter = registerLabel(board.create('point', [MAST_U,MODEL.center[2]], {
        ...base,name:'G',size:5,face:'+',label:{...labelStyle([12,-18]),visible:()=>Math.abs(state.height-MODEL.center[2])>1e-8},
    }),[12,-18]);
    const mast = board.create('segment', [[MAST_U,.15],[MAST_U,1.2]], {
        ...base,strokeColor:colors.soft,dash:2,strokeWidth:1,ignoreForLabelAutoposition:true,
    });
    application = registerLabel(board.create('glider', [MAST_U,state.height,mast], {
        ...base,fixed:false,name:'A',size:6,face:'o',highlight:true,
        highlightStrokeColor:colors.ink,highlightFillColor:colors.fill,
        label:labelStyle([12,16]), layer:9, precision:{mouse:14,touch:24},
    }),[12,16]);
    application.label.setText(() => Math.abs(application.Y()-MODEL.center[2])<1e-8?'A / G':'A');
    const ring = board.create('circle', [application,HANDLE_RADIUS], {
        ...base,strokeColor:colors.soft,strokeWidth:1,dash:2,fillColor:'none',ignoreForLabelAutoposition:true,
    });
    const initialAngle = state.angle*Math.PI/180;
    direction = board.create('glider', [MAST_U+HANDLE_RADIUS*Math.cos(initialAngle),state.height+HANDLE_RADIUS*Math.sin(initialAngle),ring], {
        ...base,fixed:false,name:'',withLabel:false,size:5,face:'[]',highlight:true,
        highlightStrokeColor:colors.ink,highlightFillColor:colors.fill,layer:9,precision:{mouse:14,touch:24},
    });
    const unit = () => {
        const dx=direction.X()-application.X(),dy=direction.Y()-application.Y(),length=Math.hypot(dx,dy);
        return [dx/length,dy/length];
    };
    forceTip = hiddenPoint([()=>application.X()+ARROW_LENGTH*unit()[0],()=>application.Y()+ARROW_LENGTH*unit()[1]]);
    primaryArrow = registerLabel(board.create('arrow', [application,forceTip], {
        ...base,name:'P₁',withLabel:true,strokeWidth:2.5,lastArrow:{type:2,size:5},label:{...labelStyle([-14,18]),position:'last'},
    }),[-14,18]);
    const actionLine = board.create('line', [application,forceTip], {
        ...base,strokeColor:colors.muted,strokeWidth:1,dash:2,visible:()=>state.construction,ignoreForLabelAutoposition:true,
    });
    foot = board.create('orthogonalprojection', [pivot,actionLine], {
        ...base,name:'',size:2,visible:()=>state.construction && !!foot && pivot.Dist(foot)>1e-7,withLabel:false,
    });
    arm = board.create('segment', [pivot,foot], {...base,strokeWidth:2,visible:()=>state.construction});
    const armLabel = board.create('smartlabel', [arm], {
        fontSize:12,digits:3,measure:'length',prefix:'d = ',unit:' m',baseUnit:'m',strokeColor:colors.ink,
        useMathJax:false,display:'html',orientation:'none',cssClass:'lab-measure',highlightCssClass:'lab-measure',
        visibleThreshold:.7,
    });
    // Smartlabel's horizontal mode otherwise hides segments shorter than 1.5
    // user units. Our geometry is in meters, so apply a screen-length limit.
    armLabel.setAttribute({visible:()=>state.construction && pivot.Dist(foot)*board.unitX>55});
    reactionPoint = registerLabel(board.create('point', [()=>section()?.reaction[0]??0,0], {
        ...base,name:'R',size:4,face:'<>',visible:currentResult,label:labelStyle([12,-20]),
        strokeColor:()=>currentResult() && section().reaction[0]<0?colors.danger:colors.ink,
    }),[12,-20]);
    for (const id of ['W','I','P2','N','T']) {
        const visible = () => currentResult() && !!forceById(id) && Math.hypot(...forceById(id).vector)>1e-7;
        const anchor = id==='W'||id==='I'||id==='P2'?massCenter:reactionPoint;
        const end = hiddenPoint([
            () => {const force=forceById(id),v=force?.vector||[0,-1];return anchor.X()+ARROW_LENGTH*v[0]/(Math.hypot(...v)||1);},
            () => {const force=forceById(id),v=force?.vector||[0,-1];return anchor.Y()+ARROW_LENGTH*v[1]/(Math.hypot(...v)||1);},
        ]);
        const reaction = id==='N'||id==='T';
        const start = reaction?hiddenPoint([()=>2*anchor.X()-end.X(),()=>2*anchor.Y()-end.Y()]):anchor;
        const finish = reaction?anchor:end;
        const arrow = registerLabel(board.create('arrow', [start,finish], {
            ...base,name:id==='P2'?'P₂':id,withLabel:true,visible,strokeWidth:2,dash:id==='I'?2:0,
            lastArrow:{type:2,size:5},label:{...labelStyle([10,12]),position:reaction?'first':'last'},
        }));
        forceArrows.push({id,arrow,anchor,reaction});
    }
    board.create('arrow', [[.98,-.3],[1.13,-.3]], {...base,strokeColor:colors.muted,strokeWidth:1});
    board.create('arrow', [[.98,-.3],[.98,-.15]], {...base,strokeColor:colors.muted,strokeWidth:1});
    board.create('text', [1.16,-.3,'u'], {...base,strokeColor:colors.muted,fontSize:12});
    board.create('text', [.98,-.11,'z'], {...base,strokeColor:colors.muted,fontSize:12});
    board.unsuspendUpdate();
    application.on('drag', () => syncFromGeometry('application'));
    direction.on('drag', () => syncFromGeometry('direction'));
    board.on('update', updateArm);
    fitBoard();
    updateArm();
}

function showResult() {
    const selected = forceById('P1');
    $('moment-value').textContent = fmt(selected.restoring_moment,1) + ' N·m';
    $('moment-kind').textContent = Math.abs(selected.restoring_moment)<1e-7?'Zero moment':selected.restoring_moment>0?'Restoring':'Tipping';
    $('reaction-value').textContent = fmt(section().reaction[0],3) + ' m';
    const equilibrium = result.equilibrium;
    $('solve-status').dataset.status = equilibrium.status;
    $('solve-status').textContent = equilibrium.status==='beyond'?
        'Beyond tipping: the required ground reaction is outside the footprint.':
        equilibrium.status==='threshold'?'At the tipping threshold.':'Required ground reaction is inside the footprint.';
    $('force-table').innerHTML = section().forces.filter((force)=>Math.hypot(...force.vector)>1e-7).map((force)=>
        '<tr><td>'+force.id+'</td>'+[...force.vector,...force.point,force.restoring_moment].map((value,index)=>'<td>'+fmt(value,index===2||index===3?3:1)+'</td>').join('')+'</tr>'
    ).join('');
    $('lab-main').dataset.solveState = 'ready';
    board.update();
    updateArm();
}

function fail(message) {
    solvedRevision=-1;
    $('lab-main').dataset.solveState='error';
    $('moment-value').textContent='Unavailable';
    $('reaction-value').textContent='Unavailable';
    $('moment-kind').textContent='Calculation unavailable';
    $('solve-status').dataset.status='error';
    $('solve-status').textContent=message;
    if($('lab-main').dataset.state!=='ready') {
        $('lab-main').dataset.state='error';
        $('loading-message').textContent='Could not start the experiment. '+message+' Reload to retry.';
    }
    board?.update();
}

const bootTimeout=setTimeout(()=>fail('The calculation engine did not finish loading.'),90000);
worker.onmessage=({data})=>{
    if(data.type==='ready') {
        workerReady=true; requestSolve();
    } else if(data.type==='result'||data.type==='error') {
        busy=false;
        if(data.revision!==revision) {requestSolve();return;}
        clearTimeout(bootTimeout);
        if(data.type==='error') {fail(data.message);return;}
        result=data.result; solvedRevision=data.revision;
        showResult();
        $('lab-main').dataset.state='ready';
        $('loading-overlay').hidden=true;
    } else if(data.type==='fatal') {
        clearTimeout(bootTimeout); fail(data.message);
    }
};
worker.onerror=(event)=>{clearTimeout(bootTimeout);fail(event.message||'The calculation worker stopped.');};

for(const [id,key] of [['load-height','height'],['load-angle','angle'],['load-force','force']]) {
    $(id).addEventListener('input',(event)=>{state[key]=Number(event.target.value);moveHandles();changed();});
}
$('crowded-loads').addEventListener('change',(event)=>{state.crowded=event.target.checked;changed();});
$('auto-labels').addEventListener('change',(event)=>{
    state.auto=event.target.checked;
    for(const {object,offset} of labeledObjects)object.label?.setAttribute({autoPosition:state.auto,offset:[...offset]});
    board.fullUpdate();saveUrl();
});
$('show-construction').addEventListener('change',(event)=>{state.construction=event.target.checked;board.update();saveUrl();});
$('preset-reset').addEventListener('click',()=>{Object.assign(state,DEFAULTS);syncControls();buildBoard();changed();});
$('preset-crowded').addEventListener('click',()=>{Object.assign(state,{height:.6,angle:190,force:300,crowded:true});moveHandles();changed();});
$('preset-through').addEventListener('click',()=>{
    state.angle=(Math.atan2(-state.height,-MAST_U)*180/Math.PI+360)%360;
    moveHandles();changed();
});
$('zoom-in').addEventListener('click',()=>board.zoomIn());
$('zoom-out').addEventListener('click',()=>board.zoomOut());
$('fit-board').addEventListener('click',fitBoard);
$('settings-open').addEventListener('click',()=>$('settings-panel').showModal());
$('settings-close').addEventListener('click',()=>$('settings-panel').close());
$('theme-select').value=document.body.dataset.theme;
$('theme-select').addEventListener('change',(event)=>{
    document.body.dataset.theme=event.target.value;
    try{localStorage.setItem('tipping-fbd-theme',event.target.value);}catch(_){}
    buildBoard();
});
matchMedia('(prefers-color-scheme:dark)').addEventListener('change',()=>{if(document.body.dataset.theme==='system')buildBoard();});
$('copy-link').addEventListener('click',async()=>{
    saveUrl();
    try{await navigator.clipboard.writeText(location.href);$('copy-status').textContent='Link copied';}
    catch(_){$('copy-status').textContent='Copy the URL from the address bar.';}
});
let resizeTimer,lastWidth=0;
new ResizeObserver(([entry])=>{
    if(Math.abs(entry.contentRect.width-lastWidth)<1)return;
    lastWidth=entry.contentRect.width;
    clearTimeout(resizeTimer);
    resizeTimer=setTimeout(()=>{if(board){board.resizeContainer($('lab-board').clientWidth,$('lab-board').clientHeight,true);fitBoard();}},50);
}).observe($('lab-board'));
try {
    syncControls(); buildBoard(); saveUrl();
} catch(error) {clearTimeout(bootTimeout);fail(error.message);}
window.JsxFbdLab = {
    state,MODEL,get result(){return result;},get board(){return board;},get application(){return application;},
    get direction(){return direction;},get forceTip(){return forceTip;},get pivot(){return pivot;},get foot(){return foot;},
    get arm(){return arm;},get primaryArrow(){return primaryArrow;},get reactionPoint(){return reactionPoint;},
    get forceArrows(){return forceArrows;},get labeledObjects(){return labeledObjects;},get revision(){return revision;},
    get solvedRevision(){return solvedRevision;},physicalInputs,
};
