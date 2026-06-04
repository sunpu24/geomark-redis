const CHENGDU_CENTER = [104.06476, 30.5702];
const DEFAULT_PADDING = [70, 70, 70, 70];

let map;
let infoWindow;
let searchCenterMarker;
let searchCircle;

let allLandmarks = [];
let visibleLandmarks = [];
let selectedLandmarkId = "";
let editingLandmarkId = "";
let highlightedIds = new Set();
let toastTimer;
let currentUser = null;

const markerMap = new Map();

const mapStatus = document.getElementById("mapStatus");
const landmarkList = document.getElementById("landmarkList");
const landmarkCount = document.getElementById("landmarkCount");
const resetViewBtn = document.getElementById("resetViewBtn");
const resetSeedBtn = document.getElementById("resetSeedBtn");
const exportJsonBtn = document.getElementById("exportJsonBtn");
const importJsonBtn = document.getElementById("importJsonBtn");
const importJsonInput = document.getElementById("importJsonInput");
const categoryFilter = document.getElementById("categoryFilter");
const keywordSearch = document.getElementById("keywordSearch");
const openAuthModalBtn = document.getElementById("openAuthModalBtn");
const authEntryText = document.getElementById("authEntryText");
const logoutBtn = document.getElementById("logoutBtn");
const authModal = document.getElementById("authModal");
const closeAuthModalBtn = document.getElementById("closeAuthModalBtn");
const loginTabBtn = document.getElementById("loginTabBtn");
const registerTabBtn = document.getElementById("registerTabBtn");
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const nearbyForm = document.getElementById("nearbyForm");
const distanceForm = document.getElementById("distanceForm");
const distanceFrom = document.getElementById("distanceFrom");
const distanceTo = document.getElementById("distanceTo");
const distanceResult = document.getElementById("distanceResult");
const addLandmarkForm = document.getElementById("addLandmarkForm");
const landmarkFormCard = document.getElementById("landmarkFormCard");
const landmarkFormTitle = document.getElementById("landmarkFormTitle");
const landmarkIdInput = document.getElementById("landmarkIdInput");
const saveLandmarkBtn = document.getElementById("saveLandmarkBtn");
const cancelEditBtn = document.getElementById("cancelEditBtn");
const toast = document.getElementById("toast");

function setStatus(message) {
    if (mapStatus) {
        mapStatus.textContent = message;
    }
}

function showToast(message, type = "success") {
    if (!toast) {
        return;
    }

    window.clearTimeout(toastTimer);
    toast.textContent = message;
    toast.className = `toast ${type}`;

    toastTimer = window.setTimeout(() => {
        toast.classList.add("hidden");
    }, 3200);
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function getLandmarkName(id) {
    const landmark = allLandmarks.find((item) => item.id === id);
    return landmark?.name || id;
}

function getLandmarkPosition(landmark) {
    const longitude = Number(landmark.longitude);
    const latitude = Number(landmark.latitude);

    if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) {
        return null;
    }

    return [longitude, latitude];
}

function validateLandmarkPayload(payload, isEditing = false) {
    const idPattern = /^[a-zA-Z0-9_-]+$/;
    const id = String(payload.id || "").trim();
    const name = String(payload.name || "").trim();
    const longitude = Number(payload.longitude);
    const latitude = Number(payload.latitude);

    if (!isEditing && !id) {
        throw new Error("请填写地标 ID");
    }
    if (id && !idPattern.test(id)) {
        throw new Error("地标 ID 只能包含英文字母、数字、下划线和中划线");
    }
    if (!name) {
        throw new Error("请填写地标名称");
    }
    if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) {
        throw new Error("经度和纬度必须是数字");
    }
    if (longitude < -180 || longitude > 180) {
        throw new Error("经度必须在 -180 到 180 之间");
    }
    if (latitude < -90 || latitude > 90) {
        throw new Error("纬度必须在 -90 到 90 之间");
    }

    return {
        ...payload,
        id,
        name,
        category: String(payload.category || "").trim() || "未分类",
        address: String(payload.address || "").trim(),
        description: String(payload.description || "").trim(),
        longitude,
        latitude,
    };
}

