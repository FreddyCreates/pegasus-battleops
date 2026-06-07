/**
 * Spatium Computationis — 3D Simulation Renderer
 * ⌬ Three.js powered real-time 3D battlespace visualization
 * 
 * Renders entities, zones, connections, and particle effects
 * in a navigable 3D environment with orbit controls.
 */

// CDN imports handled via importmap in the HTML template
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ---------------------------------------------------------------------------
// Scene Setup
// ---------------------------------------------------------------------------

const canvas = document.getElementById('simulation-canvas');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a0a1a);
scene.fog = new THREE.FogExp2(0x0a0a1a, 0.008);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 500);
camera.position.set(0, 50, 80);

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.maxPolarAngle = Math.PI * 0.85;
controls.minDistance = 10;
controls.maxDistance = 200;

// ---------------------------------------------------------------------------
// Lighting
// ---------------------------------------------------------------------------

const ambientLight = new THREE.AmbientLight(0x404060, 0.6);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(30, 50, 30);
dirLight.castShadow = true;
scene.add(dirLight);

const pointLight1 = new THREE.PointLight(0x6c5ce7, 1.5, 60);
pointLight1.position.set(0, 10, 0);
scene.add(pointLight1);

const pointLight2 = new THREE.PointLight(0x00cec9, 1.0, 50);
pointLight2.position.set(30, 10, 0);
scene.add(pointLight2);

// ---------------------------------------------------------------------------
// Grid & Reference plane
// ---------------------------------------------------------------------------

const gridHelper = new THREE.GridHelper(120, 40, 0x1a1a3e, 0x1a1a2e);
gridHelper.position.y = -0.5;
scene.add(gridHelper);

// Ground plane
const groundGeo = new THREE.PlaneGeometry(200, 200);
const groundMat = new THREE.MeshStandardMaterial({
    color: 0x0a0a1a,
    roughness: 0.9,
    transparent: true,
    opacity: 0.5,
});
const ground = new THREE.Mesh(groundGeo, groundMat);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -1;
ground.receiveShadow = true;
scene.add(ground);

// ---------------------------------------------------------------------------
// Entity Management
// ---------------------------------------------------------------------------

const entityMeshes = new Map(); // entity_id -> THREE.Mesh
const zoneMeshes = new Map();   // zone_id -> THREE.Mesh
const trailParticles = [];

// Geometry cache
const sphereGeo = new THREE.SphereGeometry(1, 16, 12);
const octaGeo = new THREE.OctahedronGeometry(1, 0);
const boxGeo = new THREE.BoxGeometry(1, 1, 1);
const coneGeo = new THREE.ConeGeometry(0.6, 1.5, 6);
const torusGeo = new THREE.TorusGeometry(1, 0.3, 8, 16);

function getGeometryForType(entityType) {
    switch (entityType) {
        case 'agent': return octaGeo;
        case 'threat': return coneGeo;
        case 'signal': return sphereGeo;
        case 'honeypot': return torusGeo;
        case 'data_packet': return boxGeo;
        case 'defensive_node': return octaGeo;
        case 'gateway': return boxGeo;
        default: return sphereGeo;
    }
}

function createEntityMesh(entity) {
    const geo = getGeometryForType(entity.entity_type);
    const color = new THREE.Color(entity.color);
    
    const mat = new THREE.MeshStandardMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 0.4,
        metalness: 0.3,
        roughness: 0.4,
        transparent: true,
        opacity: entity.state === 'spawning' ? 0.3 : 0.9,
    });

    const mesh = new THREE.Mesh(geo, mat);
    mesh.scale.setScalar(entity.size);
    mesh.position.set(entity.position.x, entity.position.y, entity.position.z);
    mesh.castShadow = true;
    mesh.userData = { entityId: entity.entity_id, entityType: entity.entity_type };

    // Add glow for agents
    if (entity.entity_type === 'agent') {
        const glowGeo = new THREE.SphereGeometry(entity.size * 1.5, 16, 12);
        const glowMat = new THREE.MeshBasicMaterial({
            color: color,
            transparent: true,
            opacity: 0.15,
        });
        const glow = new THREE.Mesh(glowGeo, glowMat);
        mesh.add(glow);
    }

    scene.add(mesh);
    entityMeshes.set(entity.entity_id, mesh);
    return mesh;
}

