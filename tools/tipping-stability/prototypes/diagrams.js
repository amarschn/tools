/* Original diagram primitives. Only projection/layout lives here; forces come from Python. */
export const WIDTH = 680;
export const HEIGHT = 420;
export const norm = (v) => Math.hypot(...v);
export const add = (a, b) => a.map((x, i) => x + b[i]);
export const sub = (a, b) => a.map((x, i) => x - b[i]);
export const mul = (a, s) => a.map((x) => x * s);
export const dot = (a, b) => a.reduce((sum, x, i) => sum + x * b[i], 0);
export const fmt = (x, places = 2) => (Math.abs(x) < 1e-9 ? 0 : x).toFixed(places);
export const escape = (x) => String(x).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

export function palette() {
    const css = getComputedStyle(document.body);
    return Object.fromEntries(Object.entries({ink:'--text-color',muted:'--text-light',soft:'--diagram-soft',fill:'--diagram-fill',paper:'--diagram-paper',border:'--border-color',danger:'--danger-color',good:'--success-color'}).map(([key, value]) => [key, css.getPropertyValue(value).trim()]));
}

export function caseView(item, edgeId) {
    const e = item.result.equilibrium;
    const edge = e.edges.find((candidate) => candidate.id === edgeId);
    const section = item.result.free_body.sections[edge.id];
    const forces = section.forces.map((force) => ({...item.result.free_body.forces.find((f) => f.id === force.id), ...force}));
    return {item, e, edge, section, forces: forces.filter((f) => norm([...f.vector, f.out_of_plane]) > 1e-7)};
}

function primitives() {
    const items = [];
    return {
        items,
        line: (a, b, opts = {}) => items.push({type:'line', a, b, ...opts}),
        poly: (points, opts = {}) => items.push({type:'poly', points, ...opts}),
        circle: (p, radius, opts = {}) => items.push({type:'circle', p, radius, ...opts}),
        text: (p, text, opts = {}) => items.push({type:'text', p, text, size:14, ...opts}),
        arrow: (anchor, vector, force, opts = {}) => {
            // Reactions have their head at the contact. No lateral displacement is permitted.
            const headAtAnchor = force.kind === 'reaction';
            const a = headAtAnchor ? sub(anchor, vector) : anchor;
            const b = headAtAnchor ? anchor : add(anchor, vector);
            items.push({type:'arrow', a, b, anchor, id:force.id, headAtAnchor, ...opts});
        },
    };
}

function glyph(pen, p, label, options = {}) {
    const radius = label === 'G' ? 6 : 4;
    pen.circle(p, radius, {fill:label==='R'?null:'paper', width:1.7, pointName:label, ...options});
    if (label === 'G') {
        pen.line(add(p,[-4,0]),add(p,[4,0]),options);
        pen.line(add(p,[0,-4]),add(p,[0,4]),options);
    }
    if (label) pen.text(add(p,label === 'R' ? [-13,19] : [12,-12]),label,{size:14,bold:true,align:label==='R'?'end':'start',...options});
}

function anchorGuide(pen, p) {
    pen.circle(p, 11, {stroke:'muted',dash:[2,3],width:.8});
    pen.line(add(p,[-16,0]),add(p,[16,0]),{stroke:'muted',width:.7});
    pen.line(add(p,[0,-16]),add(p,[0,16]),{stroke:'muted',width:.7});
}

function forceGlyph(pen, anchor, force, options = {}) {
    // A component directed along the viewing axis is a dot/cross at the actual point.
    pen.circle(anchor, 7, {width:1.5,fill:'paper',...options});
    if (force.out_of_plane > 0) pen.circle(anchor, 2, {fill:'ink',...options});
    else {
        pen.line(add(anchor,[-3,-3]),add(anchor,[3,3]),options);
        pen.line(add(anchor,[-3,3]),add(anchor,[3,-3]),options);
    }
}

function intersects(box, other) {
    return box.x < other.x+other.w && box.x+box.w > other.x && box.y < other.y+other.h && box.y+box.h > other.y;
}