function resetLandmarkForm() {
    editingLandmarkId = "";
    addLandmarkForm.reset();
    landmarkIdInput.disabled = false;
    landmarkFormTitle.textContent = "新增地标";
    saveLandmarkBtn.textContent = "保存地标";
    cancelEditBtn.classList.add("hidden");
    landmarkFormCard.classList.remove("is-editing");
}

function startEditLandmark(landmark) {
    editingLandmarkId = landmark.id;
    landmarkFormCard.open = true;
    landmarkFormCard.classList.add("is-editing");
    landmarkFormTitle.textContent = `编辑地标：${landmark.name}`;
    saveLandmarkBtn.textContent = "保存修改";
    cancelEditBtn.classList.remove("hidden");

    addLandmarkForm.elements.id.value = landmark.id || "";
    addLandmarkForm.elements.name.value = landmark.name || "";
    addLandmarkForm.elements.longitude.value = landmark.longitude ?? "";
    addLandmarkForm.elements.latitude.value = landmark.latitude ?? "";
    addLandmarkForm.elements.category.value = landmark.category || "";
    addLandmarkForm.elements.address.value = landmark.address || "";
    addLandmarkForm.elements.description.value = landmark.description || "";
    landmarkIdInput.disabled = true;

    selectedLandmarkId = landmark.id;
    openLandmarkInfo(landmark);
    landmarkFormCard.scrollIntoView({ behavior: "smooth", block: "start" });
    addLandmarkForm.elements.name.focus({ preventScroll: true });
    landmarkFormCard.classList.add("is-flashing");
    window.setTimeout(() => landmarkFormCard.classList.remove("is-flashing"), 1200);
    setStatus(`已打开「${landmark.name}」编辑表单，请在右侧上方修改后点击保存修改`);
}

function buildInfoContent(landmark) {
    const position = getLandmarkPosition(landmark) || ["", ""];
    const longitude = Number(position[0]);
    const latitude = Number(position[1]);
    const coordinateText = Number.isFinite(longitude) && Number.isFinite(latitude)
        ? `${longitude.toFixed(6)},${latitude.toFixed(6)}`
        : "暂无坐标";
    const amapUrl = Number.isFinite(longitude) && Number.isFinite(latitude)
        ? `https://uri.amap.com/marker?position=${encodeURIComponent(`${longitude},${latitude}`)}&name=${encodeURIComponent(landmark.name || landmark.id || "地标")}`
        : `https://www.amap.com/search?query=${encodeURIComponent(landmark.name || landmark.id || "地标")}`;

    return `
        <div class="info-window">
            <h3>${escapeHtml(landmark.name)}</h3>
            <p><strong>ID：</strong>${escapeHtml(landmark.id)}</p>
            <p><strong>分类：</strong>${escapeHtml(landmark.category || "未分类")}</p>
            <p><strong>地址：</strong>${escapeHtml(landmark.address || "暂无地址")}</p>
            <p><strong>经纬度：</strong><span class="coordinate-text">${escapeHtml(coordinateText)}</span></p>
            <p>${escapeHtml(landmark.description || "暂无描述")}</p>
            <div class="info-actions">
                <button type="button" class="info-edit-btn" data-id="${escapeHtml(landmark.id)}">编辑此地标</button>
                <button type="button" class="info-copy-btn" data-id="${escapeHtml(landmark.id)}">复制坐标</button>
                <button type="button" class="info-delete-btn danger" data-id="${escapeHtml(landmark.id)}">删除此地标</button>
                <a class="info-amap-link" href="${escapeHtml(amapUrl)}" target="_blank" rel="noopener noreferrer">高德查看</a>
            </div>
        </div>
    `;
}

function clearSearchOverlay() {
    if (searchCenterMarker) {
        map.remove(searchCenterMarker);
        searchCenterMarker = null;
    }

    if (searchCircle) {
        map.remove(searchCircle);
        searchCircle = null;
    }
}

function clearMarkers() {
    markerMap.forEach((marker) => map.remove(marker));
    markerMap.clear();
}

