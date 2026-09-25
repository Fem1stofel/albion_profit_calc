const API_URL = "http://127.0.0.1:8000/api";
let scanInterval = null;
let catalogItems = [];

function renderItemInfo(item) {
    const icon = item.icon_url || `https://render.albiononline.com/v1/item/${item.item_id}.png?size=64`;
    const ruName = item.name_ru || item.name || item.item_id;
    const enName = item.name_en || item.item_id;
    return `
        <div class="item-cell">
            <img class="item-icon" loading="lazy" src="${icon}" alt="${ruName}">
            <div class="item-names">
                <span class="item-name-ru">${ruName}</span>
                <span class="item-name-en">${enName}</span>
                <small>${item.item_id}</small>
            </div>
        </div>
    `;
}

function switchTab(tab) {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

    if (tab === "routes") {
        document.querySelector(".tab-btn:nth-child(1)").classList.add("active");
        document.getElementById("routes-tab").classList.add("active");
    } else if (tab === "item") {
        document.querySelector(".tab-btn:nth-child(2)").classList.add("active");
        document.getElementById("item-tab").classList.add("active");
    } else {
        document.querySelector(".tab-btn:nth-child(3)").classList.add("active");
        document.getElementById("scan-tab").classList.add("active");
    }
}

async function loadLocations() {
    try {
        const res = await fetch(`${API_URL}/locations`);
        if (!res.ok) {
            const text = await res.text();
            throw new Error(text || `HTTP ${res.status}`);
        }
        const data = await res.json();

        const fromSelect = document.getElementById("fromLocation");
        const toSelect = document.getElementById("toLocation");

        fromSelect.innerHTML = '<option value="">📍 Город покупки</option>';
        toSelect.innerHTML = '<option value="">📍 Город продажи</option>';

        data.locations.forEach((loc) => {
            const emoji = loc.id === 10 ? "⭐" : "👑";
            const text = `${emoji} ${loc.name} (${loc.tax_rate}%)`;
            fromSelect.add(new Option(text, loc.id));
            toSelect.add(new Option(text, loc.id));
        });
    } catch (e) {
        console.error("Ошибка загрузки городов:", e);
    }
}

async function loadStats() {
    try {
        const res = await fetch(`${API_URL}/health`);
        if (!res.ok) {
            const text = await res.text();
            throw new Error(text || `HTTP ${res.status}`);
        }
        const data = await res.json();
        if (data.status === "ok") {
            document.getElementById("totalOrders").textContent = data.orders.toLocaleString();
        }
    } catch (e) {
        console.error("Ошибка статистики:", e);
    }
}

async function loadItemsCatalogForSearch() {
    try {
        const res = await fetch(`${API_URL}/items-catalog?limit=20000`);
        const data = await res.json();
        if (!res.ok || !data.items) return;

        const list = document.getElementById("itemCatalogList");
        list.innerHTML = "";

        catalogItems = data.items;
        data.items.forEach((item) => {
            const option = document.createElement("option");
            option.value = item.name_ru;
            option.label = `${item.name_ru} / ${item.name_en}`;
            list.appendChild(option);
        });
    } catch (e) {
        console.error("Ошибка каталога предметов:", e);
    }
}