function labelForces(pen) {
    const occupied = pen.items.filter((p) => p.type === 'text').map((p) => ({x:p.p[0]-4,y:p.p[1]-p.size,w:p.text.length*p.size*.6+8,h:p.size+6}));
    const arrows = pen.items.filter((p) => p.type === 'arrow' && p.id && !p.noLabel);
    for (const arrow of arrows) {
        const origin = arrow.headAtAnchor ? arrow.a : arrow.b;
        const candidates = [[14,-9],[14,17],[-30,-9],[-30,19],[7,-22],[7,31],[30,0],[-44,0]];
        const width = arrow.id.length*9+8, height = 21;
        let best;
        for (const [dx,dy] of candidates) {
            const x = origin[0]+dx, y = origin[1]+dy;
            const box = {x:x-3,y:y-16,w:width,h:height};
            let cost = Math.hypot(dx,dy);
            cost += occupied.filter((p) => intersects(box,p)).length*1000;
            for (const other of arrows) {
                for (let t=.1;t<1;t+=.15) {
                    const p = add(other.a,mul(sub(other.b,other.a),t));
                    if (p[0]>box.x && p[0]<box.x+box.w && p[1]>box.y && p[1]<box.y+box.h) cost+=150;
                }
            }
            if (box.x<18 || box.y<20 || box.x+width>WIDTH-18 || box.y+height>HEIGHT-38) cost+=10000;
            if (!best || cost<best.cost) best={x,y,box,cost};
        }
        occupied.push(best.box);
        pen.text([best.x,best.y],arrow.id,{size:15,bold:true,opacity:arrow.opacity,id:arrow.id});
    }
}

