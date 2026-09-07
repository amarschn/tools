/* Single-threaded OCCT in a dedicated worker. All units are millimetres. */
import initOC from './vendor/replicad-opencascadejs-1.1.0/replicad_single.js';
import * as cad from './vendor/replicad-1.1.0/replicad.js';

let kernel;
const stage = (id, message) => self.postMessage({ id, stage: message });

async function build(model, id, verify, preview) {
    const requested = performance.now();
    const cold = !kernel;
    stage(id, 'Loading CAD kernel');
    kernel ||= initOC({
        locateFile: () => new URL('./vendor/replicad-opencascadejs-1.1.0/replicad_single.wasm', import.meta.url).href,
        print: () => {}, printErr: () => {},
    }).then((oc) => { cad.setOC(oc); return oc; });
    const oc = await kernel;
    const initialization = performance.now() - requested;
    const objects = [];
    const keep = (object) => { objects.push(object); return object; };
    const started = performance.now();
    try {
        stage(id, 'Building helical solid');
        const { pitch_mm: pitch, length_mm: length, major_diameter_mm: diameter } = model;
        if (![pitch, length, diameter].every((n) => Number.isFinite(n) && n > 0) || length / pitch > 20 || length > 250) throw new Error('Invalid or over-limit CAD specimen.');
        const internal = model.specimen === 'internal';
        const overlap = Math.min(pitch / 10, 0.1);
        let points;
        let solid;
        if (internal) {
            const minor = model.internal_minor_mm / 2;
            const halfWidth = model.internal[1][0];
            points = [[-halfWidth, minor - overlap], [-halfWidth, minor],
                [0, model.sharp_radius_mm], [halfWidth, minor], [halfWidth, minor - overlap]];
            const body = keep(cad.makeCylinder(model.body_diameter_mm / 2, length));
            const bore = keep(cad.makeCylinder(minor, length));
            solid = keep(body.cut(bore));
        } else {
            points = model.external.slice(1, -1);
            points = [...points, [points.at(-1)[0], diameter / 2 + overlap], [points[0][0], diameter / 2 + overlap]];
            solid = keep(cad.makeCylinder(diameter / 2, length));
        }
        const path = keep(cad.makeHelix(pitch, length + 2 * pitch, diameter / 2, [0, 0, -pitch], [0, 0, 1], model.hand === 'LH'));
        const edges = points.map(([z, r], i) => {
            const [nextZ, nextR] = points[(i + 1) % points.length];
            return keep(cad.makeLine([r, 0, z - pitch], [nextR, 0, nextZ - pitch]));
        });
        const wire = keep(cad.assembleWire(edges));
        // A circular helix's Frenet frame rotates about Z. Keep the authored
        // axial section oblique to the tangent; correcting it to a normal
        // section would change the intended axial flank angle.
        const groove = keep(cad.genericSweep(wire, path, {
            frenet: true, forceProfileSpineOthogonality: false, withContact: false,
        }));
        // Keep the helical face away from the cylinder's seam. The fuzzy
        // boolean tolerance resolves sweep p-curve approximation (~20 nm to
        // micrometres here); it is a topology tolerance, never a thread fit.
        const rotatedGroove = keep(groove.rotate(23, [0, 0, 0], [0, 0, 1]));
        const cut = keep(new oc.BRepAlgoAPI_Cut(solid.wrapped, rotatedGroove.wrapped));
        cut.SetFuzzyValue(1e-4);
        cut.Build();
        solid = keep(cad.cast(cut.Shape()));
        if (model.end_style === 'chamfer') {
            stage(id, 'Forming finished lead-ins');
            const c = model.chamfer_depth_mm, base = model.envelope_base_radius_mm, tip = model.end_radius_mm;
            const [start, end] = model.full_profile_range_mm;
            if (![c, base, tip, start, end].every(Number.isFinite) || c <= 0 || tip <= 0 || end - start < pitch - 1e-8) throw new Error('Invalid lead-in envelope.');
            const contour = [[0, 0, 0], [start ? tip : base, 0, 0]];
            if (start) contour.push([base, 0, start]);
            contour.push([base, 0, end]);
            if (end < length) contour.push([tip, 0, length]);
            contour.push([0, 0, length]);
            const face = keep(cad.makePolygon(contour));
            const envelope = keep(cad.revolution(face));
            const operation = keep(internal ? new oc.BRepAlgoAPI_Cut(solid.wrapped, envelope.wrapped)
                : new oc.BRepAlgoAPI_Common(solid.wrapped, envelope.wrapped));
            operation.SetFuzzyValue(1e-4); operation.Build();
            solid = keep(cad.cast(operation.Shape()));
        }
        const checker = keep(new oc.BRepCheck_Analyzer(solid.wrapped, true));
        if (!checker.IsValid()) throw new Error('The kernel could not produce a valid solid for this specimen.');
        let solidCount = 0;
        for (const item of cad.iterTopo(solid.wrapped, 'solid')) { solidCount++; item.delete(); }
        if (solidCount !== 1) throw new Error('The specimen must contain exactly one closed solid.');
        const volume = cad.measureVolume(solid);
        if (!Number.isFinite(volume) || volume <= 0) throw new Error('The resulting specimen has no valid volume.');
        if (Math.abs(volume - model.expected_volume_mm3) / model.expected_volume_mm3 > 1e-4) throw new Error('The solid does not match the expected threaded volume. Try a shorter specimen.');
        stage(id, 'Preparing STEP download');
        const name = model.step_name || `${model.designation} ${model.hand} ${model.specimen} L${length}mm REPRESENTATIVE ${model.version}`;
        const blob = cad.exportSTEP([{ shape: solid, name }], { unit: 'MM', modelUnit: 'MM' });
        let verification = null, mesh = null;
        if (verify || preview) {
            stage(id, 'Checking exported STEP');
            const imported = keep(await cad.importSTEP(blob));
            const importedCheck = keep(new oc.BRepCheck_Analyzer(imported.wrapped, true));
            const bbox = keep(imported.boundingBox);
            verification = { valid: importedCheck.IsValid(), volume: cad.measureVolume(imported), bounds: bbox.bounds };
            if (!verification.valid || Math.abs(verification.volume / volume - 1) > 1e-5) throw new Error('STEP round-trip verification failed.');
            if (preview) {
                stage(id, 'Meshing exported STEP for preview');
                const tolerance = Math.min(0.01, pitch / 100);
                mesh = imported.mesh({ tolerance, angularTolerance: 0.12 });
                mesh.edges = imported.meshEdges({ tolerance, angularTolerance: 0.12 }).lines;
                mesh.tolerance_mm = tolerance;
                if (!mesh.triangles.length || mesh.triangles.length > 6000000 ||
                    !mesh.vertices.every(Number.isFinite) || !mesh.normals.every(Number.isFinite)) throw new Error('Preview mesh exceeds safe limits or contains invalid coordinates.');
                // Replicad returns ordinary arrays. Own transferable buffers
                // rather than transferring an OCCT heap or cloning large lists.
                for (const key of ['vertices', 'normals', 'edges']) mesh[key] = Float32Array.from(mesh[key]);
                mesh.triangles = Uint32Array.from(mesh.triangles);
            }
        }
        return { blob, mesh, milliseconds: performance.now() - started, volume, verification,
            initialization_ms: initialization, cold_start: cold,
            kernel_memory_bytes: oc.wasmMemory.buffer.byteLength };
    } finally {
        for (const object of objects.reverse()) {
            try { object.delete(); } catch { /* A boolean may consume a wrapper. */ }
        }
    }
}

self.onmessage = async ({ data }) => {
    try {
        const result = await build(data.model, data.id, data.verify === true, data.preview === true);
        const transfers = result.mesh ? ['vertices', 'normals', 'triangles', 'edges'].map((key) => result.mesh[key].buffer) : [];
        self.postMessage({ id: data.id, ...result }, transfers);
    } catch (error) {
        self.postMessage({ id: data.id, error: typeof error === 'number' ? 'CAD construction failed. Try a shorter specimen.' : error.message || String(error) });
    }
};