async function searchRoutes() {
    const from = document.getElementById("fromLocation").value;
    const to = document.getElementById("toLocation").value;
    const resultsDiv = document.getElementById("results");

    if (!from || !to) {
        resultsDiv.innerHTML = '<div class="error">⚠️ Выберите оба города!</div>';
        return;
    }

    if (from === to) {
        resultsDiv.innerHTML = '<div class="error">⚠️ Города должны быть разными!</div>';
        return;
    }

    resultsDiv.innerHTML = '<div class="loading">🔍 Поиск маршрутов...</div>';

    try {
        const url = `${API_URL}/transport-routes?from_location=${from}&to_location=${to}&limit=100`;
        const res = await fetch(url);
        const data = await res.json();

        document.getElementById("totalRoutes").textContent = data.count;

        if (data.routes && data.routes.length > 0) {
            let html = `<h3 class="section-title">📊 Найдено маршрутов: ${data.count}</h3>`;
            html += "<div style=\"overflow-x:auto;\"><table><thead><tr><th>Предмет</th><th>Купить в</th><th>Продать в</th><th>Цена покупки</th><th>Цена продажи</th><th>Прибыль/шт</th><th>ROI</th></tr></thead><tbody>";

            data.routes.forEach((route) => {
                html += `<tr>
                    <td>${renderItemInfo(route)}</td>
                    <td><span class="city-badge">${route.from_city}</span></td>
                    <td><span class="city-badge">${route.to_city}</span></td>
                    <td>${route.buy_price.toLocaleString()} 🪙</td>
                    <td>${route.sell_price.toLocaleString()} 🪙</td>
                    <td class="profit">+${route.profit_per_item.toLocaleString()} 🪙</td>
                    <td class="roi">${route.roi}%</td>
                </tr>`;
            });

            html += "</tbody></table></div>";
            resultsDiv.innerHTML = html;
        } else {
            resultsDiv.innerHTML = '<div class="empty">😔 Маршрутов не найдено. Попробуйте другие города или просканируйте предметы во вкладке "🔄 Сканировать всё".</div>';
        }
    } catch (e) {
        resultsDiv.innerHTML = `<div class="error">❌ Ошибка: ${e.message}</div>`;
    }
}

async function analyzeItem() {
    const searchValue = document.getElementById("itemSearch").value.trim();
    const resultsDiv = document.getElementById("results");

    if (!searchValue) {
        resultsDiv.innerHTML = '<div class="error">⚠️ Введите название предмета или ID!</div>';
        return;
    }

    const normalized = searchValue.toLowerCase();
    const resolved = catalogItems.find((item) =>
        item.item_id.toLowerCase() === normalized ||
        item.name_ru.toLowerCase() === normalized ||
        item.name_en.toLowerCase() === normalized
    );
    const itemId = resolved ? resolved.item_id : searchValue;

    resultsDiv.innerHTML = '<div class="loading">🔄 Анализ цен...</div>';

    try {
        const res = await fetch(`${API_URL}/analyze-item/${itemId}`);
        const data = await res.json();

        if (res.ok && data.success) {
            displayItemResults(data);
            loadStats();
        } else {
            resultsDiv.innerHTML = `<div class="error">❌ ${data.detail || "Ошибка"}</div>`;
        }
    } catch (e) {
        resultsDiv.innerHTML = `<div class="error">❌ Ошибка: ${e.message}</div>`;
    }
}

