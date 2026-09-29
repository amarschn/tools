import * as THREE from '../../thread-visualizer-sizer/vendor/three-0.180.0/three.module.min.js';
import { OrbitControls } from '../../thread-visualizer-sizer/vendor/three-0.180.0/OrbitControls.js';
import { palette, fmt, escape } from './diagrams.js';

export class AssemblyView {
    constructor(container) {
        this.container=container;
        this.overlay=document.getElementById('three-labels');
        this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
        this.renderer.setPixelRatio(Math.min(devicePixelRatio,2));
        this.renderer.setClearColor(0,0);
        this.renderer.domElement.setAttribute('aria-label','Orbitable assembly with forces attached to their calculated 3D positions');
        this.renderer.domElement.setAttribute('role','img');
        container.prepend(this.renderer.domElement);
        this.scene=new THREE.Scene();
        this.camera=new THREE.OrthographicCamera(-2,2,1.2,-1.2,.01,100);
        this.camera.up.set(0,0,1);
        this.controls=new OrbitControls(this.camera,this.renderer.domElement);
        this.controls.enableDamping=false;
        this.controls.enablePan=false;
        this.controls.enableZoom=false;
        this.controls.minPolarAngle=.08;
        this.controls.maxPolarAngle=Math.PI-.08;
        this.controls.addEventListener('change',()=>this.render());
        this.labels=[];
        this.anchors=[];
        this.forceArrows=[];
        this.group=null;
        this.resizeObserver=new ResizeObserver(()=>this.resize());
        this.resizeObserver.observe(container);
    }

