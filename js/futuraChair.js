import * as THREE from "https://cdn.skypack.dev/three@0.129.0/build/three.module.js";
import { OrbitControls } from "https://cdn.skypack.dev/three@0.129.0/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "https://cdn.skypack.dev/three@0.129.0/examples/jsm/loaders/GLTFLoader.js";

const container = document.getElementById("futuraChair");

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);

let object;
let controls;
let objToRender = 'futura_Chair'; 

const loader = new GLTFLoader();

loader.load(
  './models/Futura.gltf',
  function (gltf) {
    object = gltf.scene;
    scene.add(object);
    
    const box = new THREE.Box3().setFromObject(object);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    
    object.position.x += (object.position.x - center.x);
    object.position.z += (object.position.z - center.z);
    object.position.y += (object.position.y - box.min.y);
    
    const maxDim = Math.max(size.x, size.y, size.z);
    camera.position.set(0, maxDim * 1.2, maxDim * 2.0);
    
    if (controls) {
        controls.target.set(0, maxDim * 0.5, 0);
        controls.update();
    }
  },
  function (xhr) {
    console.log((xhr.loaded / xhr.total * 100) + '% loaded');
  },
  function (error) {
    console.error("An error occurred loading the model:", error);
  }
);

const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
container.appendChild(renderer.domElement);

const topLight = new THREE.DirectionalLight(0xffffff, 1.5);
topLight.position.set(5, 10, 7);
scene.add(topLight);

const fillLight = new THREE.DirectionalLight(0xffffff, 0.5);
fillLight.position.set(-5, 4, -5);
scene.add(fillLight);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
scene.add(ambientLight);

controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; 
controls.dampingFactor = 0.05;

function animate() {
  requestAnimationFrame(animate);
  if (controls) controls.update();
  renderer.render(scene, camera);
}

const resizeObserver = new ResizeObserver(() => {
    const w = container.clientWidth || 300;
    const h = container.clientHeight || 300;
    
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
});
resizeObserver.observe(container);

animate();