function displayItemResults(data) {
    const resultsDiv = document.getElementById("results");

    let html = "<h2 class=\"section-title\">📦 Предмет</h2>";
    html += renderItemInfo({
        item_id: data.item_id,
        name_ru: data.item_name_ru || data.item_name,
        name_en: data.item_name_en || data.item_id,
        icon_url: data.icon_url
    });

    if (data.prices.length > 0) {
        html += "<h3 class=\"section-title\">💰 Цены в городах</h3>";
        html += "<div style=\"overflow-x:auto;\"><table><thead><tr><th>Город</th><th>Продать (SELL)</th><th>Купить (BUY)</th></tr></thead><tbody>";

        const sorted = [...data.prices].sort((a, b) => a.sell_price - b.sell_price);
        sorted.forEach((p, i) => {
            const badge = i === 0 ? " 🟢" : i === sorted.length - 1 ? " 🔴" : "";
            html += `<tr><td>${p.city}${badge}</td><td class="profit">${p.sell_price.toLocaleString()}</td><td>${p.buy_price || "N/A"}</td></tr>`;
        });

        html += "</tbody></table></div>";
    }

    if (data.best_route) {
        const br = data.best_route;
        html += `<div class="best-route">
            <h3>🏆 ЛУЧШИЙ МАРШРУТ</h3>
            <p><strong>${br.from_city}</strong> → <strong>${br.to_city}</strong><br>
            💰 ${br.buy_price.toLocaleString()} → ${br.sell_price.toLocaleString()} 🪙<br>
            📈 <span class="profit">+${br.profit_per_item.toLocaleString()} 🪙</span> (${br.roi}%)</p>
        </div>`;
    }

    if (data.routes.length > 0) {
        html += `<h3 class="section-title">🚀 Все маршруты (${data.total_routes})</h3>`;
        html += "<div style=\"overflow-x:auto;\"><table><thead><tr><th>Откуда</th><th>Куда</th><th>Купить</th><th>Продать</th><th>Прибыль</th><th>ROI</th></tr></thead><tbody>";

        data.routes.forEach((r) => {
            html += `<tr>
                <td>${r.from_city}</td>
                <td>${r.to_city}</td>
                <td>${r.buy_price.toLocaleString()}</td>
                <td>${r.sell_price.toLocaleString()}</td>
                <td class="profit">+${r.profit_per_item.toLocaleString()}</td>
                <td class="roi">${r.roi}%</td>
            </tr>`;
        });

        html += "</tbody></table></div>";
    }

    resultsDiv.innerHTML = html;
    document.getElementById("totalRoutes").textContent = data.total_routes;
}

async function startScan() {
    const scanBtn = document.getElementById("scanBtn");
    const stopBtn = document.getElementById("stopBtn");
    const scanStatus = document.getElementById("scanStatus");
    const scanBar = document.getElementById("scanBar");
    const scanText = document.getElementById("scanText");

    scanBtn.disabled = true;
    stopBtn.style.display = "block";
    scanStatus.style.display = "block";

    scanInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API_URL}/scan-all-items?batch_size=10`);
            const data = await res.json();

            if (data.status === "running" || data.status === "completed") {
                const p = data.progress;
                const percent = p.total > 0 ? Math.round((p.processed / p.total) * 100) : 0;

                scanBar.style.width = `${percent}%`;
                scanText.innerHTML = `
                    📦 Обработано: ${p.processed}/${p.total} (${percent}%)<br>
                    🔍 Текущий: ${p.current_item || "..."}<br>
                    ✅ Найдено маршрутов: ${p.found_routes}<br>
                    ❌ Ошибок: ${p.errors}
                `;

                loadStats();

                if (data.status === "completed") {
                    clearInterval(scanInterval);
                    scanBtn.disabled = false;
                    stopBtn.style.display = "none";
                    scanText.innerHTML += "<br><br><strong style=\"color:#00d4aa; font-size: 1.1em;\">✅ Сканирование завершено! Перейдите на вкладку \"🚀 Все маршруты\" для просмотра результатов.</strong>";
                    loadStats();
                }
            }
        } catch (e) {
            console.error("Ошибка сканирования:", e);
        }
    }, 3000);
}

function stopScan() {
    clearInterval(scanInterval);
    fetch(`${API_URL}/scan-reset`);

    document.getElementById("scanBtn").disabled = false;
    document.getElementById("stopBtn").style.display = "none";
    document.getElementById("scanText").innerHTML += "<br><br><strong style=\"color:#ff6b6b;\">⏹️ Остановлено пользователем</strong>";
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("itemSearch").addEventListener("keypress", (e) => {
        if (e.key === "Enter") analyzeItem();
    });

    loadLocations();
    loadStats();
    loadItemsCatalogForSearch();

    fetch(`${API_URL}/scan-progress`)
        .then((r) => r.json())
        .then((data) => {
            if (data.running || data.processed > 0) {
                document.getElementById("scanStatus").style.display = "block";
                document.getElementById("scanBtn").disabled = true;
                document.getElementById("stopBtn").style.display = "block";
                startScan();
            }
        });

    setInterval(loadStats, 30000);
});