function updateMarkerState() {
    markerMap.forEach((marker, id) => {
        const isSelected = selectedLandmarkId === id;
        const isHighlighted = highlightedIds.has(id);

        marker.setzIndex(isSelected ? 120 : isHighlighted ? 110 : 100);
        marker.setLabel(
            isSelected || isHighlighted
                ? {
                      direction: "top",
                      offset: new AMap.Pixel(0, -5),
                      content: `<div class="marker-label ${isSelected ? "selected" : "highlighted"}">${escapeHtml(getLandmarkName(id))}</div>`,
                  }
                : null
        );
    });
}

function openLandmarkInfo(landmark) {
    const marker = markerMap.get(landmark.id);
    const position = getLandmarkPosition(landmark);

    if (!marker || !position) {
        return;
    }

    selectedLandmarkId = landmark.id;
    infoWindow.setContent(buildInfoContent(landmark));
    infoWindow.open(map, position);
    map.setZoomAndCenter(Math.max(map.getZoom(), 13), position);
    updateMarkerState();
    renderLandmarkList(visibleLandmarks);
}

function createMarker(landmark) {
    const position = getLandmarkPosition(landmark);
    if (!position) {
        return null;
    }

    const marker = new AMap.Marker({
        map,
        position,
        title: landmark.name,
        zIndex: 100,
    });

    marker.on("click", () => openLandmarkInfo(landmark));
    markerMap.set(landmark.id, marker);
    return marker;
}

function renderMarkers(landmarks) {
    clearMarkers();
    const markers = landmarks.map(createMarker).filter(Boolean);
    updateMarkerState();
    return markers;
}

function renderLandmarkList(landmarks) {
    landmarkCount.textContent = `${landmarks.length} 个`;

    if (landmarks.length === 0) {
        landmarkList.innerHTML = '<div class="empty-tip">暂无景点数据</div>';
        return;
    }

    landmarkList.innerHTML = "";
    landmarks.forEach((landmark) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "landmark-card";
        if (selectedLandmarkId === landmark.id) {
            card.classList.add("is-selected");
        }
        if (highlightedIds.has(landmark.id)) {
            card.classList.add("is-highlighted");
        }

        const distanceText = landmark.distance !== undefined && landmark.distance !== null
            ? `<p class="distance">距离搜索中心：${escapeHtml(landmark.distance)} ${escapeHtml(landmark.unit || "")}</p>`
            : "";

        card.innerHTML = `
            <span class="card-main">
                <strong>${escapeHtml(landmark.name)}</strong>
                <span class="tag">${escapeHtml(landmark.category || "未分类")}</span>
                <p class="address">${escapeHtml(landmark.address || "暂无地址")}</p>
                ${distanceText}
            </span>
            <span class="card-actions">
                <span class="edit-btn" role="button" tabindex="0" data-id="${escapeHtml(landmark.id)}">编辑</span>
                <span class="delete-btn" role="button" tabindex="0" data-id="${escapeHtml(landmark.id)}">删除</span>
            </span>
        `;

        card.addEventListener("click", () => openLandmarkInfo(landmark));
        card.querySelector(".edit-btn").addEventListener("click", (event) => {
            event.stopPropagation();
            startEditLandmark(landmark);
        });
        card.querySelector(".delete-btn").addEventListener("click", (event) => {
            event.stopPropagation();
            deleteLandmark(landmark);
        });
        landmarkList.appendChild(card);
    });
}

function populateCategoryFilter() {
    const currentValue = categoryFilter.value;
    const categories = [...new Set(allLandmarks.map((item) => item.category || "未分类"))].sort();

    categoryFilter.innerHTML = '<option value="">全部分类</option>';
    categories.forEach((category) => {
        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        categoryFilter.appendChild(option);
    });

    if (categories.includes(currentValue)) {
        categoryFilter.value = currentValue;
    }
}

function populateDistanceSelects() {
    const options = allLandmarks
        .map((landmark) => `<option value="${escapeHtml(landmark.id)}">${escapeHtml(landmark.name)}</option>`)
        .join("");

    distanceFrom.innerHTML = options;
    distanceTo.innerHTML = options;

    if (allLandmarks.length > 1) {
        distanceTo.selectedIndex = 1;
    }
}

