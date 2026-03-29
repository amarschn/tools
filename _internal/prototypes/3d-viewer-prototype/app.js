import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import opencascade from 'https://unpkg.com/opencascade.js@1.1.1/dist/opencascade.wasm.js';

let oc; // OpenCascade instance
let currentShape = null;
let scene, camera, renderer, controls, mesh;

const statusEl = document.getElementById('status');
const btnGenerate = document.getElementById('btn-generate');
const btnStl = document.getElementById('btn-stl');
const btnStep = document.getElementById('btn-step');

async function init() {
    initThreeJS();

    try {
        statusEl.innerText = "Loading OpenCascade.js WASM (this may take a moment)...";
        // Initialize OpenCascade by invoking the default export
        oc = await opencascade({
            locateFile: (path) => `https://unpkg.com/opencascade.js@1.1.1/dist/${path}`
        });
        
        statusEl.innerText = "Engine ready. Click Generate.";
        
        btnGenerate.disabled = false;
        btnGenerate.innerText = "Generate Shape";
        
        btnGenerate.addEventListener('click', generateGeometry);
        btnStl.addEventListener('click', exportSTL);
        btnStep.addEventListener('click', exportSTEP);

    } catch (err) {
        console.error(err);
        statusEl.innerText = "Failed to load OpenCascade. See console.";
    }
}

function initThreeJS() {
    const container = document.getElementById('viewer-container');

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f0f0);

    camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(50, 50, 50);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    // Lights
    const ambientLight = new THREE.AmbientLight(0x404040);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(100, 200, 50);
    scene.add(dirLight);

    // Grid
    const gridHelper = new THREE.GridHelper(100, 10);
    scene.add(gridHelper);

    window.addEventListener('resize', onWindowResize);

    animate();
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

function generateGeometry() {
    statusEl.innerText = "Generating geometry...";
    btnGenerate.disabled = true;

    // Cleanup previous
    if (currentShape) {
        currentShape.delete();
        currentShape = null;
    }
    if (mesh) {
        scene.remove(mesh);
        mesh.geometry.dispose();
        mesh.material.dispose();
        mesh = null;
    }

    // Give UI time to update
    setTimeout(() => {
        try {
            // Create a box. Note: The exact suffix (_1, _2, etc) depends on the opencascade.js version build.
            // Using typical defaults.
            const boxAPI = new oc.BRepPrimAPI_MakeBox_2(20, 30, 15);
            const box = boxAPI.Shape();

            // Create a cylinder for a hole
            const cylAx2 = new oc.gp_Ax2_3(new oc.gp_Pnt_3(10, 15, 0), new oc.gp_Dir_4(0, 0, 1));
            const cylAPI = new oc.BRepPrimAPI_MakeCylinder_3(cylAx2, 5, 20);
            const cylinder = cylAPI.Shape();

            // Cut cylinder from box
            const cutAPI = new oc.BRepAlgoAPI_Cut_3(box, cylinder);
            cutAPI.Build();
            currentShape = cutAPI.Shape();

            // Cleanup intermediate objects
            boxAPI.delete();
            box.delete();
            cylAx2.delete();
            cylAPI.delete();
            cylinder.delete();
            cutAPI.delete();

            statusEl.innerText = "Geometry generated. Rendering...";

            // To render in Three.js, we export it as STL internally and load it.
            const stlWriter = new oc.StlAPI_Writer();
            const filename = "temp.stl";
            stlWriter.Write(currentShape, filename);
            
            const fileContent = oc.FS.readFile("/" + filename);
            oc.FS.unlink("/" + filename);
            stlWriter.delete();

            // Load STL to Three.js
            const blob = new Blob([fileContent], { type: "application/octet-stream" });
            const url = URL.createObjectURL(blob);
            
            const loader = new STLLoader();
            loader.load(url, (geometry) => {
                geometry.computeVertexNormals();
                geometry.center();
                
                const material = new THREE.MeshStandardMaterial({ 
                    color: 0x156289, 
                    roughness: 0.3,
                    metalness: 0.1,
                    side: THREE.DoubleSide
                });
                
                mesh = new THREE.Mesh(geometry, material);
                scene.add(mesh);
                
                URL.revokeObjectURL(url);
                
                statusEl.innerText = "Ready. You can download the files.";
                btnGenerate.disabled = false;
                btnStl.disabled = false;
                btnStep.disabled = false;
            });

        } catch (e) {
            console.error(e);
            statusEl.innerText = "Error generating geometry. Check console (might be OpenCascade API mismatch).";
            btnGenerate.disabled = false;
        }
    }, 50);
}

function exportSTL() {
    if (!currentShape) return;
    statusEl.innerText = "Exporting STL...";

    try {
        const stlWriter = new oc.StlAPI_Writer();
        const filename = "model.stl";
        stlWriter.Write(currentShape, filename);
        
        const fileContent = oc.FS.readFile("/" + filename);
        oc.FS.unlink("/" + filename);
        stlWriter.delete();

        const blob = new Blob([fileContent], { type: "application/octet-stream" });
        downloadBlob(blob, filename);
        
        statusEl.innerText = "STL Exported.";
    } catch(e) {
        console.error(e);
        statusEl.innerText = "Error exporting STL.";
    }
}

function exportSTEP() {
    if (!currentShape) return;
    statusEl.innerText = "Exporting STEP...";

    try {
        const writer = new oc.STEPControl_Writer_1();
        
        const transferStatus = writer.Transfer(
            currentShape, 
            oc.STEPControl_StepModelType.STEPControl_AsIs, 
            true, 
            new oc.Message_ProgressRange_1()
        );
        
        const filename = "model.step";
        writer.Write(filename);

        const fileContent = oc.FS.readFile("/" + filename, { encoding: "binary" });
        oc.FS.unlink("/" + filename);
        writer.delete();

        const blob = new Blob([fileContent.buffer], { type: "application/step" });
        downloadBlob(blob, filename);
        
        statusEl.innerText = "STEP Exported.";
    } catch(e) {
        console.error(e);
        statusEl.innerText = "Error exporting STEP.";
    }
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Start app
init();