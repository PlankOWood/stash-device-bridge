console.log("Device Bridge plugin loaded");

let ws = null;
let lastScene = null;

let lastMoveTime = 0;
const MOVE_INTERVAL = 50;

window.deviceRanges = {};

/* ---------------------------------------------------
CONNECT TO CONTROLLER
--------------------------------------------------- */

function connectController(){

    ws = new WebSocket("ws://127.0.0.1:5757");

    ws.onopen = () => {

        console.log("Connected to motion controller");

        ws.send(JSON.stringify({ command:"get_status" }));

        startSceneMonitoring();
        startTimeSync();
    };

    ws.onclose = () => {
        console.log("Controller disconnected, retrying...");
        setTimeout(connectController,2000);
    };

    ws.onerror = (err) => {
        console.log("WebSocket error",err);
    };

    ws.onmessage = (msg) => {

        try{

            const data = JSON.parse(msg.data);

            console.log("Controller message:",data);

            if(data.type === "device_list"){

                const select = document.getElementById("device-select");
                if(!select) return;

                select.innerHTML = "";

                data.devices.forEach(device => {

                    const option = document.createElement("option");

                    option.value = device.port;
                    option.textContent = device.name
                        ? `${device.name} (${device.port})`
                        : `Unknown Device (${device.port})`;

                    select.appendChild(option);
                });
            }

            if(data.type === "device_profile" || data.type === "device_connected"){

                window.deviceRanges = data.ranges;
                buildSliders();
            }

        }catch(e){
            console.log("Invalid controller message",e);
        }
    };
}

/* ---------------------------------------------------
SCENE DETECTION
--------------------------------------------------- */

function startSceneMonitoring(){

    setInterval(()=>{

        const match = window.location.pathname.match(/scenes\/(\d+)/);
        if(!match) return;

        const sceneId = match[1];

        if(sceneId === lastScene) return;
        lastScene = sceneId;

        fetch("/graphql",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                query:`
                query FindScene($id:ID!){
                    findScene(id:$id){
                        files{path}
                    }
                }`,
                variables:{id:sceneId}
            })
        })
        .then(r=>r.json())
        .then(json=>{

            const path = json.data.findScene.files[0].path;

            if(ws?.readyState === 1){
                ws.send(JSON.stringify({ scene:path }));
            }
        });

    },1000);
}

/* ---------------------------------------------------
VIDEO TIME SYNC
--------------------------------------------------- */

function startTimeSync(){

    setInterval(()=>{

        const video = document.querySelector("video");
        if(!video) return;

        const ms = Math.floor(video.currentTime * 1000);

        if(ws?.readyState === 1){
            ws.send(JSON.stringify({ time:ms }));
        }

    },50);
}

/* ---------------------------------------------------
DEVICE COMMANDS
--------------------------------------------------- */

function scanDevices(){
    if(ws?.readyState !== 1) return;
    ws.send(JSON.stringify({ command:"scan_devices" }));
}

function connectDevice(){
    const port = document.getElementById("device-select").value;
    if(ws?.readyState !== 1) return;
    ws.send(JSON.stringify({ command:"connect_device", port }));
}

function setupDevice(){

    const port = document.getElementById("device-select").value;

    if(!port){
        alert("Please select a device first.");
        return;
    }

    const name = prompt("Enter device name:");
    if(!name) return;

    if(ws?.readyState !== 1) return;

    ws.send(JSON.stringify({
        command:"start_setup",
        port: port,
        name: name
    }));
}

function moveToMiddle(){
    if(ws?.readyState !== 1) return;
    ws.send(JSON.stringify({ command:"move_to_middle" }));
}

/* ---------------------------------------------------
AXIS CALIBRATION
--------------------------------------------------- */