function fitLandmarks(landmarks) {
    const markers = landmarks.map((landmark) => markerMap.get(landmark.id)).filter(Boolean);
    if (markers.length > 0) {
        map.setFitView(markers, false, DEFAULT_PADDING);
    } else {
        map.setZoomAndCenter(12, CHENGDU_CENTER);
    }
}

function applyListFilters() {
    clearSearchOverlay();
    highlightedIds = new Set();
    selectedLandmarkId = "";

    const category = categoryFilter.value;
    const keyword = String(keywordSearch.value || "").trim().toLowerCase();
    visibleLandmarks = allLandmarks.filter((landmark) => {
        const matchesCategory = !category || (landmark.category || "未分类") === category;
        const searchableText = [landmark.name, landmark.category, landmark.address]
            .map((value) => String(value || "").toLowerCase())
            .join(" ");
        const matchesKeyword = !keyword || searchableText.includes(keyword);
        return matchesCategory && matchesKeyword;
    });

    renderMarkers(visibleLandmarks);
    renderLandmarkList(visibleLandmarks);
    fitLandmarks(visibleLandmarks);
    const filterText = [category ? `分类「${category}」` : "", keyword ? `关键词「${keywordSearch.value.trim()}」` : ""]
        .filter(Boolean)
        .join("、");
    setStatus(filterText ? `已筛选 ${visibleLandmarks.length} 个地标：${filterText}` : `已显示全部 ${visibleLandmarks.length} 个地标`);
}

function applyCategoryFilter() {
    applyListFilters();
}

function switchAuthTab(mode) {
    const isRegister = mode === "register";

    loginTabBtn.classList.toggle("active", !isRegister);
    registerTabBtn.classList.toggle("active", isRegister);
    loginTabBtn.setAttribute("aria-selected", String(!isRegister));
    registerTabBtn.setAttribute("aria-selected", String(isRegister));
    loginForm.classList.toggle("hidden", isRegister);
    registerForm.classList.toggle("hidden", !isRegister);
}

function updateAuthUI() {
    if (!authEntryText || !openAuthModalBtn || !logoutBtn) {
        return;
    }

    if (currentUser) {
        const displayName = currentUser.nickname || currentUser.username;
        authEntryText.textContent = `你好，${displayName}`;
        openAuthModalBtn.classList.add("is-logged-in");
        logoutBtn.classList.remove("hidden");
    } else {
        authEntryText.textContent = "登录 / 注册";
        openAuthModalBtn.classList.remove("is-logged-in");
        logoutBtn.classList.add("hidden");
    }
}

async function loadCurrentUser() {
    const response = await fetch("/api/users/me");
    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(result.message || `读取当前用户失败：${response.status}`);
    }

    currentUser = result.logged_in ? result.data : null;
    updateAuthUI();
    return currentUser;
}

function openAuthModal(mode = "login") {
    switchAuthTab(mode);
    authModal.classList.remove("hidden");
    authModal.setAttribute("aria-hidden", "false");
    window.setTimeout(() => {
        const firstInput = mode === "register"
            ? registerForm.querySelector("input")
            : loginForm.querySelector("input");
        firstInput?.focus();
    }, 0);
}

function closeAuthModal() {
    authModal.classList.add("hidden");
    authModal.setAttribute("aria-hidden", "true");
    openAuthModalBtn.focus({ preventScroll: true });
}

async function loadLandmarks(focusId = "") {
    setStatus("正在从 /api/landmarks 读取景点数据...");

    const response = await fetch("/api/landmarks");
    if (!response.ok) {
        throw new Error(`接口请求失败：${response.status}`);
    }

    const result = await response.json();
    if (!result.success || !Array.isArray(result.data)) {
        throw new Error("接口返回格式不正确");
    }

    allLandmarks = result.data;
    visibleLandmarks = [...allLandmarks];
    selectedLandmarkId = focusId;
    highlightedIds = new Set();
    clearSearchOverlay();

    populateCategoryFilter();
    populateDistanceSelects();
    const markers = renderMarkers(visibleLandmarks);
    renderLandmarkList(visibleLandmarks);

    if (focusId) {
        const focused = allLandmarks.find((landmark) => landmark.id === focusId);
        if (focused) {
            openLandmarkInfo(focused);
        }
    } else if (markers.length > 0) {
        map.setFitView(markers, false, DEFAULT_PADDING);
    }

    setStatus(`已加载 ${allLandmarks.length} 个成都景点 Marker`);
}