function updateEntityMesh(entity) {
    let mesh = entityMeshes.get(entity.entity_id);
    
    if (!mesh) {
        mesh = createEntityMesh(entity);
        return;
    }

    // Smooth position interpolation
    mesh.position.lerp(
        new THREE.Vector3(entity.position.x, entity.position.y, entity.position.z),
        0.3
    );

    // Update color
    const color = new THREE.Color(entity.color);
    mesh.material.color.copy(color);
    mesh.material.emissive.copy(color);

    // Scale pulse for active entities
    const pulse = 1 + Math.sin(Date.now() * 0.003 + mesh.position.x) * 0.05;
    mesh.scale.setScalar(entity.size * pulse);

    // Rotation
    mesh.rotation.y += 0.02;
    if (entity.entity_type === 'threat') {
        mesh.rotation.x += 0.01;
    }

    // Opacity based on state
    if (entity.state === 'spawning') {
        mesh.material.opacity = Math.min(mesh.material.opacity + 0.05, 0.9);
    }
}

function removeEntityMesh(entityId) {
    const mesh = entityMeshes.get(entityId);
    if (mesh) {
        scene.remove(mesh);
        mesh.geometry?.dispose();
        mesh.material?.dispose();
        entityMeshes.delete(entityId);
    }
}

// ---------------------------------------------------------------------------
// Zone Rendering
// ---------------------------------------------------------------------------

function createZoneMesh(zone) {
    const color = new THREE.Color(zone.color);
    
    // Transparent sphere for zone boundary
    const geo = new THREE.SphereGeometry(zone.radius, 24, 16);
    const mat = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.05,
        wireframe: false,
        side: THREE.BackSide,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(zone.center.x, zone.center.y, zone.center.z);

    // Wireframe ring
    const ringGeo = new THREE.TorusGeometry(zone.radius, 0.1, 8, 48);
    const ringMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.3 });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI / 2;
    mesh.add(ring);

    scene.add(mesh);
    zoneMeshes.set(zone.zone_id, mesh);
}

// ---------------------------------------------------------------------------
// Connection Lines (data flow visualization)
// ---------------------------------------------------------------------------

const connectionLines = [];

function createConnectionLine(from, to, color = 0x74b9ff) {
    const points = [
        new THREE.Vector3(from.x, from.y, from.z),
        new THREE.Vector3(to.x, to.y, to.z),
    ];
    const geo = new THREE.BufferGeometry().setFromPoints(points);
    const mat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.2 });
    const line = new THREE.Line(geo, mat);
    scene.add(line);
    connectionLines.push(line);
    return line;
}

// ---------------------------------------------------------------------------
// Particle Trails
// ---------------------------------------------------------------------------

const particleCount = 200;
const particleGeo = new THREE.BufferGeometry();
const particlePositions = new Float32Array(particleCount * 3);
const particleColors = new Float32Array(particleCount * 3);

for (let i = 0; i < particleCount; i++) {
    particlePositions[i * 3] = (Math.random() - 0.5) * 100;
    particlePositions[i * 3 + 1] = Math.random() * 20;
    particlePositions[i * 3 + 2] = (Math.random() - 0.5) * 100;
    particleColors[i * 3] = 0.3;
    particleColors[i * 3 + 1] = 0.5;
    particleColors[i * 3 + 2] = 1.0;
}

particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
particleGeo.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

const particleMat = new THREE.PointsMaterial({
    size: 0.3,
    vertexColors: true,
    transparent: true,
    opacity: 0.6,
    blending: THREE.AdditiveBlending,
});
const particles = new THREE.Points(particleGeo, particleMat);
scene.add(particles);

// ---------------------------------------------------------------------------
// WebSocket Connection
// ---------------------------------------------------------------------------