    update(view,{selected='all',anchors=false,arrowScale='schematic'}={}) {
        this.view=view;this.showAnchors=anchors;
        if(this.group) {
            this.scene.remove(this.group);
            this.group.traverse((o)=>{o.geometry?.dispose();if(o.material) o.material.dispose();});
        }
        this.labels=[];this.forceArrows=[];this.anchors=[];
        const c=palette(),e=view.e,group=new THREE.Group();this.group=group;
        const v=(p)=>new THREE.Vector3(...p);
        const axis=v([-Math.sin(view.item.inputs.downhill_deg*Math.PI/180),Math.cos(view.item.inputs.downhill_deg*Math.PI/180),0]);
        group.quaternion.setFromAxisAngle(axis,view.item.inputs.slope_deg*Math.PI/180);
        const span=Math.max(...e.polygon.flatMap((p)=>p.map(Math.abs)))*2;
        const top=Math.max(e.center[2]+.16,...view.item.result.free_body.forces.filter((f)=>f.kind!=='reaction').map((f)=>f.point[2]+.03));
        const line=(points,color=c.soft,width=1,dashed=false)=>{
            const geometry=new THREE.BufferGeometry().setFromPoints(points.map(v));
            const material=dashed ? new THREE.LineDashedMaterial({color,dashSize:.025,gapSize:.018}) : new THREE.LineBasicMaterial({color,linewidth:width});
            const object=new THREE.Line(geometry,material);if(dashed)object.computeLineDistances();group.add(object);return object;
        };
        const marker=(p,size,color,solid=true)=>{
            const object=new THREE.Mesh(new THREE.SphereGeometry(size,14,8),new THREE.MeshBasicMaterial({color,wireframe:!solid,depthTest:false}));
            object.position.copy(v(p));object.renderOrder=5;group.add(object);return object;
        };
        const floor=e.polygon.map(([x,y])=>[x,y,0]);
        const ceiling=e.polygon.map(([x,y])=>[x,y,top]);
        line([...floor,floor[0]],c.ink);
        line([...ceiling,ceiling[0]],c.soft);
        for(let i=0;i<floor.length;i++)line([floor[i],ceiling[i]],c.soft);
        const shape=new THREE.Shape(e.polygon.map(([x,y])=>new THREE.Vector2(x,y)));
        const mesh=new THREE.Mesh(new THREE.ShapeGeometry(shape),new THREE.MeshBasicMaterial({color:c.fill,side:THREE.DoubleSide,transparent:true,opacity:.65,depthWrite:false}));
        group.add(mesh);
        for(const p of floor)marker(p,span*.017,c.ink);
        // A short cylinder gives the selected tipping edge visible width in WebGL.
        const ea=v([...view.edge.start,0]),eb=v([...view.edge.end,0]),edgeVector=eb.clone().sub(ea);
        const edgeMesh=new THREE.Mesh(new THREE.CylinderGeometry(span*.006,span*.006,edgeVector.length(),10),new THREE.MeshBasicMaterial({color:c.ink}));
        edgeMesh.position.copy(ea.clone().add(eb).multiplyScalar(.5));
        edgeMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),edgeVector.clone().normalize());
        group.add(edgeMesh);
        this.labels.push({text:view.edge.id,point:ea.clone().add(eb).multiplyScalar(.5),dx:-16,dy:20});
        line([e.center,[e.center[0],e.center[1],0]],c.soft,1,true);
        marker(e.center,span*.017,c.ink);
        const reaction=[...e.reaction_point,0];
        marker(reaction,span*.022,view.section.reaction[0]<-1e-8?c.danger:c.ink,false);
        this.labels.push({text:'G',point:v(e.center),dx:12,dy:-14});
        this.labels.push({text:'R',point:v(reaction),dx:-18,dy:19});
        const forces=view.item.result.free_body.forces.filter((f)=>Math.hypot(...f.vector)>1e-7);
        const forceScale=span*.33/Math.max(...forces.map((f)=>Math.hypot(...f.vector)));
        for(const force of forces) {
            const anchor=v(force.point),direction=v(force.vector).normalize(),length=arrowScale==='schematic'?span*.3:Math.hypot(...force.vector)*forceScale;
            const headAtAnchor=force.kind==='reaction';
            const origin=headAtAnchor?anchor.clone().addScaledVector(direction,-length):anchor.clone();
            const alpha=selected==='all'||selected===force.id?1:.16;
            const arrow=new THREE.ArrowHelper(direction,origin,length,c.ink,Math.min(span*.052,length*.38),Math.min(span*.026,length*.2));
            for(const part of [arrow.line,arrow.cone]){part.material.depthTest=false;part.material.transparent=true;part.material.opacity=alpha;part.renderOrder=3;}
            // WebGL lines stay one device pixel wide. A cylinder keeps shafts legible when enlarged.
            const shaftLength=length-Math.min(span*.052,length*.38);
            const shaft=new THREE.Mesh(new THREE.CylinderGeometry(span*.0025,span*.0025,shaftLength,8),new THREE.MeshBasicMaterial({color:c.ink,depthTest:false,transparent:true,opacity:alpha}));
            shaft.position.y=shaftLength/2;shaft.renderOrder=3;arrow.line.visible=false;arrow.add(shaft);
            group.add(arrow);
            const labelPoint=headAtAnchor?origin.clone():origin.clone().addScaledVector(direction,length);
            this.labels.push({text:`${force.id} · ${fmt(Math.hypot(...force.vector),0)} N`,point:labelPoint,dx:12,dy:4,opacity:alpha});
            this.forceArrows.push({force,anchor,origin,direction,length,headAtAnchor,arrow});
            this.anchors.push(anchor);
            if(force.id.startsWith('P'))marker(force.point,span*.012,c.ink);
        }
        this.scene.add(group);group.updateMatrixWorld(true);
        this.halfHeight=Math.max(span,top)*.96;
        if(!this.initialized){this.reset();this.initialized=true;}
        this.resize();
    }

    reset() {
        if(!this.view)return;
        const center=new THREE.Vector3(...this.view.e.center).multiplyScalar(.45).applyQuaternion(this.group.quaternion);
        this.controls.target.copy(center);
        this.camera.position.copy(center).add(new THREE.Vector3(2.8,-3.7,2.3));
        this.camera.lookAt(center);this.controls.update();this.render();
    }

    rotate(delta) {
        const offset=this.camera.position.clone().sub(this.controls.target);
        offset.applyAxisAngle(new THREE.Vector3(0,0,1),delta);
        this.camera.position.copy(this.controls.target).add(offset);this.controls.update();this.render();
    }

    resize() {
        const width=this.container.clientWidth,height=this.container.clientHeight;
        if(!width||!height)return;
        this.renderer.setSize(width,height,false);
        const half=this.halfHeight||1.2;
        this.camera.left=-half*width/height;this.camera.right=half*width/height;
        this.camera.top=half;this.camera.bottom=-half;this.camera.updateProjectionMatrix();
        this.render();
    }

    render() {
        if(!this.group)return;
        const width=this.container.clientWidth,height=this.container.clientHeight;if(!width||!height)return;
        this.renderer.render(this.scene,this.camera);
        this.overlay.setAttribute('viewBox',`0 0 ${width} ${height}`);
        const project=(point)=>{
            const p=point.clone().applyMatrix4(this.group.matrixWorld).project(this.camera);
            return [(p.x*.5+.5)*width,(-p.y*.5+.5)*height];
        };
        const colors=palette(),occupied=[],fontSize=Math.max(12,Math.min(17,width/56));
        const labels=this.labels.map((label)=>{
            const p=project(label.point),w=label.text.length*fontSize*.56+8;
            let x=p[0]+label.dx,y=p[1]+label.dy;
            x=Math.max(10,Math.min(width-w-10,x));y=Math.max(46,Math.min(height-12,y));
            for(let tries=0;tries<7;tries++){
                if(!occupied.some((box)=>x<box.x+box.w&&x+w>box.x&&y-14<box.y+17&&y+3>box.y))break;
                y+=18;if(y>height-12)y=p[1]-22-tries*18;
            }
            occupied.push({x,y:y-14,w});
            const leader=Math.hypot(x-p[0],y-p[1])>28?`<line x1="${p[0]}" y1="${p[1]}" x2="${x}" y2="${y-4}" stroke="${colors.soft}" stroke-width=".8"/>`:'';
            return `<g opacity="${label.opacity??1}">${leader}<text x="${x}" y="${y}" font-size="${fontSize}" font-weight="550" fill="${colors.ink}" stroke="${colors.paper}" stroke-width="4" paint-order="stroke">${escape(label.text)}</text></g>`;
        });
        if(this.showAnchors)for(const anchor of this.anchors){const p=project(anchor);labels.push(`<circle cx="${p[0]}" cy="${p[1]}" r="8" fill="none" stroke="${colors.muted}" stroke-dasharray="2 3"/><path d="M${p[0]-12},${p[1]}h24 M${p[0]},${p[1]-12}v24" stroke="${colors.muted}" stroke-width=".7"/>`);}
        // Surface-frame axes use the same camera and ground rotation as the assembly.
        const origin=[42,height-38],worldOrigin=new THREE.Vector3(0,0,0).project(this.camera);
        for(const [basis,name] of [[[1,0,0],'x'],[[0,1,0],'y'],[[0,0,1],'z']]){
            const endpoint=new THREE.Vector3(...basis).applyQuaternion(this.group.quaternion).project(this.camera);
            const dx=(endpoint.x-worldOrigin.x)*width,dy=-(endpoint.y-worldOrigin.y)*height,mag=Math.hypot(dx,dy);
            const end=[origin[0]+dx/mag*25,origin[1]+dy/mag*25];
            labels.push(`<line x1="${origin[0]}" y1="${origin[1]}" x2="${end[0]}" y2="${end[1]}" stroke="${colors.muted}"/><text x="${end[0]+4}" y="${end[1]+3}" font-size="11" fill="${colors.muted}">${name}</text>`);
        }
        this.overlay.innerHTML=labels.join('');
    }
}