async function resetSeedData() {
    if (!window.confirm("恢复示例数据会清空当前所有地标，并恢复 12 个成都示例地标。确定继续吗？")) {
        return;
    }

    setStatus("正在恢复成都示例地标数据...");
    showToast("正在恢复示例数据...", "info");

    const response = await fetch("/api/landmarks/reset-seed", {
        method: "POST",
    });
    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(result.message || `恢复示例数据失败：${response.status}`);
    }

    resetLandmarkForm();
    categoryFilter.value = "";
    keywordSearch.value = "";
    distanceResult.textContent = "请选择两个地标计算距离";
    await loadLandmarks();
    setStatus(result.message || `已恢复 ${result.count || 0} 个成都示例地标`);
    showToast(result.message || "示例数据恢复成功", "success");
}


async function exportLandmarks() {
    setStatus("正在导出当前地标数据...");
    showToast("正在导出 JSON...", "info");

    const response = await fetch("/api/landmarks/export");
    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(result.message || `导出失败：${response.status}`);
    }

    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "chengdu_landmarks_export.json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);

    setStatus(`已导出 ${result.count || 0} 个地标`);
    showToast(`已导出 ${result.count || 0} 个地标`, "success");
}


function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error("读取文件失败"));
        reader.readAsText(file, "utf-8");
    });
}


async function importLandmarksFromFile(file) {
    if (!file) {
        return;
    }

    if (!window.confirm("导入 JSON 会清空当前所有地标，并写入文件中的数据。确定继续吗？")) {
        importJsonInput.value = "";
        return;
    }

    setStatus(`正在读取导入文件：${file.name}`);
    const text = await readFileAsText(file);
    let payload;
    try {
        payload = JSON.parse(text);
    } catch (error) {
        throw new Error(`JSON 解析失败：${error.message}`);
    }

    setStatus("正在导入地标数据...");
    showToast("正在导入 JSON...", "info");
    const response = await fetch("/api/landmarks/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(result.message || `导入失败：${response.status}`);
    }

    resetLandmarkForm();
    categoryFilter.value = "";
    keywordSearch.value = "";
    distanceResult.textContent = "请选择两个地标计算距离";
    await loadLandmarks();
    setStatus(result.message || `已导入 ${result.count || 0} 个地标`);
    showToast(result.message || `已导入 ${result.count || 0} 个地标`, "success");
}

function drawNearbyOverlay(longitude, latitude, radius, unit) {
    clearSearchOverlay();

    const position = [longitude, latitude];
    const radiusInMeters = unit === "km" ? radius * 1000 : unit === "m" ? radius : null;

    searchCenterMarker = new AMap.Marker({
        map,
        position,
        title: "附近搜索中心",
        content: '<div class="search-center-marker">搜</div>',
        zIndex: 130,
    });

    if (radiusInMeters) {
        searchCircle = new AMap.Circle({
            map,
            center: position,
            radius: radiusInMeters,
            strokeColor: "#2563eb",
            strokeOpacity: 0.75,
            strokeWeight: 2,
            fillColor: "#3b82f6",
            fillOpacity: 0.12,
        });
    }
}

async function handleNearbySubmit(event) {
    event.preventDefault();

    const formData = new FormData(nearbyForm);
    const longitude = Number(formData.get("longitude"));
    const latitude = Number(formData.get("latitude"));
    const radius = Number(formData.get("radius"));
    const unit = formData.get("unit") || "km";

    if (!Number.isFinite(longitude) || !Number.isFinite(latitude) || !Number.isFinite(radius)) {
        setStatus("附近搜索失败：经度、纬度、半径必须是数字");
        return;
    }

    setStatus("正在执行附近搜索...");
    const params = new URLSearchParams({ longitude, latitude, radius, unit });
    const response = await fetch(`/api/landmarks/nearby?${params.toString()}`);
    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(result.message || `附近搜索失败：${response.status}`);
    }

    visibleLandmarks = result.data;
    highlightedIds = new Set(visibleLandmarks.map((landmark) => landmark.id));
    selectedLandmarkId = "";
    categoryFilter.value = "";
    keywordSearch.value = "";

    drawNearbyOverlay(longitude, latitude, radius, unit);
    renderMarkers(visibleLandmarks);
    renderLandmarkList(visibleLandmarks);
    fitLandmarks(visibleLandmarks);
    setStatus(`附近搜索完成：${radius} ${unit} 范围内找到 ${visibleLandmarks.length} 个地标`);
    showToast(`附近搜索完成，找到 ${visibleLandmarks.length} 个地标`, "success");
}

