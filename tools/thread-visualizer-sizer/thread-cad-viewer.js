/* Lazy display of a mesh reimported from the downloadable STEP. No CAD math here. */
import * as THREE from './vendor/three-0.180.0/three.module.min.js';
import { OrbitControls } from './vendor/three-0.180.0/OrbitControls.js';

export function createCADViewer(host, mesh, model, onLost) {
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, stencil: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    renderer.localClippingEnabled = true;
    renderer.setClearColor(0, 0);
    const canvas = renderer.domElement;
    canvas.tabIndex = 0;
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', 'Interactive representative solid: ' + model.step_name);
    canvas.setAttribute('aria-describedby', 'step-view-help');
    host.replaceChildren(canvas);
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 10000);
    camera.up.set(0, 0, 1);
    const target = new THREE.Vector3(0, 0, model.length_mm / 2);
    const span = Math.max(model.length_mm, model.specimen === 'internal' ? model.body_diameter_mm : model.major_diameter_mm);
    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = false;
    controls.minZoom = 0.15; controls.maxZoom = 20;
    controls.target.copy(target);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(mesh.vertices, 3));
    geometry.setAttribute('normal', new THREE.Float32BufferAttribute(mesh.normals, 3));
    geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(mesh.triangles), 1));
    geometry.computeBoundingSphere();
    const material = new THREE.MeshStandardMaterial({ metalness: 0.18, roughness: 0.5 });
    const solid = new THREE.Mesh(geometry, material); solid.renderOrder = 4;
    scene.add(solid);
    const edgeGeometry = new THREE.BufferGeometry();
    edgeGeometry.setAttribute('position', new THREE.Float32BufferAttribute(mesh.edges, 3));
    const edgeMaterial = new THREE.LineBasicMaterial({ transparent: true, opacity: 0.48 });
    const edges = new THREE.LineSegments(edgeGeometry, edgeMaterial);
    edges.visible = false; edges.renderOrder = 5; scene.add(edges);
    const ambient = new THREE.AmbientLight(0xffffff, 1.5);
    const key = new THREE.DirectionalLight(0xffffff, 2.6);
    key.position.set(span * 2, -span * 3, span * 4);
    const fill = new THREE.DirectionalLight(0xffffff, 1.2);
    fill.position.set(-span * 2, span, -span);
    scene.add(ambient, key, fill);

    // Stencil cap follows the closed solid's cross-section. See the Three.js
    // clipping-stencil example linked with its MIT notice in vendor/NOTICE.md.
    const plane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0);
    const section = new THREE.Group(); section.visible = false;
    const sectionMaterials = [];
    for (const [side, operation] of [[THREE.BackSide, THREE.IncrementWrapStencilOp], [THREE.FrontSide, THREE.DecrementWrapStencilOp]]) {
        const stencil = new THREE.MeshBasicMaterial({ side, depthWrite: false, depthTest: false,
            colorWrite: false, stencilWrite: true, stencilFunc: THREE.AlwaysStencilFunc,
            stencilFail: operation, stencilZFail: operation, stencilZPass: operation, clippingPlanes: [plane] });
        sectionMaterials.push(stencil);
        const surface = new THREE.Mesh(geometry, stencil); surface.renderOrder = 1;
        section.add(surface);
    }
    const capGeometry = new THREE.PlaneGeometry(span * 3, span * 3);
    const capMaterial = new THREE.MeshStandardMaterial({ roughness: 0.85, metalness: 0,
        side: THREE.DoubleSide, stencilWrite: true, stencilRef: 0, stencilFunc: THREE.NotEqualStencilFunc,
        stencilFail: THREE.ReplaceStencilOp, stencilZFail: THREE.ReplaceStencilOp, stencilZPass: THREE.ReplaceStencilOp });
    const cap = new THREE.Mesh(capGeometry, capMaterial);
    cap.position.copy(target); cap.rotation.y = Math.PI / 2; cap.renderOrder = 2;
    cap.onAfterRender = () => renderer.clearStencil();
    section.add(cap); scene.add(section);
    let disposed = false, frames = 0;
    function render() {
        if (disposed || !host.clientWidth || !host.clientHeight) return;
        renderer.render(scene, camera);
        canvas.dataset.frames = String(++frames);
        canvas.dataset.triangles = String(mesh.triangles.length / 3);
        canvas.dataset.section = String(section.visible);
    }
    function resize() {
        if (disposed || !host.clientWidth) return;
        const width = host.clientWidth, height = host.clientHeight, aspect = width / height;
        const half = span * 0.72 * Math.max(1, 1 / aspect);
        camera.left = -half * aspect; camera.right = half * aspect;
        camera.top = half; camera.bottom = -half;
        camera.far = Math.max(100, span * 50); camera.updateProjectionMatrix();
        renderer.setSize(width, height, false); render();
    }
    function reset() {
        controls.target.copy(target);
        camera.position.copy(target).add(new THREE.Vector3(1.6, -2.5, 1.5).multiplyScalar(span));
        camera.zoom = 1; camera.updateProjectionMatrix(); controls.update(); render();
    }
    function theme() {
        const styles = getComputedStyle(host);
        material.color.set(styles.getPropertyValue('--secondary-color').trim());
        edgeMaterial.color.set(styles.getPropertyValue('--text-color').trim());
        capMaterial.color.set(styles.getPropertyValue('--text-light').trim());
        render();
    }
    const observer = new ResizeObserver(resize); observer.observe(host);
    const themes = new MutationObserver(theme); themes.observe(document.body, { attributes: true, attributeFilter: ['data-theme'] });
    const media = matchMedia('(prefers-color-scheme: dark)'); media.addEventListener('change', theme);
    controls.addEventListener('change', render);
    const keyboard = (event) => {
        if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '=', '-', '_', 'Home'].includes(event.key)) return;
        event.preventDefault();
        if (event.key === 'Home') { reset(); return; }
        if (['+', '=', '-', '_'].includes(event.key)) {
            camera.zoom = THREE.MathUtils.clamp(camera.zoom * (['+', '='].includes(event.key) ? 1.2 : 1 / 1.2), 0.15, 20);
            camera.updateProjectionMatrix();
        } else {
            const offset = camera.position.clone().sub(controls.target);
            const spherical = new THREE.Spherical().setFromVector3(offset.applyAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2));
            if (event.key === 'ArrowLeft') spherical.theta -= .12;
            if (event.key === 'ArrowRight') spherical.theta += .12;
            if (event.key === 'ArrowUp') spherical.phi -= .12;
            if (event.key === 'ArrowDown') spherical.phi += .12;
            spherical.makeSafe();
            offset.setFromSpherical(spherical).applyAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 2);
            camera.position.copy(controls.target).add(offset);
        }
        controls.update(); render();
    };
    const lost = (event) => { event.preventDefault(); if (!disposed) onLost(); };
    canvas.addEventListener('keydown', keyboard);
    canvas.addEventListener('webglcontextlost', lost);
    reset(); resize(); theme();
    return {
        reset,
        edges(value) { edges.visible = value; render(); },
        section(value) {
            section.visible = value;
            material.clippingPlanes = edgeMaterial.clippingPlanes = value ? [plane] : [];
            material.needsUpdate = edgeMaterial.needsUpdate = true;
            render();
        },
        dispose() {
            disposed = true; observer.disconnect(); themes.disconnect(); media.removeEventListener('change', theme);
            canvas.removeEventListener('keydown', keyboard); canvas.removeEventListener('webglcontextlost', lost);
            controls.dispose();
            [geometry, edgeGeometry, capGeometry, material, edgeMaterial, capMaterial, ...sectionMaterials].forEach((item) => item.dispose());
            renderer.dispose(); renderer.forceContextLoss(); canvas.remove();
        },
    };
}
