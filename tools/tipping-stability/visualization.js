/* Surface-fixed footprint and linked FBD. Force balance/projections come from Python. */
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
        this.model.addEventListener('keydown', (event) => {
            const edge = event.target.closest('[data-diagram-edge]');
            if (!edge || !['Enter',' '].includes(event.key)) return;
            event.preventDefault();
            edge.dispatchEvent(new MouseEvent('click', {bubbles:true}));
        });
        let previousWidth = 0;
        new ResizeObserver(([entry]) => {
            if (Math.abs(entry.contentRect.width - previousWidth) < 1 || !this.result) return;
            previousWidth = entry.contentRect.width;
            this.draw();
        }).observe(document.querySelector('.visual-pair'));
        this.setExpanded(true);
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
            const selected = this.expanded && (element.dataset.entity === entity || (element.dataset.linkedEntities || '').split(' ').includes(entity));
            element.classList.toggle('linked-active', selected);
            if (element.tagName === 'BUTTON') element.setAttribute('aria-pressed', String(selected));
        }
        // A load can share its plan position with G₀ or R. Draw its selection
        // ring last so the mass-center glyph cannot hide the selected location.
        this.model.querySelector('.application-focus')?.remove();
        const pointId = ['W','I'].includes(entity) ? 'G' : ['N','T'].includes(entity) ? 'R' : entity;
        const point = this.model.querySelector(`[data-point="${pointId}"]`);
        if (this.expanded && entity !== 'G' && point) {
            const ring = document.createElementNS('http://www.w3.org/2000/svg','circle');
            for (const [key,value] of Object.entries({cx:point.getAttribute('cx'),cy:point.getAttribute('cy'),r:11,class:'application-focus',fill:'none',stroke:'var(--warning-color)','stroke-width':1.5,'pointer-events':'none'})) ring.setAttribute(key,String(value));
            this.model.append(ring);
        }
        this.inspect();
    }

    draw() {
        if (!this.result) return;
        const focusedEdge = this.model.contains(document.activeElement) ? document.activeElement.dataset.diagramEdge : null;
        this.renderFootprint();
        this.arrangeLabels(this.model);
        if (this.expanded) {
            this.renderFbd();
            this.arrangeLabels(this.fbd);
            this.renderKey();
        }
        this.select(this.entity);
        if (focusedEdge) this.model.querySelector(`[data-diagram-edge="${focusedEdge}"]`)?.focus({preventScroll:true});
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

    arrow(origin, vector, force) {
        const magnitude = Math.hypot(...vector);
        if (magnitude < 1e-9) return '';
        // Applied-force tails and reaction heads meet the exact physical point.
        // Labels may move; an arrow must never move sideways off its line of action.
        const reaction = force.kind === 'reaction';
        const start = reaction ? origin.map((value, i) => value - vector[i]) : origin;
        const end = reaction ? origin : origin.map((value, i) => value + vector[i]);
        const labelAnchor = reaction ? start : end;
        const outward = vector.map((value) => reaction ? -value : value);
        const labelX = labelAnchor[0] + (outward[0] < -1 ? -8 : 8);
        const labelY = labelAnchor[1] + (outward[1] > 1 ? 12 : -6);
        const name = this.escape(force.id);
        const unit = vector.map((value) => value / magnitude);
        const head = [end, [end[0]-unit[0]*8-unit[1]*4,end[1]-unit[1]*8+unit[0]*4], [end[0]-unit[0]*8+unit[1]*4,end[1]-unit[1]*8-unit[0]*4]].map((point) => point.join(',')).join(' ');
        return `<g class="force-arrow ${force.kind}" data-entity="${name}" aria-label="${this.escape(force.name)}"><title>${this.escape(force.name)}: ${this.number(Math.hypot(...force.vector))} N</title>${this.line(start, end, 'class="force-shaft" stroke="currentColor" stroke-width="2"')}<polygon points="${head}" fill="currentColor"/>${this.line(start, end, 'stroke="transparent" stroke-width="15"')}<text x="${labelX}" y="${labelY}" data-callout-x="${labelAnchor[0]}" data-callout-y="${labelAnchor[1]}" text-anchor="${outward[0] < -1 ? 'end' : 'start'}" class="force-label diagram-label">${name}</text></g>`;
    }

    definitions(prefix) {
        return `<defs><marker id="${prefix}-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="context-stroke"/></marker><marker id="${prefix}-dim" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto-start-reverse"><path d="M0,0 L6,3 L0,6" fill="none" stroke="var(--text-light)" stroke-width=".8"/></marker></defs>`;
    }

    renderFootprint() {
        const e = this.result.equilibrium;
        const width = Math.max(280,this.model.clientWidth), height = this.model.clientHeight || 340;
        this.model.setAttribute('viewBox',`0 0 ${width} ${height}`);
        const contacts = Array.isArray(this.inputs.contacts) ? this.inputs.contacts : e.polygon;
        const applied = this.expanded ? this.result.free_body.forces.filter((force) => force.id.startsWith('P') && Math.hypot(...force.vector)>1e-8) : [];
        const points = [...contacts,e.center,e.reaction_point,...applied.map((force) => force.point)];
        const min = [0,1].map((axis) => Math.min(...points.map((point) => point[axis])));
        const max = [0,1].map((axis) => Math.max(...points.map((point) => point[axis])));
        // Surface-fixed plan: front (+x) is always up, left (+y) always left.
        // Slope changes the reaction and downhill cue, never the footprint's shape.
        const scale = Math.min((width-150)/Math.max(max[1]-min[1],.001),(height-132)/Math.max(max[0]-min[0],.001));
        const project = (point) => [width/2-(point[1]-(min[1]+max[1])/2)*scale,(height-46)/2-(point[0]-(min[0]+max[0])/2)*scale];
        const outline = e.polygon.map((point) => project(point).join(',')).join(' ');
        let svg = this.definitions('model');
        svg += `<polygon class="support-outline" points="${outline}" fill="var(--model-ground)" stroke="var(--text-light)" stroke-width="1"/>`;
        for (const edge of e.edges) {
            const a = project(edge.start), b = project(edge.end), active = edge.id === this.edge;
            const midpoint = [(a[0]+b[0])/2,(a[1]+b[1])/2];
            const outward = [edge.normal[1],edge.normal[0]];
            const label = this.label(midpoint[0]+outward[0]*16,midpoint[1]+outward[1]*19+4,
                edge.label,`text-anchor="${outward[0]<-.5 ? 'end' : outward[0]>.5 ? 'start' : 'middle'}" ${active ? 'font-weight="700"' : ''}`);
            svg += `<g data-diagram-edge="${edge.id}" tabindex="0" role="button" aria-label="Inspect ${this.escape(edge.label)}" aria-pressed="${active}"><title>${this.escape(edge.label)}: select its section</title>${this.line(a,b,`stroke="var(--text-light)" stroke-width="1.2" ${active ? 'class="edge-active"' : ''}`)}${this.line(a,b,'class="edge-hit"')}${e.edges.length<=8 || active ? label : ''}</g>`;
        }
        contacts.forEach((point) => {
            const p = project(point);
            svg += `<circle class="contact-point" cx="${p[0]}" cy="${p[1]}" r="3" fill="var(--bg-card)" stroke="var(--text-color)" pointer-events="none"/>`;
        });
        for (const force of applied) {
            const point = project(force.point);
            svg += `<g data-entity="${force.id}"><title>${this.escape(force.name)}: application point projected onto the support plane</title><circle class="entity-mark" data-point="${force.id}" cx="${point[0]}" cy="${point[1]}" r="3" fill="var(--bg-card)" stroke="var(--text-color)"/>${this.label(point[0]+9,point[1]+17,force.id)}</g>`;
        }
        const center = project(e.center), reaction = project(e.reaction_point);
        const coincide = Math.hypot(center[0]-reaction[0],center[1]-reaction[1]) < 10;
        if (!coincide) svg += this.line(center,reaction,'class="leader"');
        svg += `<g data-entity="N" data-linked-entities="N T"><title>R: required ground-reaction point</title><circle class="entity-mark reaction-point" data-point="R" data-outside="${e.margin < -1e-8}" cx="${reaction[0]}" cy="${reaction[1]}" r="7" fill="none" stroke="var(--text-color)" stroke-width="1.5"/>${coincide ? '' : this.label(reaction[0]-10,reaction[1]+18,'R','text-anchor="end" font-weight="700"')}</g>`;
        svg += this.centerGlyph(center,coincide ? 'G₀ / R' : 'G₀','G W I');
        const slope = this.inputs.slope_deg || 0;
        const phi = (this.inputs.downhill_deg ?? 90)*Math.PI/180;
        if (slope > 1e-8) {
            const origin = [47,height-39], end = [origin[0]-Math.sin(phi)*27,origin[1]-Math.cos(phi)*27];
            svg += this.line(origin,end,'class="downhill-direction" stroke="var(--text-color)" stroke-width="1.5" marker-end="url(#model-arrow)"');
            svg += `<text x="89" y="${height-43}" class="small-label">Downhill</text><text x="89" y="${height-26}" class="small-label">Ground ${this.number(slope)}°</text>`;
        } else svg += `<text x="18" y="${height-30}" class="small-label">Level ground</text>`;
        svg += `<text x="${width-14}" y="${height-30}" text-anchor="end" class="small-label">G height ${this.number(e.center[2])} m</text>`;
        this.model.innerHTML = svg;
        this.model.dataset.edge = this.edge;
        this.model.dataset.slope = String(slope);
    }

    centerGlyph(point, label = 'G', linkedEntities = '') {
        return `<g data-entity="G" data-linked-entities="${linkedEntities}"><title>${label.includes('G₀') ? 'G₀: combined mass center projected onto the support plane' : 'G: combined center of mass'}</title><circle class="entity-mark" data-point="G" cx="${point[0]}" cy="${point[1]}" r="6" fill="var(--bg-card)" stroke="var(--text-color)" stroke-width="1.8"/><path d="M${point[0]-4},${point[1]} h8 M${point[0]},${point[1]-4} v8" stroke="var(--text-color)"/>${this.label(point[0]+10,point[1]-10,label,'font-weight="700"')}</g>`;
    }

    reactionGlyph(point) {
        return `<g data-entity="N"><title>R: required ground-reaction point</title><circle class="entity-mark" data-point="R" cx="${point[0]}" cy="${point[1]}" r="4" fill="var(--bg-card)" stroke="var(--text-color)" stroke-width="1.5"/>${this.label(point[0]-10,point[1]+18,'R','text-anchor="end" font-weight="700"')}</g>`;
    }

    renderFbd() {
        const e = this.result.equilibrium;
        const section = this.result.free_body.sections[this.edge];
        const edge = e.edges.find((item) => item.id === this.edge);
        const width = Math.max(280,this.fbd.clientWidth), height = this.fbd.clientHeight || 340;
        this.fbd.setAttribute('viewBox',`0 0 ${width} ${height}`);
        document.getElementById('fbd-subtitle').textContent = `${edge.label} · looking along the edge`;
        const forces = section.forces.map((force) => ({...this.result.free_body.forces.find((item) => item.id === force.id), ...force}))
            .filter((force) => Math.hypot(...force.vector, force.out_of_plane) > 1e-8);
        // Study B: rotate the whole edge-normal section until projected gravity
        // points down. This apparent incline can differ from the entered slope.
        const weight = section.forces.find((force) => force.id === 'W');
        const angle = Math.atan2(weight.vector[0], -weight.vector[1]);
        const rotate = ([u,z]) => [u*Math.cos(angle)+z*Math.sin(angle), u*Math.sin(angle)-z*Math.cos(angle)];
        const componentPoints = this.result.mass_components.map((component) => [(component.x-edge.start[0])*edge.normal[0]+(component.y-edge.start[1])*edge.normal[1],component.z]);
        const points = [section.center,section.reaction,...componentPoints,...forces.map((force) => force.point)];
        const minU = Math.min(0,...points.map((point) => point[0]));
        const maxU = Math.max(section.support_span,...points.map((point) => point[0]));
        const top = Math.max(section.center[1]+.13,...points.map((point) => point[1]+.04));
        const shell = [[0,0],[section.support_span,0],[section.support_span,top],[0,top]];
        const ground = [[minU-section.support_span*.1,0],[maxU+section.support_span*.1,0]];
        const arrowLength = Math.min(56,width*.18);
        const direction = (force) => rotate(force.vector).map((value) => value/Math.hypot(...force.vector)*arrowLength);

        // Fit physical geometry and fixed-pixel arrow ends together. In particular,
        // include reaction tails and reactions outside the footprint after tipping.
        const fitting = [...shell,...ground,...points].map((point) => ({point:rotate(point), offset:[0,0]}));
        for (const force of forces) {
            if (Math.hypot(...force.vector) <= 1e-8) continue;
            fitting.push({point:rotate(force.point), offset:direction(force).map((value) => force.kind === 'reaction' ? -value : value)});
        }
        const bounds = (scale) => {
            const screen = fitting.map(({point,offset}) => point.map((value,i) => value*scale+offset[i]));
            return {left:Math.min(...screen.map((point) => point[0])), right:Math.max(...screen.map((point) => point[0])),
                top:Math.min(...screen.map((point) => point[1])), bottom:Math.max(...screen.map((point) => point[1]))};
        };
        const area = {left:30,right:width-30,top:38,bottom:height-78};
        const rotated = fitting.map(({point}) => point);
        const range = [0,1].map((axis) => Math.max(...rotated.map((point) => point[axis]))-Math.min(...rotated.map((point) => point[axis])));
        let lo = 0, hi = Math.min((area.right-area.left)/Math.max(range[0],.001),(area.bottom-area.top)/Math.max(range[1],.001));
        for (let i=0;i<28;i++) {
            const trial = (lo+hi)/2, box = bounds(trial);
            if (box.right-box.left <= area.right-area.left && box.bottom-box.top <= area.bottom-area.top) lo = trial;
            else hi = trial;
        }
        const scale = lo, box = bounds(scale);
        const offset = [(area.left+area.right-box.left-box.right)/2,(area.top+area.bottom-box.top-box.bottom)/2];
        const project = (point) => rotate(point).map((value,i) => value*scale+offset[i]);
        const pivot = project([0,0]), center = project(section.center), reaction = project(section.reaction);
        let svg = this.definitions('fbd');
        svg += `<polygon class="assembly-outline" points="${shell.map((point) => project(point).join(',')).join(' ')}" fill="var(--model-ground)" stroke="var(--text-light)" stroke-width="1"/>`;
        svg += `<text x="${width/2}" y="18" text-anchor="middle" class="small-label">Weight vertical · schematic arrows</text>`;
        svg += this.line(...ground.map(project),'class="dimension"');
        const hatch = rotate([-.022,-.025]).map((value) => value*scale);
        for (let i=0;i<=18;i++) {
            const start = project([section.support_span*i/18,0]);
            svg += this.line(start,start.map((value,axis) => value+hatch[axis]),'class="dimension"');
        }
        svg += this.line(pivot,project([section.support_span,0]),'class="support-line" stroke="var(--text-color)" stroke-width="2"');
        svg += this.line(center,project([section.center[0],0]),'class="leader"');
        for (const force of forces) {
            const point = project(force.point);
            if (Math.hypot(...force.vector) > 1e-8) {
                const original = this.result.free_body.forces.find((item) => item.id === force.id);
                svg += this.arrow(point,direction(force),original);
            }
            if (force.id.startsWith('P')) svg += `<circle data-point="${force.id}" cx="${point[0]}" cy="${point[1]}" r="3" fill="var(--bg-card)" stroke="var(--text-color)"/>`;
        }
        svg += this.centerGlyph(center);
        if (componentPoints.length > 1 && componentPoints.length <= 8) componentPoints.forEach((point,index) => {
            const p = project(point);
            svg += `<circle cx="${p[0]}" cy="${p[1]}" r="2.5" fill="var(--text-color)"/>` + this.label(p[0]+10,p[1]-7,`m${index+1}`);
        });
        svg += `<g data-diagram-edge="${this.edge}"><circle cx="${pivot[0]}" cy="${pivot[1]}" r="4" fill="var(--warning-color)"/>${this.label(pivot[0]-8,pivot[1]-10,this.edge,'text-anchor="end" font-weight="700"')}</g>`;
        svg += this.reactionGlyph(reaction);
        for (const force of forces.filter((item) => Math.hypot(...item.vector) <= 1e-8)) {
            const point = project(force.point);
            const mark = force.out_of_plane > 0 ? `<circle cx="${point[0]}" cy="${point[1]}" r="2" fill="currentColor"/>`
                : `<path d="M${point[0]-3},${point[1]-3} l6,6 M${point[0]-3},${point[1]+3} l6,-6" stroke="currentColor"/>`;
            svg += `<g class="force-arrow ${force.kind}" data-entity="${force.id}"><title>${this.escape(force.name)} acts along the edge, outside this projection.</title><circle class="out-of-plane" cx="${point[0]}" cy="${point[1]}" r="7" fill="var(--bg-card)" stroke="currentColor"/>${mark}<text x="${point[0]+12}" y="${point[1]+20}" data-callout-x="${point[0]}" data-callout-y="${point[1]}" class="force-label diagram-label">${force.id}</text></g>`;
        }
        const axisOrigin = [width-51,height-39];
        for (const [vector,name] of [[[1,0],'u'],[[0,1],'z']]) {
            const end = rotate(vector).map((value,i) => axisOrigin[i]+value*25);
            svg += this.line(axisOrigin,end,'class="dimension" marker-end="url(#fbd-arrow)"') + this.label(end[0]+6,end[1]+3,name);
        }
        this.fbd.innerHTML = svg;
        this.fbd.dataset.edge = this.edge;
        document.getElementById('fbd-incline').textContent = `Apparent incline ${this.number(Math.abs(angle*180/Math.PI))}°`;
        const distance = document.getElementById('fbd-reaction-distance');
        distance.textContent = `R from edge ${this.number(section.reaction[0])} m`;
        distance.dataset.outside = String(section.reaction[0] < -1e-8);
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
            const componentText = components.length > 1 ? `<p>${components.length <= 8 ? components.map((component,index) => `m${index+1}: ${this.escape(component.name)}, ${this.number(component.mass)} kg`).join('; ') + '.' : `${components.length} mass components contribute to G.`}</p>` : '';
            inspector.innerHTML = `<strong>G · combined center of mass</strong><p>${this.number(e.mass)} kg at ${this.vector(e.center)} m in (x, y, z). In this FBD: ${this.vector(section.center)} m in (u, z).</p><p>Distance to the edge dG = ${this.number(section.center[0])} m. Required reaction distance dR = ${this.number(section.reaction[0])} m. Moment reserve about ${this.edge}: ${this.number(section.reserve)} N·m.</p>${componentText}`;
            return;
        }
        const force = this.result.free_body.forces.find((item) => item.id === this.entity);
        const projected = section.forces.find((item) => item.id === this.entity);
        inspector.innerHTML = `<strong>${this.escape(force.id)} · ${this.escape(force.name)} · ${this.number(Math.hypot(...force.vector))} N</strong><p>3D force ${this.vector(force.vector)} N at ${this.vector(force.point)} m.</p><p>FBD components (Fu, Fz) = ${this.vector(projected.vector)} N at (u, z) = ${this.vector(projected.point)} m. Along the edge, outside this view: ${this.number(projected.out_of_plane)} N.</p><p>${force.kind==='reaction' ? 'Required ground-force' : 'Restoring'} moment about ${this.edge}: ${this.number(projected.restoring_moment)} N·m.${force.id==='I' ? ' Equivalent inertia acts opposite to actual acceleration.' : ''}</p>`;
    }
};