async function handleDistanceSubmit(event) {
    event.preventDefault();

    const formData = new FormData(distanceForm);
    const fromId = formData.get("from");
    const toId = formData.get("to");
    const unit = formData.get("unit") || "km";

    if (!fromId || !toId) {
        distanceResult.textContent = "请选择起点和终点";
        return;
    }

    setStatus("正在计算两点距离...");
    const params = new URLSearchParams({ from: fromId, to: toId, unit });
    const response = await fetch(`/api/landmarks/distance?${params.toString()}`);
    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(result.message || `距离计算失败：${response.status}`);
    }

    const fromName = getLandmarkName(fromId);
    const toName = getLandmarkName(toId);
    distanceResult.textContent = `${fromName} 到 ${toName}：${result.distance} ${result.unit}`;

    highlightedIds = new Set([fromId, toId]);
    selectedLandmarkId = fromId;
    visibleLandmarks = allLandmarks.filter((landmark) => highlightedIds.has(landmark.id));
    renderMarkers(visibleLandmarks);
    renderLandmarkList(visibleLandmarks);
    fitLandmarks(visibleLandmarks);
    setStatus(`距离计算完成：${fromName} 到 ${toName} 为 ${result.distance} ${result.unit}`);
    showToast("距离计算完成", "success");
}

async function handleRegisterSubmit(event) {
    event.preventDefault();

    const formData = new FormData(registerForm);
    const payload = Object.fromEntries(formData.entries());
    payload.username = String(payload.username || "").trim();
    payload.password = String(payload.password || "");
    payload.nickname = String(payload.nickname || "").trim();
    payload.email = String(payload.email || "").trim();

    if (!payload.username) {
        throw new Error("请填写用户名");
    }
    if (payload.password.length < 6) {
        throw new Error("密码长度至少 6 位");
    }

    setStatus(`正在注册用户「${payload.username}」...`);
    const response = await fetch("/api/users/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(result.message || `注册失败：${response.status}`);
    }

    registerForm.reset();
    switchAuthTab("login");
    loginForm.elements.username.value = payload.username;
    loginForm.elements.password.value = "";
    loginForm.elements.password.focus();
    setStatus(`用户「${result.data?.username || payload.username}」注册成功`);
    showToast("注册成功，请登录", "success");
}

async function handleLoginSubmit(event) {
    event.preventDefault();

    const formData = new FormData(loginForm);
    const payload = {
        username: String(formData.get("username") || "").trim(),
        password: String(formData.get("password") || ""),
    };

    if (!payload.username) {
        throw new Error("请填写用户名");
    }
    if (!payload.password) {
        throw new Error("请填写密码");
    }

    setStatus(`正在登录用户「${payload.username}」...`);
    const response = await fetch("/api/users/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(result.message || `登录失败：${response.status}`);
    }

    currentUser = result.data;
    loginForm.reset();
    closeAuthModal();
    updateAuthUI();
    await loadCurrentUser();
    setStatus(`用户「${currentUser?.nickname || currentUser?.username || payload.username}」已登录`);
    showToast(result.message || "登录成功", "success");
}

async function handleLogout() {
    const response = await fetch("/api/users/logout", {
        method: "POST",
    });
    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(result.message || `退出登录失败：${response.status}`);
    }

    currentUser = null;
    updateAuthUI();
    setStatus("当前用户已退出登录");
    showToast(result.message || "已退出登录", "success");
}