/** Fit geometry with a single scale; rotate the section so projected gravity is vertical. */
export function sectionScene(view, {world=false, anchors=false, selected='all', only=null, moment=false, compact=false, arrowScale='schematic'} = {}) {
    const {section,forces,edge} = view;
    const pen=primitives();
    const weight=forces.find((f)=>f.id==='W');
    const angle=world ? Math.atan2(weight.vector[0],-weight.vector[1]) : 0;
    const rotate=([u,z])=>[u*Math.cos(angle)+z*Math.sin(angle),u*Math.sin(angle)-z*Math.cos(angle)];
    const u0=Math.min(0,...forces.map((f)=>f.point[0]));
    const u1=Math.max(section.support_span,...forces.map((f)=>f.point[0]));
    const top=Math.max(section.center[1]+.13,...forces.filter((f)=>f.kind!=='reaction').map((f)=>f.point[1]+.04));
    const shell=[[0,0],[section.support_span,0],[section.support_span,top],[0,top]];
    const fitting=[...shell,[u0,0],[u1,0],section.reaction].map(rotate);
    const xmin=Math.min(...fitting.map((p)=>p[0])),xmax=Math.max(...fitting.map((p)=>p[0]));
    const ymin=Math.min(...fitting.map((p)=>p[1])),ymax=Math.max(...fitting.map((p)=>p[1]));
    const scale=Math.min(365/Math.max(xmax-xmin,.1),207/Math.max(ymax-ymin,.1));
    const offset=[WIDTH/2-(xmin+xmax)*scale/2,76-ymin*scale];
    const project=(p)=>add(offset,mul(rotate(p),scale));
    const pivot=project([0,0]),center=project(section.center),reaction=project(section.reaction);
    const forceScale=Math.min(87,section.center[1]*scale*.58)/Math.max(...forces.map((f)=>norm(f.vector)),1);
    const opacity=(force)=>selected!=='all' && selected!==force.id ? .17 : 1;
    pen.poly(shell.map(project),{fill:'fill',stroke:'soft',width:1.2,dash:moment?[4,4]:[]});
    pen.line(project([u0-.15,0]),project([u1+.15,0]),{stroke:'soft',width:1});
    for (let u=0;u<section.support_span+.01;u+=section.support_span/18) {
        pen.line(project([u,0]),project([u-.025,-.026]),{stroke:'soft',width:.8});
    }
    pen.line(project([0,0]),project([section.support_span,0]),{width:2});
    pen.line(center,project([section.center[0],0]),{stroke:'soft',dash:[3,4],width:1});
    if (!compact) {
        pen.text([26,28],world ? 'WEIGHT VERTICAL IN THIS SECTION' : moment ? `MOMENT ABOUT ${edge.id}` : 'LOOKING ALONG THE SELECTED EDGE',{size:11,stroke:'muted'});
        pen.text([WIDTH-26,28],edge.label,{size:11,stroke:'muted',align:'end'});
        pen.text([26,HEIGHT-17],world ? `Apparent incline ${fmt(Math.abs(angle*180/Math.PI),1)}°` : `G height ${fmt(section.center[1])} m`,{size:12,stroke:'muted'});
        pen.text([WIDTH-26,HEIGHT-17],`R from edge ${fmt(section.reaction[0],3)} m`,{size:12,stroke:section.reaction[0]<-1e-8?'danger':'muted',align:'end'});
        const axisOrigin=[WIDTH-79,HEIGHT-74];
        for (const [v,name] of [[[1,0],'u'],[[0,1],'z']]) {
            const end=add(axisOrigin,mul(rotate(v),28));
            pen.arrow(axisOrigin,mul(rotate(v),28),{id:null,kind:'axis'},{stroke:'muted',width:1});
            pen.text(add(end,[7,3]),name,{size:12,stroke:'muted'});
        }
    }
    let momentForce=null;
    if (moment) {
        momentForce=forces.find((f)=>f.id===selected) || forces.find((f)=>f.id.startsWith('P')) || weight;
        const vector=momentForce.vector, vlen=norm(vector);
        if (vlen>1e-8) {
            const p=momentForce.point;
            const foot=sub(p,mul(vector,dot(p,vector)/(vlen*vlen)));
            const dir=mul(vector,1/vlen);
            // Clip the infinite line to the panel; it always passes through the physical point.
            const point=project(p), screenDir=rotate(dir);
            const limits=[-Infinity,Infinity];
            for (let axis=0;axis<2;axis++) {
                const lo=axis?45:75, hi=axis?HEIGHT-65:WIDTH-70;
                if (Math.abs(screenDir[axis])>1e-10) {
                    const values=[(lo-point[axis])/screenDir[axis],(hi-point[axis])/screenDir[axis]].sort((a,b)=>a-b);
                    limits[0]=Math.max(limits[0],values[0]);limits[1]=Math.min(limits[1],values[1]);
                }
            }
            pen.line(add(point,mul(screenDir,limits[0])),add(point,mul(screenDir,limits[1])),{stroke:'muted',dash:[6,5],width:1.3});
            pen.line(pivot,project(foot),{width:2.2});
            const armMid=mul(add(pivot,project(foot)),.5);
            // Lever arm uses the solver's moment and the displayed in-plane force magnitude.
            const callout=[32,164];
            pen.text(callout,`Lever arm`,{size:12,stroke:'muted'});
            pen.text(add(callout,[0,22]),`${fmt(Math.abs(momentForce.restoring_moment)/vlen,3)} m`,{size:17,bold:true});
            pen.line([112,192],armMid,{stroke:'soft',width:.9});
            const footPx=project(foot),towardPivot=sub(pivot,footPx);
            if(norm(towardPivot)>12) {
                const leg=mul(towardPivot,8/norm(towardPivot)),along=mul(screenDir,8);
                pen.line(add(footPx,leg),add(add(footPx,leg),along),{stroke:'muted',width:1});
                pen.line(add(add(footPx,leg),along),add(footPx,along),{stroke:'muted',width:1});
            }
        }
    }
    const outOfPlaneGlyphs=[];
    for (const force of forces) {
        if (only && force.id!==only) continue;
        if (moment && force.id!==momentForce.id) continue;
        const anchor=project(force.point);
        const alpha=moment||only ? 1 : opacity(force);
        const lengthFactor=arrowScale==='schematic'?70/Math.max(norm(force.vector),1e-8):forceScale;
        if (norm(force.vector)>1e-7) pen.arrow(anchor,mul(rotate(force.vector),lengthFactor),force,{opacity:alpha,width:2.3,dash:force.id==='I'?[5,3]:[]});
        if (norm(force.vector)<1e-7 && Math.abs(force.out_of_plane)>1e-7) {
            outOfPlaneGlyphs.push({anchor,force,alpha});
            pen.text(add(anchor,[15,20]),force.id,{bold:true,opacity:alpha});
        }
        if (anchors) anchorGuide(pen,anchor);
        if (force.id.startsWith('P')) glyph(pen,anchor,'',{opacity:alpha});
    }
    glyph(pen,center,'G');
    glyph(pen,reaction,'R',{stroke:section.reaction[0]<-1e-8?'danger':'ink'});
    for(const {anchor,force,alpha} of outOfPlaneGlyphs)forceGlyph(pen,anchor,force,{opacity:alpha});
    pen.circle(pivot,4,{fill:'ink'});
    if(!compact) pen.text(add(pivot,[-12,-10]),'edge',{align:'end',size:12,stroke:'muted'});
    if (anchors) {anchorGuide(pen,center);anchorGuide(pen,reaction);}
    labelForces(pen);
    return {items:pen.items,view,project,forceScale,scale,momentForce,angle};
}

function arrowHead(a,b,size=9) {
    const v=sub(b,a),length=norm(v);
    if(length<1e-7) return [];
    const u=mul(v,1/length),head=Math.min(size,length*.5),width=head*.45;
    return [b,add(sub(b,mul(u,head)),[-u[1]*width,u[0]*width]),add(sub(b,mul(u,head)),[u[1]*width,-u[0]*width])];
}