function buildSliders(){

    const axes = ["stroke","sway","surge","twist","roll","pitch"];
    const container = document.getElementById("axis-sliders");
    if(!container) return;

    container.innerHTML = "";

    axes.forEach(axis=>{

        const r = window.deviceRanges?.[axis];

        const minStart = r ? r.min : 200;
        const maxStart = r ? r.max : 800;

        const row = document.createElement("div");
        row.style.marginBottom = "25px";
        row.style.width = "100%";
        row.style.display = "block";

        row.innerHTML = `
            <label id="label-${axis}">${axis} (${minStart}-${maxStart})</label>
            <div id="slider-${axis}"></div>
        `;

        container.appendChild(row);

        const slider = document.getElementById(`slider-${axis}`);

        slider.style.width = "100%";
        slider.style.display = "block";
        slider.style.marginTop = "10px";

        noUiSlider.create(slider,{
            start:[minStart,maxStart],
            connect:true,
            range:{ min:0, max:999 }
        });

        slider.noUiSlider.on("update",(values)=>{

            document.getElementById(`label-${axis}`).innerText =
                `${axis} (${Math.round(values[0])} - ${Math.round(values[1])})`;

            if(ws?.readyState !== 1) return;

            ws.send(JSON.stringify({
                command:"set_range",
                channel:axis,
                min:parseInt(values[0]),
                max:parseInt(values[1])
            }));
        });

        slider.noUiSlider.on("slide",(values,handle)=>{

            const now = Date.now();
            if(now - lastMoveTime < MOVE_INTERVAL) return;
            lastMoveTime = now;

            const value = handle === 0
                ? parseInt(values[0])
                : parseInt(values[1]);

            if(ws?.readyState !== 1) return;

            ws.send(JSON.stringify({
                command:"test_range",
                channel:axis,
                value
            }));
        });

        slider.noUiSlider.on("end",()=>{
            if(ws?.readyState !== 1) return;

            ws.send(JSON.stringify({
                command:"clear_override",
                channel:axis
            }));
        });

    });
}

function saveCalibration(){
    if(ws?.readyState !== 1) return;
    ws.send(JSON.stringify({ command:"save_profile" }));
    alert("Calibration saved");
}

/* ---------------------------------------------------
UI BUILDER
--------------------------------------------------- */

function createUI(){

    if(document.getElementById("device-bridge-ui")) return;

    const headers = document.querySelectorAll("h5,h4,h3");
    let pluginCard = null;

    headers.forEach(el=>{
        if(el.innerText.includes("Device Bridge")){
            pluginCard = el.closest("div");
        }
    });

    if(!pluginCard){
        console.log("Device Bridge card not ready yet...");
        return;
    }

    const container = document.createElement("div");
    container.id = "device-bridge-ui";

    /* STYLE */

    if (!document.getElementById("device-bridge-style")) {

        const style = document.createElement("style");
        style.id = "device-bridge-style";

        style.innerHTML = `
        #device-bridge-ui .noUi-target {
            height: 16px;
        }
        #device-bridge-ui .noUi-handle {
            width: 26px;
            height: 26px;
            top: -6px;
            border-radius: 50%;
            cursor: pointer;
        }
        #device-bridge-ui .noUi-connect {
            background: #4caf50;
        }
        #device-bridge-ui .noUi-handle:hover {
            box-shadow: 0 0 8px rgba(0,0,0,0.4);
        }
        `;

        document.head.appendChild(style);
    }

    container.style.marginTop = "15px";
    container.style.width = "100%";
    container.style.maxWidth = "100%";
    container.style.paddingRight = "30px";

    container.innerHTML = `
        <h4>Device Setup</h4>

        <button id="scan-btn">Scan Devices</button>
        <br><br>

        <select id="device-select" style="width:220px"></select>
        <br><br>

        <button id="connect-btn">Connect Device</button>
        <button id="setup-btn">Setup New Device</button>

        <hr>

        <h4>Axis Calibration</h4>

        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <button id="center-btn">Move Device To Middle</button>
            <div style="opacity:0.6;">&nbsp;</div>
        </div>

        <div id="axis-sliders"></div>

        <button id="save-profile-btn">Save Calibration</button>
    `;

    pluginCard.appendChild(container);

    document.getElementById("scan-btn").onclick = scanDevices;
    document.getElementById("connect-btn").onclick = connectDevice;
    document.getElementById("setup-btn").onclick = setupDevice;
    document.getElementById("save-profile-btn").onclick = saveCalibration;
    document.getElementById("center-btn").onclick = moveToMiddle;

    if(window.deviceRanges){
        buildSliders();
    }
}

/* ---------------------------------------------------
INIT
--------------------------------------------------- */

connectController();
setInterval(createUI,1000);