async function handleAddLandmarkSubmit(event) {
    event.preventDefault();

    const formData = new FormData(addLandmarkForm);
    const rawPayload = Object.fromEntries(formData.entries());
    if (editingLandmarkId) {
        rawPayload.id = editingLandmarkId;
    }
    const payload = validateLandmarkPayload(rawPayload, Boolean(editingLandmarkId));

    const isEditing = Boolean(editingLandmarkId);
    const targetId = editingLandmarkId || payload.id;
    setStatus(isEditing ? `正在更新「${payload.name}」...` : "正在保存新地标...");
    const response = await fetch(isEditing ? `/api/landmarks/${encodeURIComponent(targetId)}` : "/api/landmarks", {
        method: isEditing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(result.message || `新增地标失败：${response.status}`);
    }

    resetLandmarkForm();
    await loadLandmarks(result.data?.id || targetId);
    setStatus(result.message || (isEditing ? "地标更新成功" : "地标保存成功"));
    showToast(result.message || (isEditing ? "地标更新成功" : "地标保存成功"), "success");
}

async function deleteLandmark(landmark) {
    if (!window.confirm(`确定删除「${landmark.name}」吗？`)) {
        return;
    }

    setStatus(`正在删除「${landmark.name}」...`);
    const response = await fetch(`/api/landmarks/${encodeURIComponent(landmark.id)}`, {
        method: "DELETE",
    });
    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(result.message || `删除地标失败：${response.status}`);
    }

    if (editingLandmarkId === landmark.id) {
        resetLandmarkForm();
    }
    await loadLandmarks();
    setStatus(result.message || "地标删除成功");
    showToast(result.message || "地标删除成功", "success");
}


async function copyLandmarkCoordinates(landmark) {
    const position = getLandmarkPosition(landmark);
    if (!position) {
        throw new Error("当前地标没有合法坐标");
    }

    const coordinateText = `${Number(position[0]).toFixed(6)},${Number(position[1]).toFixed(6)}`;
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(coordinateText);
    } else {
        const input = document.createElement("textarea");
        input.value = coordinateText;
        input.setAttribute("readonly", "readonly");
        input.style.position = "fixed";
        input.style.left = "-9999px";
        document.body.appendChild(input);
        input.select();
        document.execCommand("copy");
        input.remove();
    }

    showToast(`已复制坐标：${coordinateText}`, "success");
    setStatus(`已复制「${landmark.name}」坐标：${coordinateText}`);
}

function fillFormCoordinates(position) {
    if (!landmarkFormCard.open) {
        return;
    }

    const longitude = Number(position.lng).toFixed(6);
    const latitude = Number(position.lat).toFixed(6);
    addLandmarkForm.elements.longitude.value = longitude;
    addLandmarkForm.elements.latitude.value = latitude;
    setStatus(`已从地图拾取坐标：${longitude}, ${latitude}`);
    showToast("已填入地图点击位置坐标", "info");
}

