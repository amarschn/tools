/* Fixed isometric geometry and linked FBD. Force balance/projections come from Python. */
'use strict';

window.TippingDiagram = class TippingDiagram {
    constructor({ onEdge, onDerivation, format }) {
        this.onEdge = onEdge;
        this.format = format;
        this.entity = 'G';
        this.result = null;
        this.state = 'loading';
        this.expanded = false;
        this.model = document.getElementById('model-scene');
        this.fbd = document.getElementById('fbd-scene');
        this.key = document.getElementById('force-key');
        this.edgeControl = document.getElementById('diagram-edge');
        this.toggle = document.getElementById('toggle-fbd');
        this.toggle.addEventListener('click', () => this.setExpanded(!this.expanded));
        this.edgeControl.addEventListener('change', () => this.onEdge(this.edgeControl.value));
        document.getElementById('diagram-derivation').addEventListener('click', () => onDerivation(this.entity));
        for (const element of [this.model, this.fbd, this.key]) {
            element.addEventListener('click', (event) => {
                const edge = event.target.closest('[data-diagram-edge]');
                const entity = event.target.closest('[data-entity]');
                if (edge) {
                    this.setExpanded(true);
                    this.onEdge(edge.dataset.diagramEdge);
                } else if (entity) {
                    this.setExpanded(true);
                    document.getElementById('force-details').open = true;
                    this.select(entity.dataset.entity);
                }
            });
        }
        let previousWidth = 0;
        new ResizeObserver(([entry]) => {
            if (Math.abs(entry.contentRect.width - previousWidth) < 1 || !this.result) return;
            previousWidth = entry.contentRect.width;
            this.draw();
        }).observe(document.querySelector('.visual-pair'));
    }

    escape(value) {
        return String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
    }

    number(value) {
        return this.format(Math.abs(value) < 1e-10 ? 0 : value);
    }

    vector(values) {
        return `(${values.map((value) => this.number(value)).join(', ')})`;
    }

    setExpanded(open) {
        if (this.expanded === open) return;
        this.expanded = open;
        document.querySelector('.model-workspace').classList.toggle('show-fbd', open);
        this.toggle.setAttribute('aria-expanded', String(open));
        this.toggle.firstElementChild.textContent = open ? 'Hide forces & free-body diagram' : 'Show forces & free-body diagram';
        this.toggle.lastElementChild.textContent = open ? '−' : '+';
        document.getElementById('fbd-panel').hidden = !open;
        document.getElementById('fbd-controls').hidden = !open;
        this.model.setAttribute('aria-label', open ? 'Isometric cart model with ground contacts, center of mass, and forces linked to the free-body diagram' : 'Isometric cart model with ground contacts and center of mass');
        this.draw();
    }

    update(result, inputs, edge) {
        this.result = result;
        this.inputs = inputs;
        this.edge = edge;
        if (this.entity !== 'G' && !result.free_body.forces.some((force) => force.id === this.entity)) this.entity = 'G';
        this.edgeControl.innerHTML = result.equilibrium.edges.map((item) => `<option value="${item.id}" ${item.id === result.equilibrium.governing_edge ? 'selected' : ''}>${this.escape(item.label)}${item.id === result.equilibrium.governing_edge ? ' · nearest' : ''}</option>`).join('');
        this.edgeControl.value = edge;
        this.fbd.dataset.edge = edge;
        this.draw();
        this.setState('current');
    }

    setState(state, message = '') {
        this.state = state;
        if (state === 'invalid' || state === 'current') {
            this.edgeControl.disabled = state === 'invalid';
            document.getElementById('diagram-derivation').disabled = state === 'invalid';
        }
        const element = document.getElementById('diagram-state');
        element.dataset.state = state;
        element.hidden = state !== 'invalid';
        element.textContent = state === 'invalid' ? 'The image shows the last valid case. Correct the input to update it.' : '';
        document.querySelector('.primary-result').disabled = state !== 'current';
        if (message && state === 'invalid') element.title = message;
        else element.removeAttribute('title');
    }

    select(entity) {
        this.entity = entity;
        for (const element of document.querySelectorAll('.model-workspace [data-entity]')) {
            const selected = this.expanded && element.dataset.entity === entity;
            element.classList.toggle('linked-active', selected);
            if (element.tagName === 'BUTTON') element.setAttribute('aria-pressed', String(selected));
        }
        this.inspect();
    }

    draw() {
        if (!this.result) return;
        this.renderModel();
        this.arrangeLabels(this.model);
        if (this.expanded) {
            this.renderFbd();
            this.arrangeLabels(this.fbd);
            this.renderKey();
        }
        this.select(this.entity);
    }

    arrangeLabels(svg) {
        // Keep annotation text legible without moving physical points or force arrows.
        const width = svg.viewBox.baseVal.width, height = svg.viewBox.baseVal.height;
        const labels = [...svg.querySelectorAll('.diagram-label')];
        const priority = (label) => label.classList.contains('force-label') ? 3 : label.closest('[data-entity="G"]') ? 2 : 1;
        labels.sort((a,b) => priority(b)-priority(a));
        const occupied = [];
        const offsets = [[0,0],[0,-15],[0,15],[18,0],[-18,0],[22,-18],[-22,-18],[22,18],[-22,18],[0,-32],[0,32],[40,-10],[-40,-10],[40,22],[-40,22],[0,-48],[0,48]];
        for (const label of labels) {
            const x = Number(label.getAttribute('x')), y = Number(label.getAttribute('y'));
            const box = label.getBBox();
            let best = [0,0], bestCost = Infinity;
            for (const [dx,dy] of offsets) {
                const shiftX = Math.min(width-8-box.x-box.width,Math.max(8-box.x,dx));
                const shiftY = Math.min(height-9-box.y-box.height,Math.max(28-box.y,dy));
                const candidate = {x:box.x+shiftX-3,y:box.y+shiftY-2,width:box.width+6,height:box.height+4};
                const overlaps = occupied.filter((other) => candidate.x<other.x+other.width && candidate.x+candidate.width>other.x && candidate.y<other.y+other.height && candidate.y+candidate.height>other.y).length;
                const cost = overlaps*1000 + Math.hypot(shiftX,shiftY);
                if (cost<bestCost) { bestCost=cost; best=[shiftX,shiftY]; }
                if (cost===0) break;
            }
            const [dx,dy] = best;
            if (Math.hypot(dx,dy)>3) {
                label.setAttribute('x',x+dx); label.setAttribute('y',y+dy);
                const leader = document.createElementNS('http://www.w3.org/2000/svg','line');
                const anchorX = Number(label.dataset.calloutX ?? x), anchorY = Number(label.dataset.calloutY ?? y-4);
                const labelX = Math.max(box.x+dx,Math.min(box.x+dx+box.width,anchorX));
                const labelY = Math.max(box.y+dy,Math.min(box.y+dy+box.height,anchorY));
                for (const [name,value] of Object.entries({x1:anchorX,y1:anchorY,x2:labelX,y2:labelY,class:'leader','pointer-events':'none'})) leader.setAttribute(name,String(value));
                label.before(leader);
            }
            occupied.push({x:box.x+dx-3,y:box.y+dy-2,width:box.width+6,height:box.height+4});
        }
    }

    label(x, y, text, attributes = '') {
        return `<text x="${x}" y="${y}" class="diagram-label" ${attributes}>${this.escape(text)}</text>`;
    }

    line(a, b, attributes = '') {
        return `<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" ${attributes}/>`;
    }

    arrow(origin, vector, force, prefix, labelOffset = [0, 0], offset = [0, 0]) {
        const magnitude = Math.hypot(...vector);
        if (magnitude < 1e-9) return '';
        const start = [origin[0] + offset[0], origin[1] + offset[1]];
        const end = [start[0] + vector[0], start[1] + vector[1]];
        const labelX = end[0] + (vector[0] >= 0 ? 8 : -8) + labelOffset[0];
        const labelY = end[1] + (vector[1] > 0 ? 12 : -6) + labelOffset[1];
        const name = this.escape(force.id);
        const unit = vector.map((value) => value / magnitude);
        const head = [end, [end[0]-unit[0]*8-unit[1]*4,end[1]-unit[1]*8+unit[0]*4], [end[0]-unit[0]*8+unit[1]*4,end[1]-unit[1]*8-unit[0]*4]].map((point) => point.join(',')).join(' ');
        return `<g class="force-arrow ${force.kind}" data-entity="${name}" aria-label="${this.escape(force.name)}"><title>${this.escape(force.name)}: ${this.number(Math.hypot(...force.vector))} N</title>${offset.some(Boolean) ? this.line(origin, start, 'class="leader"') : ''}${this.line(start, end, `class="force-shaft" stroke="currentColor" stroke-width="2" `)}<polygon points="${head}" fill="currentColor"/>${this.line(start, end, 'stroke="transparent" stroke-width="15"')}<text x="${labelX}" y="${labelY}" data-callout-x="${end[0]}" data-callout-y="${end[1]}" text-anchor="${vector[0] < -1 ? 'end' : 'start'}" class="force-label diagram-label">${name}</text></g>`;
    }

    definitions(prefix) {
        return `<defs><marker id="${prefix}-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="context-stroke"/></marker><marker id="${prefix}-dim" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto-start-reverse"><path d="M0,0 L6,3 L0,6" fill="none" stroke="var(--text-light)" stroke-width=".8"/></marker></defs>`;
    }

    renderModel() {
        const e = this.result.equilibrium;
        const width = Math.max(280, this.model.clientWidth);
        const height = this.model.clientHeight || 340;
        this.model.setAttribute('viewBox', `0 0 ${width} ${height}`);
        const polygon = e.polygon;
        const xs = polygon.map((point) => point[0]), ys = polygon.map((point) => point[1]);
        const xmin = Math.min(...xs), xmax = Math.max(...xs), ymin = Math.min(...ys), ymax = Math.max(...ys);
        const length = xmax - xmin, track = ymax - ymin;
        const span = Math.max(length, track, .001);
        const radius = Math.max(Math.min(length, track) * .12, span * .035);
        const deckHeight = radius * 2.1;
        const theta = (this.inputs.slope_deg || 0) * Math.PI / 180;
        const phi = (this.inputs.downhill_deg ?? 90) * Math.PI / 180;
        // Rotate the surface frame downhill into a world frame with vertical gravity.
        const axis = [-Math.sin(phi), Math.cos(phi), 0];
        const world = (point) => {
            const dot = point[0] * axis[0] + point[1] * axis[1];
            const cross = [axis[1] * point[2], -axis[0] * point[2], axis[0] * point[1] - axis[1] * point[0]];
            return point.map((value, i) => value * Math.cos(theta) + cross[i] * Math.sin(theta) + axis[i] * dot * (1 - Math.cos(theta)));
        };
        const azimuth = -Math.PI / 4, elevation = Math.atan(1 / Math.sqrt(2));
        const right = [-Math.sin(azimuth), Math.cos(azimuth), 0];
        const up = [-Math.sin(elevation) * Math.cos(azimuth), -Math.sin(elevation) * Math.sin(azimuth), Math.cos(elevation)];
        const eye = [Math.cos(elevation) * Math.cos(azimuth), Math.cos(elevation) * Math.sin(azimuth), Math.sin(elevation)];
        const dot = (a, b) => a.reduce((sum, value, index) => sum + value * b[index], 0);
        const raw = (point) => { const transformed = world(point); return [dot(transformed, right), -dot(transformed, up), dot(transformed, eye)]; };
        const meshes = [];
        const face = (points, fill, extra = '') => meshes.push({ points, fill, extra, depth: points.reduce((sum, point) => sum + raw(point)[2], 0) / points.length });
        const box = (x0, y0, z0, x1, y1, z1, extra = '') => {
            const p = [[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]];
            for (const [indices, fill] of [[[0,1,5,4],'side'],[[1,2,6,5],'front'],[[2,3,7,6],'side'],[[3,0,4,7],'front'],[[4,5,6,7],'top']]) face(indices.map((index) => p[index]), `var(--model-${fill})`, extra);
        };
        const custom = Array.isArray(this.inputs.contacts);
        const contacts = custom ? this.inputs.contacts.map((point) => point.slice(0, 2).map(Number)) : polygon;
        for (const [x, y] of contacts) {
            if (custom) {
                box(x-radius*.3, y-radius*.3, 0, x+radius*.3, y+radius*.3, deckHeight);
                continue;
            }
            const rings = [-1, 1].map((side) => Array.from({ length: 20 }, (_, i) => {
                const angle = i * Math.PI / 10;
                return [x + radius * Math.cos(angle), y + side * radius * .32, radius + radius * Math.sin(angle)];
            }));
            for (let i = 0; i < 20; i++) face([rings[0][i], rings[0][(i+1)%20], rings[1][(i+1)%20], rings[1][i]], 'var(--model-tire)', 'data-mesh="wheel"');
            for (const ring of rings) face(ring, 'var(--model-tire)', 'data-mesh="wheel"');
            for (const side of [-1, 1]) face(Array.from({ length: 16 }, (_, i) => [x + radius * .4 * Math.cos(i*Math.PI/8), y + side * radius * .325, radius + radius * .4 * Math.sin(i*Math.PI/8)]), 'var(--model-hub)');
        }
        const low = polygon.map(([x,y]) => [x, y, deckHeight - radius*.4]);
        const high = polygon.map(([x,y]) => [x, y, deckHeight]);
        face(high, 'var(--model-top)');
        for (let i = 0; i < polygon.length; i++) face([low[i],low[(i+1)%low.length],high[(i+1)%high.length],high[i]], i%2 ? 'var(--model-side)' : 'var(--model-front)');
        const components = this.result.mass_components;
        for (const component of components.slice(0, 16)) {
            const size = span * .37 * Math.cbrt(component.mass / e.mass);
            const halfZ = Math.min(size * .48, component.z * .85);
            if (halfZ > span * .005) box(component.x-size*.65, component.y-size*.5, component.z-halfZ, component.x+size*.65, component.y+size*.5, component.z+halfZ, 'data-mesh="mass"');
            if (component.z - halfZ > deckHeight) box(component.x-span*.014, component.y-span*.014, deckHeight, component.x+span*.014, component.y+span*.014, component.z-halfZ);
        }
        const ground = [[xmin-span*.27,ymin-span*.27,0],[xmax+span*.27,ymin-span*.27,0],[xmax+span*.27,ymax+span*.27,0],[xmin-span*.27,ymax+span*.27,0]];
        const fitPoints = [...ground, ...meshes.flatMap((mesh) => mesh.points), e.center];
        if (this.expanded) fitPoints.push([...e.reaction_point, 0], ...this.result.free_body.forces.filter((force) => Math.hypot(...force.vector)>1e-8).map((force) => force.point));
        const bounds = fitPoints.map(raw);
        const left = Math.min(...bounds.map((p) => p[0])), rightBound = Math.max(...bounds.map((p) => p[0]));
        const top = Math.min(...bounds.map((p) => p[1])), bottom = Math.max(...bounds.map((p) => p[1]));
        const scale = Math.min((width - 108) / Math.max(rightBound-left, .001), (height-(this.expanded ? 125 : 75)) / Math.max(bottom-top, .001));
        const project = (point) => { const p = raw(point); return [width/2 + (p[0]-(left+rightBound)/2)*scale, (height-30)/2 + (p[1]-(top+bottom)/2)*scale]; };
        const coordinates = (points) => points.map((point) => project(point).join(',')).join(' ');
        let svg = this.definitions('model');
        svg += `<polygon points="${coordinates(ground)}" fill="var(--model-ground)" stroke="var(--border-color)"/>`;
        for (let i = 1; this.expanded && i < 5; i++) {
            const x = ground[0][0] + (ground[1][0]-ground[0][0])*i/5;
            const y = ground[0][1] + (ground[3][1]-ground[0][1])*i/5;
            svg += this.line(project([x,ground[0][1],0]),project([x,ground[3][1],0]),'stroke="var(--border-color)" stroke-width=".6"');
            svg += this.line(project([ground[0][0],y,0]),project([ground[1][0],y,0]),'stroke="var(--border-color)" stroke-width=".6"');
        }
        svg += `<polygon points="${coordinates(polygon.map(([x,y]) => [x,y,0]))}" fill="none" stroke="var(--text-light)" stroke-dasharray="3 3"/>`;
        svg += meshes.sort((a,b) => a.depth-b.depth).map((mesh) => `<polygon points="${coordinates(mesh.points)}" fill="${mesh.fill}" stroke="var(--secondary-color)" stroke-width=".45" ${mesh.extra}/>`).join('');
        for (const edge of e.edges) {
            const a = project([...edge.start,0]), b = project([...edge.end,0]);
            const active = this.expanded && edge.id === this.edge;
            svg += `<g data-diagram-edge="${edge.id}"><title>${this.escape(edge.label)}: select its FBD</title>${this.line(a,b,`stroke="var(--text-light)" stroke-width="1.2" ${active ? 'class="edge-active"' : ''}`)}${this.line(a,b,'class="edge-hit"')}${this.expanded && (e.edges.length <= 8 || active) ? this.label((a[0]+b[0])/2,(a[1]+b[1])/2+15,edge.id, active ? 'font-weight="700"' : '') : ''}</g>`;
        }
        contacts.forEach((point, index) => {
            const p = project([...point,0]);
            svg += `<circle cx="${p[0]}" cy="${p[1]}" r="3" fill="var(--bg-card)" stroke="var(--text-color)"/>`;
            if (this.expanded && contacts.length <= 8) svg += this.label(p[0]-8,p[1]+5,`C${index+1}`,'text-anchor="end"');
        });
        const center = project(e.center), foot = project([e.center[0],e.center[1],0]);
        svg += this.line(center,foot,'class="leader"');
        const selected = e.edges.find((edge) => edge.id === this.edge);
        const section = this.result.free_body.sections[this.edge];
        const edgeFoot = [e.center[0]-section.center[0]*selected.normal[0],e.center[1]-section.center[0]*selected.normal[1],0];
        const inward = [edgeFoot[0]+selected.normal[0]*span*.22,edgeFoot[1]+selected.normal[1]*span*.22,0];
        const inwardStart = project(edgeFoot), inwardEnd = project(inward);
        if (this.expanded) {
            svg += this.line(inwardStart,inwardEnd,'stroke="var(--warning-color)" stroke-width="1.4" marker-end="url(#model-arrow)"');
            svg += this.label(inwardEnd[0]+6,inwardEnd[1]+10,'u');
        }
        for (const force of this.expanded ? this.result.free_body.forces : []) {
            if (Math.hypot(...force.vector) < 1e-8) continue;
            const direction = raw(force.vector);
            const norm = Math.hypot(direction[0],direction[1]);
            if (norm < 1e-8) continue;
            const size = force.id === 'W' || force.id === 'N' ? 45 : 39;
            const offset = force.id === 'W' ? [-10,0] : force.id === 'N' ? [10,0] : [0,0];
            svg += this.arrow(project(force.point), [direction[0]/norm*size,direction[1]/norm*size], force, 'model', [0,0], offset);
        }
        svg += this.centerGlyph(center, this.expanded ? 'G' : 'Center of mass');
        if (this.expanded && components.length > 1 && components.length <= 8) components.forEach((component,index) => {
            const p = project([component.x,component.y,component.z]);
            svg += `<circle cx="${p[0]}" cy="${p[1]}" r="2.5" fill="var(--text-color)"/>` + this.label(p[0]+10,p[1]-8,`m${index+1}`);
        });
        const reaction = project([...e.reaction_point,0]);
        if (this.expanded) svg += `<path d="M${reaction[0]},${reaction[1]-5} l5,5 l-5,5 l-5,-5 z" fill="var(--bg-card)" stroke="var(--text-color)" data-entity="N"/>`;
        // Camera-independent axis triad. Directions rotate with the inclined surface.
        const origin = [43,height-38];
        for (const [basis,label] of this.expanded ? [[[1,0,0],'x'],[[0,1,0],'y'],[[0,0,1],'z']] : [[[1,0,0],'Forward']]) {
            const vector = raw(basis), p = [origin[0]+vector[0]*25, origin[1]+vector[1]*25];
            svg += this.line(origin,p,'stroke="var(--text-light)" stroke-width="1" marker-end="url(#model-arrow)"') + this.label(p[0]+4,p[1],label);
        }
        if (this.expanded) {
            svg += this.label(width-12,height-17,custom ? `${contacts.length} fixed contacts` : `L ${this.number(length)} m · B ${this.number(track)} m`,'text-anchor="end"');
            svg += `<text x="12" y="17" class="small-label">Ground ${this.number(this.inputs.slope_deg || 0)}° · x forward / y left / z normal</text>`;
        } else svg += this.label(width-12,height-17,`Center height ${this.number(e.center[2])} m`,'text-anchor="end"');
        this.model.innerHTML = svg;
        this.model.dataset.edge = this.edge;
        this.model.dataset.slope = String(this.inputs.slope_deg || 0);
    }

    centerGlyph(point, label = 'G') {
        return `<g data-entity="G"><title>G: combined center of mass</title><circle class="entity-mark" cx="${point[0]}" cy="${point[1]}" r="6" fill="var(--bg-card)" stroke="var(--text-color)" stroke-width="1.8"/><path d="M${point[0]-4},${point[1]} h8 M${point[0]},${point[1]-4} v8" stroke="var(--text-color)"/>${this.label(point[0]+10,point[1]-10,label,'font-weight="700"')}</g>`;
    }

    renderFbd() {
        const e = this.result.equilibrium;
        const section = this.result.free_body.sections[this.edge];
        const edge = e.edges.find((item) => item.id === this.edge);
        const width = Math.max(280,this.fbd.clientWidth), height = this.fbd.clientHeight || 340;
        this.fbd.setAttribute('viewBox',`0 0 ${width} ${height}`);
        document.getElementById('fbd-subtitle').textContent = `${edge.label} · looking along the edge`;
        const componentPoints = this.result.mass_components.map((component) => [(component.x-edge.start[0])*edge.normal[0]+(component.y-edge.start[1])*edge.normal[1],component.z]);
        const points = [[0,0],[section.support_span,0],section.center,section.reaction,...componentPoints,...section.forces.filter((f) => Math.hypot(...f.vector, f.out_of_plane)>1e-8).map((f) => f.point)];
        const min = Math.min(...points.map((p) => p[0])), max = Math.max(...points.map((p) => p[0]));
        const maxZ = Math.max(...points.map((p) => p[1]), .001);
        const scale = Math.min((width-145)/Math.max(max-min,.001),(height-155)/maxZ);
        const originX = (width-(max-min)*scale)/2-min*scale;
        const groundY = height-91;
        const project = (point) => [originX+point[0]*scale,groundY-point[1]*scale];
        const pivot = project([0,0]), center = project(section.center), reaction = project(section.reaction);
        let svg = this.definitions('fbd');
        const outlineLeft = project([min,0])[0], outlineRight = project([max,0])[0];
        const bodyTop = Math.max(42,project([0,maxZ])[1]-18);
        svg += `<rect x="${outlineLeft}" y="${bodyTop}" width="${Math.max(3,outlineRight-outlineLeft)}" height="${Math.max(4,groundY-bodyTop)}" rx="8" fill="var(--model-ground)" stroke="var(--text-light)" stroke-width="1" stroke-dasharray="4 4"/>`;
        svg += `<text x="${width/2}" y="20" text-anchor="middle" class="small-label">Whole assembly · forces in N · distances in m</text>`;
        svg += this.line([20,groundY],[width-20,groundY],'class="leader"');
        svg += this.line(center,project([section.center[0],0]),'class="leader"');
        // Arrow tails may be separated by a dotted leader; exact points remain marked.
        for (const force of this.result.free_body.forces) {
            if (Math.hypot(...force.vector)<1e-8) continue;
            const projected = section.forces.find((item) => item.id === force.id);
            const norm = Math.hypot(...projected.vector);
            const point = project(projected.point);
            if (norm > 1e-8) {
                const size = force.id === 'W' || force.id === 'N' ? 48 : 42;
                const direction = [projected.vector[0]/norm*size,-projected.vector[1]/norm*size];
                const offset = force.id === 'W' ? [-12,0] : force.id === 'N' ? [12,0] : force.id === 'T' ? [0,9] : [0,0];
                svg += this.arrow(point,direction,force,'fbd',[0,0],offset);
            }
            if (Math.abs(projected.out_of_plane)>1e-7 && norm<1e-8) {
                svg += `<g data-entity="${force.id}"><title>${this.escape(force.name)} acts along the edge, outside this projection.</title><circle cx="${point[0]-18}" cy="${point[1]+17}" r="7" fill="var(--bg-card)" stroke="var(--text-color)"/><text x="${point[0]-18}" y="${point[1]+21}" text-anchor="middle">${projected.out_of_plane>0 ? '•' : '×'}</text>${this.label(point[0]-29,point[1]+21,force.id,'text-anchor="end"')}</g>`;
            }
        }
        svg += this.centerGlyph(center);
        if (componentPoints.length > 1 && componentPoints.length <= 8) componentPoints.forEach((point,index) => {
            const p = project(point);
            svg += `<circle cx="${p[0]}" cy="${p[1]}" r="2.5" fill="var(--text-color)"/>` + this.label(p[0]+10,p[1]-7,`m${index+1}`);
        });
        svg += `<g data-diagram-edge="${this.edge}"><circle cx="${pivot[0]}" cy="${pivot[1]}" r="5" fill="var(--warning-color)"/>${this.label(pivot[0]-6,pivot[1]-10,this.edge,'text-anchor="end" font-weight="700"')}</g>`;
        svg += `<path d="M${reaction[0]},${reaction[1]-4} l4,4 l-4,4 l-4,-4 z" fill="var(--bg-card)" stroke="var(--text-color)" data-entity="N"/>`;
        const dimension = (a,b,text,x,y) => this.line(a,b,'class="dimension" marker-start="url(#fbd-dim)" marker-end="url(#fbd-dim)"') + this.label(x,y,text,'text-anchor="middle"');
        const dimensionX = Math.max(22,Math.min(pivot[0],center[0])-32);
        svg += dimension([dimensionX,groundY],[dimensionX,center[1]],`h ${this.number(section.center[1])} m`,dimensionX,center[1]-12);
        svg += dimension([pivot[0],groundY+25],[center[0],groundY+25],`dG ${this.number(section.center[0])} m`,(pivot[0]+center[0])/2,groundY+42);
        svg += dimension([pivot[0],groundY+51],[reaction[0],groundY+51],`dR ${this.number(section.reaction[0])} m`,(pivot[0]+reaction[0])/2,groundY+67);
        svg += this.line([width-54,groundY-20],[width-25,groundY-20],'class="dimension" marker-end="url(#fbd-arrow)"') + this.label(width-15,groundY-17,'u');
        svg += this.line([width-54,groundY-20],[width-54,groundY-49],'class="dimension" marker-end="url(#fbd-arrow)"') + this.label(width-49,groundY-49,'z');
        this.fbd.innerHTML = svg;
        this.fbd.dataset.edge = this.edge;
        const outOfPlane = section.forces.some((force) => Math.abs(force.out_of_plane) > 1e-7);
        const note = document.getElementById('fbd-projection-note');
        note.hidden = !outOfPlane;
        note.textContent = 'Some force components act along the edge, outside this view. Select a force to inspect them. ⊙ toward you; ⊗ away.';
    }

    renderKey() {
        const e = this.result.equilibrium;
        let html = `<button type="button" data-entity="G" aria-pressed="false"><b>G</b><span>Mass center</span><strong>${this.number(e.mass)} kg</strong></button>`;
        for (const force of this.result.free_body.forces) {
            const magnitude = Math.hypot(...force.vector);
            const title = force.id === 'N' ? 'Normal reaction' : force.id === 'T' ? 'Tangential reaction' : force.name;
            html += `<button type="button" data-entity="${force.id}" aria-pressed="false" class="${magnitude<1e-8 ? 'is-zero' : ''}" title="${this.escape(force.name)}"><b>${force.id}</b><span>${this.escape(title)}</span><strong>${this.number(magnitude)} N</strong></button>`;
        }
        this.key.innerHTML = html;
        const couple = this.result.free_body.contact_couple[2];
        document.getElementById('fbd-contact-note').textContent = `Required ground yaw couple: ${this.number(couple)} N·m about +z, in addition to N and T at the reaction point. Forces along the edge and this yaw couple are outside the FBD projection. Individual wheel loads, traction distribution, and yaw capacity are not verified. dG is the mass-center distance from the edge; dR is the required reaction distance. A negative dR lies outside that edge.`;
    }

    inspect() {
        if (!this.result) return;
        const e = this.result.equilibrium;
        const section = this.result.free_body.sections[this.edge];
        const inspector = document.getElementById('diagram-inspector');
        if (this.entity === 'G') {
            const components = this.result.mass_components;
            const componentText = components.length > 1 ? `<p>${components.length <= 8 ? components.map((component,index) => `m${index+1}: ${this.escape(component.name)}, ${this.number(component.mass)} kg`).join('; ') + '.' : `${components.length} mass components; the first 16 are drawn as illustrative blocks.`}</p>` : '';
            inspector.innerHTML = `<strong>G · combined center of mass</strong><p>${this.number(e.mass)} kg at ${this.vector(e.center)} m in (x, y, z). In this FBD: ${this.vector(section.center)} m in (u, z).</p><p>Distance to the edge dG = ${this.number(section.center[0])} m. Required reaction distance dR = ${this.number(section.reaction[0])} m. Moment reserve about ${this.edge}: ${this.number(section.reserve)} N·m.</p>${componentText}`;
            return;
        }
        const force = this.result.free_body.forces.find((item) => item.id === this.entity);
        const projected = section.forces.find((item) => item.id === this.entity);
        inspector.innerHTML = `<strong>${this.escape(force.id)} · ${this.escape(force.name)} · ${this.number(Math.hypot(...force.vector))} N</strong><p>3D force ${this.vector(force.vector)} N at ${this.vector(force.point)} m.</p><p>FBD components (Fu, Fz) = ${this.vector(projected.vector)} N at (u, z) = ${this.vector(projected.point)} m. Along the edge, outside this view: ${this.number(projected.out_of_plane)} N.</p><p>${force.kind==='reaction' ? 'Required ground-force' : 'Restoring'} moment about ${this.edge}: ${this.number(projected.restoring_moment)} N·m.${force.id==='I' ? ' Equivalent inertia acts opposite to actual acceleration.' : ''}</p>`;
    }
};