export function svgMarkup(scene, {title='Free-body diagram',interactive=true}={}) {
    const colors=palette();
    const pieces=scene.items.map((p)=>{
        const stroke=colors[p.stroke||'ink'],fill=p.fill?colors[p.fill]:'none';
        const style=`stroke="${stroke}" fill="${fill}" stroke-width="${p.width||1.2}" opacity="${p.opacity??1}"${p.dash?.length?` stroke-dasharray="${p.dash.join(' ')}"`:''}`;
        if(p.type==='line')return `<line x1="${p.a[0]}" y1="${p.a[1]}" x2="${p.b[0]}" y2="${p.b[1]}" ${style}/>`;
        if(p.type==='circle')return `<circle ${p.pointName?`data-point="${p.pointName}"`:''} cx="${p.p[0]}" cy="${p.p[1]}" r="${p.radius}" ${style}/>`;
        if(p.type==='poly')return `<polygon points="${p.points.map((q)=>q.join(',')).join(' ')}" ${style}/>`;
        if(p.type==='text')return `<text x="${p.p[0]}" y="${p.p[1]}" font-size="${p.size}" fill="${stroke}" opacity="${p.opacity??1}" text-anchor="${p.align||'start'}" font-weight="${p.bold?600:400}" paint-order="stroke" stroke="${colors.paper}" stroke-width="4" stroke-linejoin="round">${escape(p.text)}</text>`;
        const line=`x1="${p.a[0]}" y1="${p.a[1]}" x2="${p.b[0]}" y2="${p.b[1]}"`;
        return `<g class="force" ${p.id?`data-force="${p.id}" data-anchor-x="${p.anchor[0]}" data-anchor-y="${p.anchor[1]}" data-head-anchor="${p.headAtAnchor}" ${interactive?'tabindex="0" role="button"':''} aria-label="Inspect ${p.id}"`:''} opacity="${p.opacity??1}"><line ${line} stroke="${colors.paper}" stroke-width="6"/><line class="shaft" ${line} stroke="${stroke}" stroke-width="${p.width||2}" ${p.dash?.length?`stroke-dasharray="${p.dash.join(' ')}"`:''}/><polygon points="${arrowHead(p.a,p.b).map((q)=>q.join(',')).join(' ')}" fill="${stroke}"/>${p.id?`<line ${line} stroke="transparent" stroke-width="17"/>`:''}</g>`;
    });
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${WIDTH} ${HEIGHT}" role="img" aria-label="${escape(title)}">${pieces.join('')}</svg>`;
}

export function renderCanvas(canvas,scene) {
    const dpr=Math.min(window.devicePixelRatio||1,2);
    const box=canvas.getBoundingClientRect();
    canvas.width=Math.max(1,box.width*dpr); canvas.height=Math.max(1,box.height*dpr);
    const context=canvas.getContext('2d'),colors=palette();
    const zoom=Math.min(canvas.width/WIDTH,canvas.height/HEIGHT);
    context.setTransform(zoom,0,0,zoom,(canvas.width-WIDTH*zoom)/2,(canvas.height-HEIGHT*zoom)/2);
    context.lineCap='round'; context.lineJoin='round';
    function path(points,close=false) {
        context.beginPath();context.moveTo(...points[0]);points.slice(1).forEach((p)=>context.lineTo(...p));if(close)context.closePath();
    }
    for(const p of scene.items) {
        context.save();context.globalAlpha=p.opacity??1;
        context.strokeStyle=colors[p.stroke||'ink'];context.fillStyle=p.fill?colors[p.fill]:'transparent';context.lineWidth=p.width||1.2;context.setLineDash(p.dash||[]);
        if(p.type==='line'){path([p.a,p.b]);context.stroke();}
        if(p.type==='poly'){path(p.points,true);context.fill();context.stroke();}
        if(p.type==='circle'){context.beginPath();context.arc(...p.p,p.radius,0,2*Math.PI);context.fill();context.stroke();}
        if(p.type==='text'){
            context.font=`${p.bold?600:400} ${p.size}px "Helvetica Neue", Arial, sans-serif`;
            context.textAlign=p.align==='middle'?'center':p.align==='end'?'right':'left';
            context.lineWidth=4;context.strokeStyle=colors.paper;context.strokeText(p.text,...p.p);
            context.fillStyle=colors[p.stroke||'ink'];context.fillText(p.text,...p.p);
        }
        if(p.type==='arrow'){
            const color=colors[p.stroke||'ink'];
            context.setLineDash([]);context.strokeStyle=colors.paper;context.lineWidth=6;path([p.a,p.b]);context.stroke();
            context.strokeStyle=color;context.lineWidth=p.width||2;context.setLineDash(p.dash||[]);path([p.a,p.b]);context.stroke();
            context.setLineDash([]);context.fillStyle=color;path(arrowHead(p.a,p.b),true);context.fill();
        }
        context.restore();
    }
    canvas._scene=scene;
}