let ws = null;
let connected = false;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/simulation/ws`;
    
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        connected = true;
        updateStatus('connected');
        console.log('⌬ Simulation WebSocket connected');
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleMessage(msg);
    };

    ws.onclose = () => {
        connected = false;
        updateStatus('disconnected');
        // Reconnect after 2 seconds
        setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        updateStatus('error');
    };
}

function handleMessage(msg) {
    switch (msg.type) {
        case 'full_state':
            handleFullState(msg.data);
            break;
        case 'state_delta':
            handleStateDelta(msg.data);
            break;
        case 'inject_ack':
            console.log('Entity injected:', msg.entity.entity_id);
            break;
    }
}

function handleFullState(state) {
    // Create zones
    if (state.zones) {
        state.zones.forEach(zone => {
            if (!zoneMeshes.has(zone.zone_id)) {
                createZoneMesh(zone);
            }
        });
    }

    // Sync entities
    const activeIds = new Set();
    state.entities.forEach(entity => {
        activeIds.add(entity.entity_id);
        updateEntityMesh(entity);
    });

    // Remove entities no longer in state
    for (const [id] of entityMeshes) {
        if (!activeIds.has(id)) {
            removeEntityMesh(id);
        }
    }

    updateHUD(state);
}

function handleStateDelta(state) {
    const activeIds = new Set();
    state.entities.forEach(entity => {
        activeIds.add(entity.entity_id);
        updateEntityMesh(entity);
    });

    // Remove dead entities
    for (const [id] of entityMeshes) {
        if (!activeIds.has(id)) {
            removeEntityMesh(id);
        }
    }

    updateHUD(state);
}

// ---------------------------------------------------------------------------
// HUD Updates
// ---------------------------------------------------------------------------

function updateHUD(state) {
    const tickEl = document.getElementById('hud-tick');
    const entitiesEl = document.getElementById('hud-entities');
    const timeEl = document.getElementById('hud-time');
    
    if (tickEl) tickEl.textContent = state.tick || 0;
    if (entitiesEl) entitiesEl.textContent = state.entities?.length || 0;
    if (timeEl) timeEl.textContent = (state.world_time || 0).toFixed(1) + 's';
}

function updateStatus(status) {
    const el = document.getElementById('hud-status');
    if (el) {
        el.textContent = status;
        el.className = `status-${status}`;
    }
}

// ---------------------------------------------------------------------------
// Animation Loop
// ---------------------------------------------------------------------------

function animate() {
    requestAnimationFrame(animate);
    
    controls.update();

    // Animate particles
    const positions = particles.geometry.attributes.position.array;
    for (let i = 0; i < particleCount; i++) {
        positions[i * 3 + 1] += Math.sin(Date.now() * 0.001 + i) * 0.01;
        positions[i * 3] += Math.cos(Date.now() * 0.0005 + i * 0.5) * 0.005;
    }
    particles.geometry.attributes.position.needsUpdate = true;

    // Pulse zone meshes
    zoneMeshes.forEach((mesh) => {
        mesh.rotation.y += 0.001;
        const children = mesh.children;
        if (children.length > 0) {
            children[0].rotation.z += 0.005;
        }
    });

    // Pulse core light
    pointLight1.intensity = 1.5 + Math.sin(Date.now() * 0.002) * 0.5;

    renderer.render(scene, camera);
}

// ---------------------------------------------------------------------------
// Window Resize
// ---------------------------------------------------------------------------

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// ---------------------------------------------------------------------------
// Controls Panel
// ---------------------------------------------------------------------------

window.injectThreat = function() {
    if (ws && connected) {
        ws.send(JSON.stringify({
            cmd: 'inject',
            entity_type: 'threat',
            position: { x: Math.random() * 80 - 40, y: 5, z: -50 },
            target: { x: 0, y: 0, z: 0 },
            color: '#ff4757',
            speed: 3.0,
            size: 1.5,
            ttl: 15,
            label: 'manual_threat',
        }));
    }
};

window.injectSignal = function() {
    if (ws && connected) {
        ws.send(JSON.stringify({
            cmd: 'inject',
            entity_type: 'signal',
            position: { x: 0, y: 2, z: -40 },
            target: { x: 30, y: 5, z: 0 },
            color: '#00ff88',
            speed: 6.0,
            size: 0.8,
            ttl: 10,
            label: 'manual_signal',
        }));
    }
};

window.requestFullState = function() {
    if (ws && connected) {
        ws.send(JSON.stringify({ cmd: 'get_state' }));
    }
};

// ---------------------------------------------------------------------------
// Initialize
// ---------------------------------------------------------------------------

animate();
connectWebSocket();

console.log('⌬ Spatium Computationis 3D Simulation initialized');