function bindEvents() {
    resetViewBtn.addEventListener("click", () => {
        categoryFilter.value = "";
        keywordSearch.value = "";
        distanceResult.textContent = "请选择两个地标计算距离";
        visibleLandmarks = [...allLandmarks];
        highlightedIds = new Set();
        selectedLandmarkId = "";
        clearSearchOverlay();
        renderMarkers(visibleLandmarks);
        renderLandmarkList(visibleLandmarks);
        fitLandmarks(visibleLandmarks);
        setStatus(`已重置视图，显示 ${visibleLandmarks.length} 个地标`);
        showToast("视图已重置", "info");
    });

    categoryFilter.addEventListener("change", applyCategoryFilter);
    keywordSearch.addEventListener("input", applyListFilters);

    openAuthModalBtn.addEventListener("click", () => openAuthModal("login"));
    closeAuthModalBtn.addEventListener("click", closeAuthModal);
    loginTabBtn.addEventListener("click", () => switchAuthTab("login"));
    registerTabBtn.addEventListener("click", () => switchAuthTab("register"));
    logoutBtn.addEventListener("click", () => {
        handleLogout().catch((error) => {
            console.error(error);
            setStatus(error.message);
            showToast(error.message, "error");
        });
    });

    authModal.addEventListener("click", (event) => {
        if (event.target === authModal) {
            closeAuthModal();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !authModal.classList.contains("hidden")) {
            closeAuthModal();
        }
    });

    resetSeedBtn.addEventListener("click", () => {
        resetSeedData().catch((error) => {
            console.error(error);
            setStatus(error.message);
            showToast(error.message, "error");
        });
    });

    exportJsonBtn.addEventListener("click", () => {
        exportLandmarks().catch((error) => {
            console.error(error);
            setStatus(error.message);
            showToast(error.message, "error");
        });
    });

    importJsonBtn.addEventListener("click", () => {
        importJsonInput.click();
    });

    importJsonInput.addEventListener("change", (event) => {
        const file = event.target.files?.[0];
        importLandmarksFromFile(file)
            .catch((error) => {
                console.error(error);
                setStatus(error.message);
                showToast(error.message, "error");
            })
            .finally(() => {
                importJsonInput.value = "";
            });
    });

    nearbyForm.addEventListener("submit", (event) => {
        handleNearbySubmit(event).catch((error) => {
            console.error(error);
            setStatus(error.message);
            showToast(error.message, "error");
        });
    });

    distanceForm.addEventListener("submit", (event) => {
        handleDistanceSubmit(event).catch((error) => {
            console.error(error);
            distanceResult.textContent = error.message;
            setStatus(error.message);
            showToast(error.message, "error");
        });
    });

    loginForm.addEventListener("submit", (event) => {
        handleLoginSubmit(event).catch((error) => {
            console.error(error);
            setStatus(error.message);
            showToast(error.message, "error");
        });
    });

    registerForm.addEventListener("submit", (event) => {
        handleRegisterSubmit(event).catch((error) => {
            console.error(error);
            setStatus(error.message);
            showToast(error.message, "error");
        });
    });

    addLandmarkForm.addEventListener("submit", (event) => {
        handleAddLandmarkSubmit(event).catch((error) => {
            console.error(error);
            setStatus(error.message);
            showToast(error.message, "error");
        });
    });

    cancelEditBtn.addEventListener("click", () => {
        resetLandmarkForm();
        setStatus("已取消编辑，可继续新增地标");
        showToast("已取消编辑", "info");
    });

    document.addEventListener("click", (event) => {
        const editButton = event.target.closest(".info-edit-btn");
        const copyButton = event.target.closest(".info-copy-btn");
        const deleteButton = event.target.closest(".info-delete-btn");
        const actionButton = editButton || copyButton || deleteButton;

        if (!actionButton) {
            return;
        }

        const landmark = allLandmarks.find((item) => item.id === actionButton.dataset.id);
        if (!landmark) {
            showToast("未找到对应地标", "error");
            return;
        }

        if (editButton) {
            startEditLandmark(landmark);
        } else if (copyButton) {
            copyLandmarkCoordinates(landmark).catch((error) => {
                console.error(error);
                setStatus(error.message);
                showToast(error.message, "error");
            });
        } else if (deleteButton) {
            deleteLandmark(landmark).catch((error) => {
                console.error(error);
                setStatus(error.message);
                showToast(error.message, "error");
            });
        }
    });
}

function initMap() {
    if (!window.AMap) {
        setStatus("高德地图脚本加载失败，请检查网络或 AMAP_KEY 配置。 ");
        return;
    }

    map = new AMap.Map("map", {
        center: CHENGDU_CENTER,
        zoom: 12,
        viewMode: "2D",
    });

    infoWindow = new AMap.InfoWindow({
        offset: new AMap.Pixel(0, -30),
    });

    map.on("click", (event) => fillFormCoordinates(event.lnglat));

    bindEvents();
    loadCurrentUser().catch((error) => {
        console.error(error);
        currentUser = null;
        updateAuthUI();
    });
    loadLandmarks().catch((error) => {
        console.error(error);
        landmarkList.innerHTML = `<div class="empty-tip">景点数据加载失败：${escapeHtml(error.message)}</div>`;
        setStatus(`景点数据加载失败：${error.message}`);
    });
}

document.addEventListener("DOMContentLoaded", initMap);