export function smallMultiples(view,options) {
    const columns=Math.min(3,view.forces.length),rows=Math.ceil(view.forces.length/columns),cellW=WIDTH/columns,cellH=(HEIGHT-28)/rows;
    const all=[];
    view.forces.forEach((force,index)=>{
        const col=index%columns,row=Math.floor(index/columns),left=col*cellW,top=row*cellH;
        const scene=sectionScene(view,{...options,only:force.id,compact:true});
        const s=Math.min((cellW-28)/450,(cellH-63)/340);
        const offset=[left+cellW/2-340*s,top+cellH/2-205*s+16];
        const headingY=rows===1?top+60:top+24;
        all.push({type:'text',p:[left+18,headingY],text:`${force.id}   ${fmt(norm([...force.vector,force.out_of_plane]),0)} N`,size:14,bold:true});
        for(const p of scene.items){
            const q={...p,width:Math.max(.7,(p.width||1.2)*.75)};
            if(q.p)q.p=add(offset,mul(q.p,s));
            if(q.a)q.a=add(offset,mul(q.a,s));if(q.b)q.b=add(offset,mul(q.b,s));
            if(q.anchor)q.anchor=add(offset,mul(q.anchor,s));if(q.points)q.points=q.points.map((p)=>add(offset,mul(p,s)));
            if(q.radius)q.radius*=.65;if(q.size)q.size=10;
            if(q.type==='text' && q.text===force.id)continue;
            if(options.selected!=='all'&&options.selected!==force.id)q.opacity=.22;
            all.push(q);
        }
        if(Math.abs(force.out_of_plane)>1e-7)all.push({type:'text',p:[left+18,top+cellH-9],text:`${force.out_of_plane>0?'⊙':'⊗'} ${fmt(Math.abs(force.out_of_plane),1)} N along edge`,size:10,stroke:'muted'});
        if(col<columns-1)all.push({type:'line',a:[left+cellW,top+35],b:[left+cellW,top+cellH-12],stroke:'border',width:1});
    });
    if(rows<2)all.push({type:'text',p:[WIDTH/2,HEIGHT-20],text:'Only nonzero forces are shown.',size:12,stroke:'muted',align:'middle'});
    return {items:all};
}

export function renderBoard(container,scene,onSelect) {
    if(!window.JXG)throw new Error('JSXGraph did not load.');
    const colors=palette(),board=window.JXG.JSXGraph.initBoard(container.id,{
        boundingbox:[0,HEIGHT,WIDTH,0],keepaspectratio:true,axis:false,showCopyright:false,showNavigation:false,
        pan:{enabled:true,needShift:true},zoom:{enabled:true,wheel:false,needShift:true},resize:{enabled:false},
        keyboard:{enabled:false},renderer:'svg',showInfobox:false,
    });
    const pt=(p)=>[p[0],HEIGHT-p[1]];
    board.suspendUpdate();
    for(const p of scene.items){
        const attr={fixed:true,highlight:false,strokeColor:colors[p.stroke||'ink'],strokeWidth:p.width||1.2,strokeOpacity:p.opacity??1,fillOpacity:p.opacity??1,fillColor:p.fill?colors[p.fill]:'none',dash:p.dash?.length?2:0};
        if(p.type==='line')board.create('segment',[pt(p.a),pt(p.b)],attr);
        if(p.type==='circle')board.create('circle',[pt(p.p),p.radius],{...attr,center:{visible:false}});
        if(p.type==='poly')board.create('polygon',p.points.map(pt),{...attr,vertices:{visible:false},borders:attr,hasInnerPoints:false});
        if(p.type==='text')board.create('text',[...pt(p.p),p.text],{...attr,fontSize:p.size,display:'internal',anchorY:'bottom',anchorX:p.align==='middle'?'middle':p.align==='end'?'right':'left',cssStyle:`font-weight:${p.bold?600:400};`,strokeColor:colors[p.stroke||'ink']});
        if(p.type==='arrow'){
            board.create('segment',[pt(p.a),pt(p.b)],{...attr,strokeColor:colors.paper,strokeWidth:6,dash:0});
            const arrow=board.create('arrow',[pt(p.a),pt(p.b)],{...attr,lastArrow:{type:2,size:5},point1:{visible:false},point2:{visible:false}});
            if(p.id)arrow.on('down',()=>onSelect(p.id));
        }
    }
    board.unsuspendUpdate();
    board._prototypeScene=scene;
    return board;
}
