const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
if (tg) { tg.expand(); tg.ready(); }

// ==================== SOZLAMALAR ====================
const API = location.hostname === "localhost" || location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : location.origin;

const urlParams = new URLSearchParams(window.location.search);
const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
let token = hashParams.get("token") || urlParams.get("token") || localStorage.getItem("school_token") || "";
if (hashParams.get("token") || urlParams.get("token")) {
    history.replaceState(null, "", window.location.pathname + window.location.search.replace(/[?&]token=[^&]*/, ""));
}
let currentUser = null;
let guestMode = false;

let appName = "LitseyGram";
let schoolName = "Maktab";

let teachersCache = [];
let groupsCache = [];
let scheduleCache = [];
let menuCache = [];

let schedGroupId = null;
let schedEdit = false;
let menuEditOpen = false;

let currentStudent = null;
let studentPhotoUrl = "";

const WEEK_DAYS = ["", "Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"];
const ROLE_LABELS = {
    super: "👑 Asosiy admin",
    admin: "🏛 Admin",
    teacher: "👩‍🏫 O'qituvchi",
    student: "🎒 O'quvchi",
    canteen: "🍽 Oshxona xodimi",
    parent: "👨‍👦 Ota-ona",
};

const screens = {};
["login", "feed", "schedule", "canteen", "create", "profile", "card", "admin", "sadmin", "ann", "pay", "att"].forEach((n) => {
    screens[n] = document.getElementById("screen-" + n);
});

function show(name) {
    Object.entries(screens).forEach(([, s]) => s.classList.remove("active"));
    screens[name].classList.add("active");
    window.scrollTo(0, 0);
}

function todayWeekday() {
    const d = new Date().getDay();
    return d === 0 ? 7 : d;
}

function toMin(t) {
    if (!t) return null;
    const m = String(t).match(/^(\d{1,2}):(\d{2})/);
    return m ? Number(m[1]) * 60 + Number(m[2]) : null;
}

// ==================== APPLE EMOJILAR ====================
const APPLE = {
    "🤍": "1f90d", "❤️": "2764-fe0f", "💬": "1f4ac", "📤": "1f4e4", "🔖": "1f516",
    "🏠": "1f3e0", "📅": "1f4c5", "🍽": "1f37d", "🍽️": "1f37d-fe0f", "➕": "2795", "👤": "1f464",
    "🏆": "1f3c6", "📐": "1f4d0", "📖": "1f4d6", "🔢": "1f522", "📊": "1f4ca",
    "✏️": "270f-fe0f", "📝": "1f4dd", "🏅": "1f3c5", "🎓": "1f393", "⚛️": "269b-fe0f",
    "🏛️": "1f3db-fe0f", "🏛": "1f3da", "💻": "1f4bb", "🇬🇧": "1f1ec-1f1e7", "🍲": "1f372", "🍛": "1f35b",
    "🥟": "1f96f", "🥗": "1f957", "🍞": "1f35e", "🧃": "1f9c3", "🧪": "1f9ea", "🎉": "1f389",
    "💜": "1f49c", "🧡": "1f9e1", "😊": "1f60a", "⚡": "26a1-fe0f", "🖼️": "1f5bc-fe0f",
    "🆕": "1f195", "🔔": "1f514", "👑": "1f451", "🪪": "1faa9", "🎒": "1f392",
    "🪑": "1fa91", "😀": "1f600", "🌡️": "1f321-fe0f", "📋": "1f4cb", "💰": "1f4b0", "🍚": "1f35a"
};
const emojiKeys = Object.keys(APPLE).sort((a, b) => b.length - a.length);
const emojiTest = new RegExp("(" + emojiKeys.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")");
const emojiExec = new RegExp("(" + emojiKeys.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")", "g");

const EMOJI_CDN = "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.1.0/img/apple/64/";

function emjHTML(ch) {
    if (!APPLE[ch]) return "";
    return '<img class="emj" alt="" src="' + EMOJI_CDN + APPLE[ch] + '.png" data-e="' + ch +
        '" onerror="this.replaceWith(document.createTextNode(this.dataset.e))">';
}
function enchant(root) {
    root = root || document.body;
    if (!document.createTreeWalker) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
        acceptNode: function (n) {
            if (!n.nodeValue || !emojiTest.test(n.nodeValue)) return NodeFilter.FILTER_REJECT;
            let p = n.parentElement;
            while (p) {
                const t = p.tagName;
                if (t === "SELECT" || t === "OPTION" || t === "INPUT" || t === "TEXTAREA" || t === "SCRIPT" || t === "STYLE")
                    return NodeFilter.FILTER_REJECT;
                p = p.parentElement;
            }
            return NodeFilter.FILTER_ACCEPT;
        }
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function (n) {
        const s = n.nodeValue, frag = document.createDocumentFragment();
        let last = 0, m; emojiExec.lastIndex = 0;
        while ((m = emojiExec.exec(s))) {
            if (m.index > last) frag.appendChild(document.createTextNode(s.slice(last, m.index)));
            const h = document.createElement("span");
            h.innerHTML = emjHTML(m[0]);
            if (h.firstChild) frag.appendChild(h.firstChild);
            last = m.index + m[0].length;
        }
        if (last < s.length) frag.appendChild(document.createTextNode(s.slice(last)));
        if (n.parentElement) n.replaceWith(frag);
    });
}

// ==================== YORDAMCHILAR ====================
async function api(path, method = "GET", body = null) {
    const headers = {};
    if (token) headers["Authorization"] = "Bearer " + token;
    const opts = { method, headers };
    if (body !== null) {
        headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(body);
    }
    const res = await fetch(API + path, opts);
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    if (res.status === 401) {
        token = "";
        localStorage.removeItem("school_token");
        if (!guestMode) show("login");
        throw new Error((data && data.detail) || "Kirish kerak");
    }
    if (!res.ok) throw new Error((data && data.detail) || "Xatolik yuz berdi");
    return data;
}

// Telegram WebApp ichidan ochilgan bo'lsa — hisobni avtomatik ulash
// (foydalanuvchi «login:parol» yozishiga hojat qolmaydi)
function tryAutoLink() {
    try {
        if (!token || !tg || !tg.initDataUnsafe || !tg.initDataUnsafe.user) return;
        const uid = tg.initDataUnsafe.user.id;
        if (!uid) return;
        api("/link-telegram", "POST", { chat_id: String(uid) }).catch(() => {});
    } catch (e) {}
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
}

function initials(name) {
    const parts = String(name || "?").trim().split(/\s+/).slice(0, 2);
    return parts.map((p) => (p[0] ? p[0].toUpperCase() : "")).join("") || "?";
}

function fmtDate(v) {
    if (!v) return "-";
    return String(v).slice(0, 10);
}

const PHOTO_PLACEHOLDER = "data:image/svg+xml," + encodeURIComponent(
    "<svg xmlns='http://www.w3.org/2000/svg' width='120' height='150'>" +
    "<rect width='100%' height='100%' fill='#e2e8f0'/>" +
    "<text x='50%' y='52%' font-size='15' font-family='sans-serif' text-anchor='middle' fill='#94a3b8'>3x4</text>" +
    "</svg>"
);

let toastTimer = null;
function toast(msg) {
    const t = document.getElementById("toast");
    t.textContent = msg;
    enchant(t);
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 1800);
}

// ==================== BRAND / TOPBAR ====================

function renderBrand(name) {
    const parts = String(name || "LitseyGram").match(/^(.+)(Gram)$/i);
    const bn = document.getElementById("brandname");
    const bs = document.getElementById("brandsuffix");
    document.title = name || "LitseyGram";
    if (parts) {
        bn.textContent = parts[1];
        bs.textContent = "Gram";
    } else {
        bn.textContent = "";
        bs.textContent = name;
    }
}

function renderTopbarInfo() {
    const el = document.getElementById("topbar-info");
    if (guestMode) { el.textContent = "Mehmon rejimi"; }
    else if (currentUser) { el.textContent = ROLE_LABELS[currentUser.role] || currentUser.role; }
    else el.textContent = "";
    enchant(el);
}

function applySettingsNames(a, s) {
    if (a) appName = a; if (s) schoolName = s;
    renderBrand(appName);
    document.getElementById("login-school-name").textContent = schoolName;
    document.getElementById("card-school").textContent = schoolName;
}

async function loadPublicNames() {
    try {
        const [a, s] = await Promise.all([
            fetch(API + "/settings/app").then(r => r.ok ? r.json() : null).catch(() => null),
            fetch(API + "/settings/school").then(r => r.ok ? r.json() : null).catch(() => null),
        ]);
        applySettingsNames(a && a.app_name, s && s.school_name);
    } catch (e) { /* defaults */ }
}

// ==================== NAVBAR ====================

function buildNavbar(items) {
    const nav = document.getElementById("navbar");
    nav.innerHTML = "";
    items.forEach((it) => {
        const d = document.createElement("div");
        d.className = "nav-item";
        d.innerHTML = it.icon;
        d.onclick = () => go(it.id, d);
        nav.appendChild(d);
    });
    enchant(nav);
}

function go(id, el) {
    Object.entries(screens).forEach(([, s]) => s.classList.remove("active"));
    screens[id].classList.add("active");
    document.querySelectorAll("#navbar .nav-item").forEach((n) => n.classList.remove("active"));
    if (el) el.classList.add("active");
    window.scrollTo(0, 0);
    // Ekranni yangilash
    if (id === "schedule") loadSchedule();
    if (id === "canteen") loadCanteen();
    if (id === "create") renderCreateScreen();
    if (id === "profile") renderProfile();
    if (id === "ann") loadMyAnnouncements();
    if (id === "pay") loadMyPayments();
    if (id === "att") loadTeacherAttendance();
}

// ==================== ROLLAR / UI TAYYORLASH ====================

function isBoss() { return currentUser && (currentUser.role === "admin" || currentUser.role === "super"); }

function bootRoleUI() {
    renderTopbarInfo();
    if (currentUser && (currentUser.role === "student" || currentUser.role === "parent")) {
        buildNavbar([
            { id: "feed", icon: "🏠" },
            { id: "schedule", icon: "📅" },
            { id: "canteen", icon: "🍽" },
            { id: "ann", icon: "📢" },
            { id: "pay", icon: "💳" },
            { id: "profile", icon: "👤" },
        ]);
    } else if (guestMode) {
        buildNavbar([
            { id: "feed", icon: "🏠" },
            { id: "schedule", icon: "📅" },
            { id: "canteen", icon: "🍽" },
            { id: "login", icon: "🔑" },
        ]);
    } else if (currentUser && currentUser.role === "teacher") {
        // Ustoz: kundalik ishlar pastki panelda (davomat, jadval, e'lon, post)
        buildNavbar([
            { id: "att", icon: "📋" },
            { id: "schedule", icon: "📅" },
            { id: "ann", icon: "📢" },
            { id: "create", icon: "➕" },
            { id: "feed", icon: "🏠" },
            { id: "profile", icon: "👤" },
        ]);
    } else {
        buildNavbar([
            { id: "feed", icon: "🏠" },
            { id: "schedule", icon: "📅" },
            { id: "canteen", icon: "🍽" },
            { id: "ann", icon: "📢" },
            { id: "create", icon: "➕" },
            { id: "profile", icon: "👤" },
        ]);
    }
    go("feed", document.getElementById("navbar").firstElementChild);
}

// ==================== KIRISH / CHIQISH ====================

document.getElementById("btn-login").onclick = async () => {
    const login = document.getElementById("input-login").value.trim();
    const password = document.getElementById("input-password").value;
    if (!login || !password) { toast("Login va parolni kiriting"); return; }
    try {
        const res = await api("/auth/login", "POST", { login, password });
        token = res.token;
        localStorage.setItem("school_token", token);
        guestMode = false;
        document.getElementById("guest-banner").classList.add("hidden");
        await bootUser(res.user);
        tryAutoLink();
    } catch (e) { toast(e.message); }
};

document.getElementById("btn-guest-from-login").onclick = () => enterGuest();
document.getElementById("btn-guest-login").onclick = () => show("login");

document.getElementById("btn-logout").onclick = async () => {
    if (guestMode) { show("login"); return; }
    try { await api("/auth/logout", "POST"); } catch (e) {}
    token = "";
    localStorage.removeItem("school_token");
    currentUser = null;
    guestMode = false;
    document.getElementById("guest-banner").classList.add("hidden");
    show("login");
};

function enterGuest() {
    guestMode = true;
    currentUser = null;
    document.getElementById("guest-banner").classList.remove("hidden");
    bootRoleUI();
    loadFeed();
}

async function bootUser(user) {
    currentUser = user;
    guestMode = false;
    document.getElementById("guest-banner").classList.add("hidden");
    try {
        const res = await api("/me");
        applySettingsNames(res.app_name, res.school_name);
    } catch (e) {}
    bootRoleUI();
    renderProfile();
    loadFeed();
}

// ==================== FEED ====================

async function loadFeed() {
    try {
        const posts = await api("/posts");
        const list = document.getElementById("posts-list");
        list.innerHTML = "";
        if (!posts.length) {
            list.innerHTML = '<div class="post glass"><p class="note">Hozircha post yo\'q — ustozlar post joylashsa bu yerda chiqadi.</p></div>';
        }
        for (const p of posts) {
            const el = document.createElement("div");
            el.className = "post glass";
            const img = p.image_url
                ? `<img class="post-img" src="${API}${p.image_url}" alt="">`
                : `<div class="post-img-empty g1"><div style="font-size:56px">🎓</div></div>`;
            const actions = guestMode ? "" : `
                <div class="actions">
                    <span class="heart" data-id="${p.id}">🤍</span>
                    <span class="cmt-btn" data-id="${p.id}">💬</span>
                    <span class="right">🔖</span>
                </div>
                <div class="likes" data-base="${p.likes_count}">${p.likes_count} layk</div>
            `;
            const crow = guestMode ? "" : `
                <div class="crow">
                    <span>😊</span>
                    <input placeholder="Izoh qo'shish..." data-id="${p.id}">
                    <button class="cmt-submit" data-id="${p.id}">Joylash</button>
                </div>
            `;
            el.innerHTML = `
                <div class="post-head">
                    <div class="pav"><div class="pav-inner">${escapeHtml(initials(p.teacher_name))}</div></div>
                    <div>
                        <div class="pname">${escapeHtml(p.teacher_name)}</div>
                        <div class="psub">Maktab post</div>
                    </div>
                </div>
                ${img}
                <div class="post-body">
                    ${p.title ? `<div class="p-title">${escapeHtml(p.title)}</div>` : ""}
                    ${p.content ? `<div class="p-content">${escapeHtml(p.content)}</div>` : ""}
                </div>
                ${actions}
                <div class="time">${escapeHtml(String(p.created_at).slice(0, 16))}</div>
                ${crow}
            `;
            list.appendChild(el);
        }

        if (!guestMode) {
            list.querySelectorAll(".heart").forEach((btn) => {
                btn.onclick = async () => {
                    try {
                        const res = await api(`/posts/${btn.dataset.id}/like`, "POST", {});
                        const likeBox = btn.closest(".post").querySelector(".likes");
                        const base = parseInt(likeBox.dataset.base) || 0;
                        if (res.liked) {
                            btn.textContent = "❤️";
                            btn.classList.add("liked");
                            likeBox.textContent = res.count + " layk";
                            likeBox.dataset.base = res.count;
                        } else {
                            btn.textContent = "🤍";
                            btn.classList.remove("liked");
                            likeBox.textContent = res.count + " layk";
                            likeBox.dataset.base = res.count;
                        }
                        enchant(btn);
                    } catch (e) { toast(e.message); }
                };
            });

            list.querySelectorAll(".cmt-submit").forEach((b) => {
                b.onclick = async () => {
                    const input = b.closest(".crow").querySelector("input");
                    const text = input.value.trim();
                    if (!text) return;
                    try {
                        await api(`/posts/${b.dataset.id}/comment`, "POST", { content: text });
                        toast("Izoh joylandi ✔");
                        loadFeed();
                    } catch (e) { toast(e.message); }
                };
            });
        }

        const stories = await api("/stories");
        const slist = document.getElementById("stories-list");
        slist.innerHTML = "";
        if (!stories.length) slist.innerHTML = '<p class="note" style="padding:0 4px">Hozircha story yo\'q.</p>';
        for (const s of stories) {
            const el = document.createElement("div");
            el.className = "story";
            if (s.image_url) {
                el.innerHTML = `<div class="ring"><img src="${API}${s.image_url}" alt=""></div>`;
            } else {
                el.innerHTML = `<div class="ring"><div class="ring-inner">${escapeHtml(initials(s.teacher_name))}</div></div>`;
            }
            el.innerHTML += `<span>${escapeHtml(s.teacher_name)}</span>`;
            el.onclick = () => toast(s.content ? s.teacher_name + ": " + s.content : s.teacher_name + ": story");
            slist.appendChild(el);
        }
        enchant(slist);
        enchant(list);
    } catch (e) {
        if (!guestMode) toast(e.message);
    }
}

// ==================== JADVAL ====================

async function loadSchedule() {
    try {
        const groups = await api("/groups");
        groupsCache = groups;

        const chips = document.getElementById("sched-groups");
        chips.innerHTML = "";

        let ownGroupId = null;
        if (currentUser && currentUser.role === "student") {
            try {
                const me = await api("/students/me");
                ownGroupId = me.group_id;
            } catch (e) {}
        }

        const isAdminB = isBoss();
        if (ownGroupId !== null && currentUser.role === "student") {
            const g = groups.find((x) => x.id === ownGroupId);
            schedGroupId = ownGroupId;
            if (g) chips.innerHTML = `<div class="chip active">${escapeHtml(g.name)}</div><p style="font-size:12px;color:var(--muted);">Sizning guruhingiz</p>`;
        } else {
            if (!schedGroupId && groups.length) schedGroupId = groups[0].id;
            for (const g of groups) {
                const c = document.createElement("div");
                c.className = "chip" + (schedGroupId === g.id ? " active" : "");
                c.textContent = g.name;
                c.onclick = () => { schedGroupId = g.id; schedEdit = false; loadSchedule(); };
                chips.appendChild(c);
            }
            if (!groups.length) chips.innerHTML = '<p class="note">Avval admin panelda guruh oching.</p>';
        }
        enchant(chips);

        // Admin uchun form
        document.getElementById("sched-edit-card").classList.toggle("hidden", !isAdminB);
        if (isAdminB) {
            const sel = document.getElementById("sch-g");
            sel.innerHTML = groups.map((g) => `<option value="${g.id}">${escapeHtml(g.name)}</option>`).join("");
            if (schedGroupId) sel.value = String(schedGroupId);
        }

        scheduleCache = await api("/schedule" + (schedGroupId ? "?group_id=" + schedGroupId : ""));
        renderSchedule();
    } catch (e) { toast(e.message); }
}

function renderSchedule() {
    const wd = todayWeekday();
    document.getElementById("sched-date").textContent = "Bugun — " + WEEK_DAYS[wd];

    const todayList = scheduleCache.filter((l) => l.weekday === wd);
    const groupName = scheduleCache.length ? (scheduleCache[0].group_name || "") : "";
    document.getElementById("sched-count").textContent = todayList.length + " ta dars" + (groupName ? " • " + groupName : "");

    const now = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();

    const box = document.getElementById("sched-list");
    box.innerHTML = "";
    if (!todayList.length) { box.innerHTML = '<p class="note">Bugun dars yo\'q 🎉</p>'; }
    for (const l of todayList) {
        const start = toMin(l.start_time), end = toMin(l.end_time);
        let cls = "", badge = "";
        if (start !== null && end !== null) {
            if (end < nowMin) { cls = "done"; }
            else if (start <= nowMin && nowMin < end) { cls = "now"; badge = ' <span class="badge-now">DARS HOZIR</span>'; }
        }
        const del = isBoss()
            ? `<button class="del" data-id="${l.id}" title="O'chirish">🗑</button>` : "";
        const div = document.createElement("div");
        div.className = "lesson " + cls;
        div.innerHTML = `
            <div class="lt">${escapeHtml(l.start_time || "-")}<br>${escapeHtml(l.end_time || "")}</div>
            <div><div class="ln">${escapeHtml(l.subject)}${badge}</div>
            <div class="li">${escapeHtml(l.teacher_name || "")}${l.room ? " • " + escapeHtml(l.room) : ""}</div></div>
            ${del}
        `;
        if (isBoss()) {
            div.querySelector(".del").onclick = async () => {
                try { await api("/schedule/" + l.id, "DELETE"); toast("Dars o'chirildi"); loadSchedule(); }
                catch (e) { toast(e.message); }
            };
        }
        box.appendChild(div);
    }

    // Hafta ko'rinishi
    const wl = document.getElementById("sched-week-list");
    wl.innerHTML = "";
    for (let wd2 = 1; wd2 <= 7; wd2++) {
        const cnt = scheduleCache.filter((l) => l.weekday === wd2).length;
        wl.innerHTML += `<div class="weekrow"><b>${WEEK_DAYS[wd2]}</b><span>${cnt ? cnt + " dars" : "Dars yo'q"}</span></div>`;
    }
    enchant(box);
}

document.getElementById("btn-sch-add").onclick = async () => {
    try {
        const body = {
            group_id: parseInt(document.getElementById("sch-g").value),
            weekday: parseInt(document.getElementById("sch-wd").value),
            lesson_no: parseInt(document.getElementById("sch-no").value) || 1,
            start_time: document.getElementById("sch-start").value.trim() || null,
            end_time: document.getElementById("sch-end").value.trim() || null,
            subject: document.getElementById("sch-subj").value.trim(),
            teacher_name: document.getElementById("sch-teacher").value.trim() || null,
            room: document.getElementById("sch-room").value.trim() || null,
        };
        if (!body.subject) { toast("Fan nomini kiriting"); return; }
        await api("/schedule", "POST", body);
        toast("Dars jadvalga qo'shildi ✔");
        ["sch-no", "sch-start", "sch-end", "sch-subj", "sch-teacher", "sch-room"].forEach((id) => (document.getElementById(id).value = ""));
        schedGroupId = body.group_id;
        loadSchedule();
    } catch (e) { toast(e.message); }
};

// ==================== OSHXONA ====================

async function loadCanteen() {
    try {
        menuCache = await api("/menu");
        const wd = todayWeekday();
        document.getElementById("canteen-date").textContent = "Bugun — " + WEEK_DAYS[wd];

        const role = currentUser ? currentUser.role : null;
        const canEdit = role === "canteen" || role === "super";
        document.getElementById("menu-edit-card").classList.toggle("hidden", !canEdit);
        document.getElementById("canteen-sub").textContent = canEdit
            ? "Siz menyuni tahrirlashingiz mumkin"
            : "Bugungi menyu va narxlar • Tahrirlash huquqi: oshxona rahbari / oshpaz";

        const todayItems = menuCache.filter((m) => m.weekday === wd);
        const box = document.getElementById("menu-list");
        box.innerHTML = "";
        if (!todayItems.length) box.innerHTML = '<p class="note">Bugun menyu tayyorlanmoqda 🍳</p>';
        for (const m of todayItems) {
            const del = canEdit ? `<button class="del" data-id="${m.id}" title="O'chirish">🗑</button>` : "";
            const div = document.createElement("div");
            div.className = "menu-row";
            div.innerHTML = `
                <div class="me">${escapeHtml(m.emoji || "🍽")}</div>
                <div class="mn"><b>${escapeHtml(m.name)}</b>${m.description ? `<span>${escapeHtml(m.description)}</span>` : ""}</div>
                ${m.price ? `<div class="mp">${escapeHtml(m.price)} so'm</div>` : ""}
                ${del}
            `;
            if (canEdit) {
                div.querySelector(".del").onclick = async () => {
                    try { await api("/menu/" + m.id, "DELETE"); toast("Taom o'chirildi"); loadCanteen(); }
                    catch (e) { toast(e.message); }
                };
            }
            box.appendChild(div);
        }

        // Hafta
        const wm = document.getElementById("menu-week");
        wm.innerHTML = "";
        for (let d = 1; d <= 6; d++) {
            const items = menuCache.filter((m) => m.weekday === d);
            const names = items.map((m) => m.name).slice(0, 3).join(", ");
            wm.innerHTML += `<div class="weekrow"><b>${WEEK_DAYS[d]}</b><span>${names || "—"}</span></div>`;
        }
        enchant(box);
    } catch (e) { toast(e.message); }
}

document.getElementById("btn-men-add").onclick = async () => {
    try {
        const body = {
            weekday: parseInt(document.getElementById("men-wd").value),
            emoji: document.getElementById("men-emoji").value.trim() || "🍲",
            name: document.getElementById("men-name").value.trim(),
            description: document.getElementById("men-desc").value.trim() || null,
            price: document.getElementById("men-price").value.replace(/\s/g, "") || null,
        };
        if (!body.name) { toast("Taom nomini kiriting"); return; }
        await api("/menu", "POST", body);
        toast("Menyuga qo'shildi ✔");
        ["men-name", "men-desc", "men-price"].forEach((id) => (document.getElementById(id).value = ""));
        loadCanteen();
    } catch (e) { toast(e.message); }
};

// ==================== YARATISH EKRANI (rolga qarab) ====================

function renderCreateScreen() {
    const role = currentUser ? currentUser.role : null;
    ["create-teacher", "create-accounts", "create-canteen", "create-default"].forEach((id) =>
        document.getElementById(id).classList.add("hidden")
    );
    if (guestMode) { document.getElementById("create-default").classList.remove("hidden"); return; }
    if (role === "teacher") document.getElementById("create-teacher").classList.remove("hidden");
    else if (role === "canteen") document.getElementById("create-canteen").classList.remove("hidden");
    else if (isBoss()) {
        document.getElementById("create-accounts").classList.remove("hidden");
        fillCreateForm();
    } else document.getElementById("create-default").classList.remove("hidden");
    enchant(screens.create);
}

function fillCreateForm() {
    const roleSel = document.getElementById("acc-role");
    const isSuper = currentUser.role === "super";
    Array.from(roleSel.options).forEach((o) => {
        if (o.value === "admin") o.disabled = !isSuper;
    });
    if (roleSel.value === "admin" && !isSuper) roleSel.value = "teacher";
    roleHint();

    const gSel = document.getElementById("acc-group");
    gSel.innerHTML = '<option value="">Guruh tanlanmagan</option>' + groupsCache.map((g) => `<option value="${g.id}">${escapeHtml(g.name)}</option>`).join("");

    const tSel = document.getElementById("acc-teacher");
    tSel.innerHTML = '<option value="">Repetitor yo\'q</option><option value="__other__">Boshqa ustoz (qo\'lda kiritish)</option>' +
        teachersCache.map((t) => {
            const label = t.full_name + (t.subject ? ` (${t.subject})` : "");
            return `<option value="${t.id}" data-subject="${escapeHtml(t.subject || "")}">${escapeHtml(label)}</option>`;
        }).join("");
}

async function ensureCreateCaches() {
    if (!groupsCache.length) { try { groupsCache = await api("/groups"); } catch (e) {} }
    if (!teachersCache.length) { try { teachersCache = await api("/teachers"); } catch (e) {} }
}

const ROLE_HINTS = {
    teacher: "👩‍🏫 Post va story joylash huquqi (fan talab qilinadi)",
    student: "🎒 Feed, dars jadvali, oshxona + shaxsiy kirish kartochkasi",
    canteen: "🍽 Faqat oshxona menyusini tahrirlash huquqi (lavozim kiritiladi)",
    admin: "🏛 Guruhlar, ustozlar, o'quvchilar, jadval — faqat ASOSIY ADMIN ochadi",
};

function roleHint() {
    const v = document.getElementById("acc-role").value;
    document.getElementById("acc-subj-box").classList.toggle("hidden", !(v === "teacher"));
    document.getElementById("acc-position-box").classList.toggle("hidden", !(v === "canteen" || v === "admin"));
    document.getElementById("acc-student-box").classList.toggle("hidden", v !== "student");
    document.getElementById("acc-hint").textContent = ROLE_HINTS[v] || "";
    enchant(document.getElementById("acc-hint"));
}

document.getElementById("acc-role").onchange = () => { fillCreateForm(); roleHint(); };

document.getElementById("acc-teacher").onchange = () => {
    const val = document.getElementById("acc-teacher").value;
    const fields = document.getElementById("acc-rep-fields");
    if (!val) { fields.classList.add("hidden"); return; }
    fields.classList.remove("hidden");
    if (val === "__other__") {
        document.getElementById("acc-rep-name").value = "";
        document.getElementById("acc-rep-subject").value = "";
    } else {
        const opt = document.getElementById("acc-teacher").selectedOptions[0];
        document.getElementById("acc-rep-name").value = opt ? opt.textContent.replace(/\s*\(.*\)$/, "") : "";
        document.getElementById("acc-rep-subject").value = (opt && opt.dataset.subject) || "";
    }
};

document.getElementById("btn-acc-create").onclick = async () => {
    const role = document.getElementById("acc-role").value;
    const full_name = document.getElementById("acc-name").value.trim();
    const login = document.getElementById("acc-login").value.trim();
    const password = document.getElementById("acc-password").value;
    if (!full_name || !login || !password) { toast("F.I.Sh., login va parolni kiriting"); return; }
    try {
        if (role === "teacher") {
            const subject = document.getElementById("acc-subj").value.trim();
            if (!subject) { toast("Fan kiriting"); return; }
            await api("/teachers", "POST", { full_name, subject, login, password });
        } else if (role === "student") {
            const teacherVal = document.getElementById("acc-teacher").value;
            const body = {
                full_name, login, password,
                group_id: document.getElementById("acc-group").value ? parseInt(document.getElementById("acc-group").value) : null,
                teacher_id: teacherVal && teacherVal !== "__other__" ? parseInt(teacherVal) : null,
                repetitor_fullname: null, repetitor_subject: null, repetitor_start_date: null,
                info: null,
            };
            if (teacherVal) {
                const repName = document.getElementById("acc-rep-name").value.trim();
                const repSubject = document.getElementById("acc-rep-subject").value.trim();
                const repDate = document.getElementById("acc-rep-date").value;
                if (!repName) { toast("Repetitor tanlandi — ustoz F.I.Sh.ni kiriting"); return; }
                if (!repSubject) { toast("Repetitor tanlandi — fanni kiriting"); return; }
                if (!repDate) { toast("Repetitor tanlandi — kelgan sanani kiriting"); return; }
                body.repetitor_fullname = repName;
                body.repetitor_subject = repSubject;
                body.repetitor_start_date = repDate;
            }
            await api("/students", "POST", body);
        } else {
            const position = document.getElementById("acc-position").value.trim() || null;
            await api("/users", "POST", { role, full_name, position, login, password });
        }
        toast("Hisob ochildi ✔ (" + (ROLE_LABELS[role] || role) + ")");
        ["acc-name", "acc-subj", "acc-position", "acc-login", "acc-password", "acc-rep-name", "acc-rep-subject", "acc-rep-date"].forEach((id) => (document.getElementById(id).value = ""));
        document.getElementById("acc-teacher").value = "";
        document.getElementById("acc-rep-fields").classList.add("hidden");
        groupsCache = []; teachersCache = [];
        if (screens.admin.classList.contains("active")) loadAdminData();
        if (screens.sadmin.classList.contains("active")) loadSadminUsers();
    } catch (e) { toast(e.message); }
};

// ==================== POST / STORY (ustoz) ====================

async function uploadImage(file) {
    const fd = new FormData();
    fd.append("file", file);
    const resp = await fetch(API + "/upload", {
        method: "POST",
        headers: { "Authorization": "Bearer " + token },
        body: fd,
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.detail || "Rasm yuklashda xato");
    return data.url;
}

document.getElementById("btn-post").onclick = async () => {
    const title = document.getElementById("post-title").value.trim();
    const content = document.getElementById("post-content").value.trim();
    const fileInput = document.getElementById("post-file");
    if (!title) { toast("Sarlavha kiriting"); return; }
    try {
        let image_url = null;
        if (fileInput.files.length) image_url = await uploadImage(fileInput.files[0]);
        await api("/posts", "POST", { title, content, image_url });
        toast("Post joylandi ✔");
        document.getElementById("post-title").value = "";
        document.getElementById("post-content").value = "";
        fileInput.value = "";
        loadFeed();
        go("feed", document.getElementById("navbar").firstElementChild);
    } catch (e) { toast(e.message); }
};

document.getElementById("btn-story").onclick = async () => {
    const content = document.getElementById("story-text").value.trim();
    const fileInput = document.getElementById("story-file");
    if (!content && !fileInput.files.length) { toast("Matn yoki rasm kiriting"); return; }
    try {
        let image_url = null;
        if (fileInput.files.length) image_url = await uploadImage(fileInput.files[0]);
        const expires = new Date(Date.now() + 24 * 3600 * 1000).toISOString();
        await api("/stories", "POST", { content, image_url, expires_at: expires });
        toast("Story joylandi ✔ (24 soat)");
        document.getElementById("story-text").value = "";
        fileInput.value = "";
        loadFeed();
        go("feed", document.getElementById("navbar").firstElementChild);
    } catch (e) { toast(e.message); }
};

// ==================== E'LONLAR ====================

// Yozish oynasini ochish: E'lonlar ekraniga o'tadi va composer ko'rinadi
function openAnnTab() {
    if (!isBoss()) { toast("Bu bo'lim faqat adminlar uchun"); return; }
    show("ann");
    const compose = document.getElementById("adm-ann");
    compose.classList.remove("hidden");
    loadComposerData();
    compose.scrollIntoView({ behavior: "smooth", block: "start" });
}

// Yozish oynasi uchun kerakli ma'lumotlar: guruhlar va e'lonlar tarixi
async function loadComposerData() {
    try {
        groupsCache = await api("/groups");
    } catch (e) {
        groupsCache = groupsCache || [];
    }
    fillAnnGroupSelect();
    loadAnnouncements();
}

// E'lonlar ekranini ochganda (menyudan)
async function loadMyAnnouncements() {
    document.getElementById("btn-ann-write").classList.toggle("hidden", !isBoss());
    document.getElementById("adm-ann").classList.add("hidden");
    const box = document.getElementById("my-ann-list");
    try {
        const list = await api("/announcements/mine");
        box.innerHTML = "";
        if (!list.length) {
            box.innerHTML = '<p class="note">Hozircha e\'lon yo\'q</p>';
            return;
        }
        for (const a of list) {
            const scope = a.scope === "group" ? `🎓 ${a.group_name || "guruh"}` : "🌍 Barchalariga";
            const date = String(a.created_at || "").slice(0, 16);
            const div = document.createElement("div");
            div.className = "row";
            div.innerHTML = `
                <div class="row-head">📢 ${escapeHtml(scope)} <span class="badge">${escapeHtml(date)}</span></div>
                <div class="row-sub">${escapeHtml(a.body)}</div>
            `;
            box.appendChild(div);
        }
        enchant(box);
    } catch (e) {
        box.innerHTML = '<p class="note">E\'lonlar yuklanmadi</p>';
    }
}

// Qamrov tanlanganda guruh tanlash qutisini ko'rsatish
document.getElementById("ann-scope").onchange = () => {
    const isGroup = document.getElementById("ann-scope").value === "group";
    document.getElementById("ann-group-box").classList.toggle("hidden", !isGroup);
    if (isGroup) fillAnnGroupSelect();
};

function fillAnnGroupSelect() {
    const sel = document.getElementById("ann-group");
    sel.innerHTML = groupsCache.length
        ? groupsCache.map((g) => `<option value="${g.id}">${escapeHtml(g.name)}</option>`).join("")
        : '<option value="">Guruh yo\'q — avval guruh oching</option>';
}

// Yuborilgan e'lonlar tarixi
async function loadAnnouncements() {
    const box = document.getElementById("ann-list");
    try {
        const list = await api("/announcements");
        box.innerHTML = "";
        if (!list.length) {
            box.innerHTML = '<p class="note">Hozircha e\'lon yuborilmagan</p>';
            return;
        }
        for (const a of list) {
            const scopeLabel = a.scope === "group"
                ? `🎓 ${a.group_name || "guruh"}`
                : "🌍 Barchalariga";
            const date = String(a.created_at || "").slice(0, 16);
            const sentNote = a.failed_count
                ? `Yuborildi: ${a.sent_count} • Yuborilmadi: ${a.failed_count}`
                : `Yuborildi: ${a.sent_count}`;
            const div = document.createElement("div");
            div.className = "row";
            div.innerHTML = `
                <div class="row-head">${escapeHtml(scopeLabel)} <span class="badge">${escapeHtml(date)}</span></div>
                <div class="row-sub">${escapeHtml(a.body.slice(0, 160))}${a.body.length > 160 ? "…" : ""}</div>
                <div class="row-sub" style="margin-top:4px;">📤 ${escapeHtml(sentNote)} • Rejada: ${a.queued} ta</div>
            `;
            box.appendChild(div);
        }
        enchant(box);
    } catch (e) {
        box.innerHTML = '<p class="note">Tarix yuklanmadi</p>';
    }
}

document.getElementById("btn-ann-write").onclick = () => openAnnTab();

// E'lonni yuborish
document.getElementById("btn-ann-send").onclick = async () => {
    const sendBtn = document.getElementById("btn-ann-send");
    const result = document.getElementById("ann-result");
    const body = document.getElementById("ann-body").value.trim();
    const scope = document.getElementById("ann-scope").value;
    const groupId = document.getElementById("ann-group").value;

    if (!body) { toast("E'lon matnini yozing"); return; }
    if (scope === "group" && !groupId) { toast("Guruhni tanlang"); return; }

    sendBtn.disabled = true;
    try {
        const res = await api("/announcements", "POST", {
            body,
            scope,
            group_id: scope === "group" ? parseInt(groupId, 10) : null,
        });
        let msg = `✅ E'lon qabul qilindi: ${res.queued} ta foydalanuvchiga yuborishga qo'yildi`;
        if (res.missed > 0) msg += ` • ${res.missed} ta botga ulanmagan (ulansa keyingi e'londa oladi)`;
        result.textContent = msg;
        result.classList.remove("hidden");
        enchant(result);
        toast("E'lon yuborishga qo'yildi ✔");
        document.getElementById("ann-body").value = "";
        loadAnnouncements();
    } catch (e) {
        toast(e.message || "E'lon yuborilmadi");
    } finally {
        sendBtn.disabled = false;
    }
};

// ==================== DAVOMAT (admin) ====================

function todayISO() {
    const d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}

async function loadAttendance() {
    const dateInput = document.getElementById("att-date");
    if (!dateInput.value) dateInput.value = todayISO();
    loadAttendanceStatus(dateInput.value);
    try {
        const data = await api("/attendance/stats?date=" + encodeURIComponent(dateInput.value));
        const box = document.getElementById("att-summary");
        box.innerHTML = "";
        if (!data.groups.length) {
            box.innerHTML = '<div class="glass rows-box"><p class="note">Hozircha guruh yo\'q</p></div>';
            return;
        }
        for (const g of data.groups) {
            const card = document.createElement("div");
            card.className = "stat-card glass";
            card.style.cursor = "pointer";
            const color = g.percent >= 95 ? "" : (g.percent >= 85 ? " style=\"color:#e08600\"" : " style=\"color:#e03c3c\"");
            card.innerHTML = `
                <div class="st-ic">🏫</div>
                <div class="st-num"${color}>${g.percent}%</div>
                <div class="st-lb">${escapeHtml(g.group_name)} • ${g.absent} kelmadi / ${g.total}</div>
            `;
            card.onclick = () => loadAttendanceDetail(g.group_id, g.group_name);
            box.appendChild(card);
        }
        enchant(box);
        document.getElementById("att-detail").innerHTML = '<p class="note">Guruhni tanlang — kimlar kelmaganini ko\'rasiz</p>';
    } catch (e) {}
}

async function loadAttendanceDetail(groupId, groupName) {
    const box = document.getElementById("att-detail");
    box.innerHTML = '<p class="note">Yuklanmoqda...</p>';
    try {
        const date = document.getElementById("att-date").value;
        const list = await api(`/attendance/list?date=${encodeURIComponent(date)}&group_id=${groupId}`);
        box.innerHTML = "";
        const head = document.createElement("div");
        head.className = "row";
        head.innerHTML = `<div class="row-head">📋 ${escapeHtml(groupName)} — ${escapeHtml(date)}</div>`;
        box.appendChild(head);
        if (!list.length) {
            const p = document.createElement("p");
            p.className = "note";
            p.textContent = "Bu kuni kimdir kelmagan deb belgilanmagan — hammasi keldi ✔";
            box.appendChild(p);
            return;
        }
        for (const a of list) {
            const div = document.createElement("div");
            div.className = "row";
            div.innerHTML = `
                <div class="row-head">❌ ${escapeHtml(a.full_name)}</div>
                <div class="row-sub">${a.excuse_comment ? "Sabab: " + escapeHtml(a.excuse_comment) : "Sabab kiritilmagan"}</div>
            `;
            if (a.has_photo) {
                const btn = document.createElement("button");
                btn.className = "btn-mini";
                btn.textContent = "📷 Rasmiy hujjatni ko'rish";
                btn.onclick = async () => {
                    if (div.querySelector(".excuse-photo")) return;
                    try {
                        const res = await fetch(`${API}/attendance/${a.id}/excuse-photo`, {
                            headers: { Authorization: "Bearer " + token },
                        });
                        if (!res.ok) throw new Error("Rasm ochilmadi");
                        const img = document.createElement("img");
                        img.className = "excuse-photo";
                        img.src = URL.createObjectURL(await res.blob());
                        div.appendChild(img);
                    } catch (e) { toast(e.message); }
                };
                div.appendChild(btn);
            }
            box.appendChild(div);
        }
        enchant(box);
    } catch (e) { box.innerHTML = '<p class="note">Xatolik: ' + escapeHtml(e.message) + '</p>'; }
}

document.getElementById("att-date").onchange = () => {
    document.getElementById("att-detail").innerHTML = "";
    loadAttendance();
};


// ==================== DAVOMAT: ustoz veb-ekrani ====================

function tashkentTime(utcText) {
    // Bazadagi vaqt UTC (CURRENT_TIMESTAMP): Toshkent vaqtiga o'tkazamiz
    if (!utcText) return "";
    const d = new Date(String(utcText).replace(" ", "T") + "Z");
    if (isNaN(d)) return "";
    return d.toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Tashkent" });
}

// Admin: bugungi holat — qaysi guruh davomat olgan, qaysi biri olinmagan
async function loadAttendanceStatus(date) {
    const box = document.getElementById("att-status");
    try {
        const data = await api("/attendance/sessions?date=" + encodeURIComponent(date));
        const done = data.groups.filter((g) => g.taken).length;
        const lines = data.groups.map((g) => g.taken
            ? `✅ ${escapeHtml(g.name)} — olindi (${tashkentTime(g.marked_at)}), ${g.absent} ta kelmadi`
            : `⏳ ${escapeHtml(g.name)} — olinmagan`).join("<br>");
        box.innerHTML = `<div class="row-head">📊 Bugungi holat: ${done} / ${data.groups.length} guruh davomat olgan</div>
            <div class="row-sub" style="line-height:1.8;margin-top:6px;">${lines || "Guruh yo'q"}</div>`;
    } catch (e) {
        box.innerHTML = '<p class="note">Holat yuklanmadi</p>';
    }
}

let tAttState = { students: [], days: [], date: "" };

async function loadTeacherAttendance() {
    const gSel = document.getElementById("att-tgroup");
    const dInp = document.getElementById("att-tdate");
    if (!dInp.value) dInp.value = todayISO();
    try {
        const groups = await api("/groups");
        const keep = gSel.value;
        gSel.innerHTML = groups.map((g) => `<option value="${g.id}">${escapeHtml(g.name)}</option>`).join("");
        if (keep && groups.some((g) => String(g.id) === keep)) gSel.value = keep;
    } catch (e) {
        gSel.innerHTML = "";
    }
    gSel.onchange = loadTeacherGroup;
    dInp.onchange = loadTeacherGroup;
    document.getElementById("btn-att-save").onclick = saveTeacherAttendance;
    await loadTeacherGroup();
}

function weekdayShort(iso) {
    return ["Ya", "Du", "Se", "Ch", "Pa", "Ju", "Sh"][new Date(iso + "T00:00:00").getDay()];
}

async function loadTeacherGroup() {
    const gid = document.getElementById("att-tgroup").value;
    const date = document.getElementById("att-tdate").value || todayISO();
    const list = document.getElementById("att-tlist");
    const week = document.getElementById("att-tweek");
    if (!gid) { list.innerHTML = '<p class="note">Guruh yo\'q</p>'; week.innerHTML = ""; return; }
    try {
        const wk = await api(`/attendance/week?group_id=${gid}&start=${encodeURIComponent(date)}`);
        tAttState = { students: wk.students, days: wk.days, date };
        // Haftalik jadval
        const cells = (s) => wk.days.map((d) => {
            const st = s.days[d].status;
            const mark = st === "present" ? "✅" : st === "absent" ? "❌" : "—";
            return `<td style="text-align:center;padding:6px 4px;">${mark}</td>`;
        }).join("");
        week.innerHTML = wk.students.length
            ? `<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:14px;">
                <tr><th style="text-align:left;padding:6px 4px;">O'quvchi</th>${wk.days.map((d) => `<th style="padding:6px 4px;">${weekdayShort(d)}<br><small>${d.slice(5)}</small></th>`).join("")}</tr>
                ${wk.students.map((s) => `<tr><td style="padding:6px 4px;">${escapeHtml(s.name)}</td>${cells(s)}</tr>`).join("")}
               </table></div>`
            : '<p class="note">Bu guruhda o\'quvchi yo\'q</p>';
        // Tanlangan kun ro'yxati
        const idx = wk.days.indexOf(date);
        if (idx < 0) {
            list.innerHTML = '<p class="note">Tanlangan sana dushanba–juma oralig\'ida emas (dam olish kuni). Ish kunini tanlang.</p>';
            document.getElementById("btn-att-save").disabled = true;
            return;
        }
        document.getElementById("btn-att-save").disabled = false;
        if (!wk.students.length) { list.innerHTML = '<p class="note">Bu guruhda o\'quvchi yo\'q</p>'; return; }
        const taken = wk.taken.includes(date);
        list.innerHTML = `<div class="row-sub" style="margin-bottom:8px;">${taken ? "Bu kun davomat olingan — o'zgartirish mumkin" : "Bu kun hali davomat olinmagan"}</div>` +
            wk.students.map((s) => {
                const absent = s.days[date].status === "absent";
                return `<label class="row" style="display:flex;align-items:center;gap:10px;cursor:pointer;">
                    <input type="checkbox" data-sid="${s.id}" ${absent ? "checked" : ""} style="width:20px;height:20px;">
                    <span>${escapeHtml(s.name)}</span>
                    <span style="margin-left:auto;font-size:13px;color:#e03c3c;">kelmadi</span>
                </label>`;
            }).join("");
    } catch (e) {
        list.innerHTML = '<p class="note">Xatolik: ' + escapeHtml(e.message) + '</p>';
    }
}

async function saveTeacherAttendance() {
    const gid = document.getElementById("att-tgroup").value;
    const date = document.getElementById("att-tdate").value;
    const absentIds = Array.from(document.querySelectorAll("#att-tlist input[type=checkbox]"))
        .filter((c) => c.checked).map((c) => parseInt(c.dataset.sid, 10));
    const btn = document.getElementById("btn-att-save");
    btn.disabled = true;
    try {
        const res = await api("/attendance", "POST", { date, group_id: parseInt(gid, 10), absent_student_ids: absentIds });
        toast(`✅ Saqlandi: ${res.marked} ta kelmadi`);
        await loadTeacherGroup();
    } catch (e) {
        toast(e.message || "Saqlanmadi");
    } finally {
        btn.disabled = false;
    }
}

// ==================== TO'LOV ESLATMALARI (admin) ====================

async function loadPayments() {
    try {
        let students = [];
        try { students = await api("/students"); } catch (e) {}
        const sel = document.getElementById("pay-student");
        sel.innerHTML = students.length
            ? students.map((s) => `<option value="${s.id}">${escapeHtml(s.full_name)}${s.group_name ? " (" + escapeHtml(s.group_name) + ")" : ""}</option>`).join("")
            : '<option value="">O\'quvchi yo\'q — avval hisob oching</option>';

        const list = await api("/payments");
        const box = document.getElementById("pay-list");
        box.innerHTML = "";
        if (!list.length) { box.innerHTML = '<p class="note">Hozircha to\'lov eslatmasi yo\'q</p>'; return; }
        const today = todayISO();
        for (const p of list) {
            box.appendChild(payRow(p, today, true));
        }
        enchant(box);
    } catch (e) {}
}

function payBadge(p, today) {
    if (p.status === "paid") return '<span class="badge">✅ To\'landi</span>';
    if (p.due_date && p.due_date < today) return '<span class="badge off">⚠️ Muddati o\'tdi</span>';
    return '<span class="badge">Kutilmoqda</span>';
}

function payRow(p, today, withActions) {
    const div = document.createElement("div");
    div.className = "row";
    div.innerHTML = `
        <div class="row-head">💳 ${escapeHtml(p.student_name || "")} ${p.group_name ? "(" + escapeHtml(p.group_name) + ")" : ""} ${payBadge(p, today)}</div>
        <div class="row-sub">${escapeHtml(p.note || "To'lov")} • <b>${escapeHtml(p.amount)}</b>${p.due_date ? " • Muddat: " + escapeHtml(p.due_date) : ""}</div>
    `;
    if (withActions && p.status === "pending") {
        const payBtn = document.createElement("button");
        payBtn.className = "btn-mini";
        payBtn.textContent = "✅ To'lov qabul qilindi";
        payBtn.onclick = async () => {
            try {
                const r = await api(`/payments/${p.id}/pay`, "POST");
                toast(r.queued ? "To'lov belgilandi — xabar ketdi" : "To'lov belgilandi");
                loadPayments();
            } catch (e) { toast(e.message); }
        };
        div.appendChild(payBtn);

        const remBtn = document.createElement("button");
        remBtn.className = "btn-mini";
        remBtn.textContent = "🔁 Qayta eslatma";
        remBtn.onclick = async () => {
            try {
                const r = await api(`/payments/${p.id}/remind`, "POST");
                toast("Eslatma yuborildi: " + (r.queued || 0) + " ta chatga");
            } catch (e) { toast(e.message); }
        };
        div.appendChild(remBtn);
    }
    if (withActions) {
        const delBtn = document.createElement("button");
        delBtn.className = "btn-mini";
        delBtn.textContent = "🗑 O'chirish";
        delBtn.onclick = async () => {
            if (!window.confirm("Bu eslatma o'chirilsinmi?")) return;
            try { await api(`/payments/${p.id}`, "DELETE"); toast("O'chirildi"); loadPayments(); }
            catch (e) { toast(e.message); }
        };
        div.appendChild(delBtn);
    }
    return div;
}

document.getElementById("btn-pay-create").onclick = async () => {
    const studentId = document.getElementById("pay-student").value;
    const note = document.getElementById("pay-note").value.trim();
    const amount = document.getElementById("pay-amount").value.trim();
    const due = document.getElementById("pay-due").value;
    const notify = document.getElementById("pay-notify").checked;
    if (!studentId) { toast("O'quvchini tanlang"); return; }
    if (!note) { toast("Izoh yozing — nima uchun to'lov?"); return; }
    if (!amount) { toast("Summani kiriting"); return; }
    try {
        const r = await api("/payments", "POST", {
            student_id: Number(studentId),
            amount, note,
            due_date: due || null,
            notify,
        });
        toast(r.queued ? `Eslatma yaratildi — ${r.queued} ta chatga xabar ketdi` : "Eslatma yaratildi");
        document.getElementById("pay-note").value = "";
        document.getElementById("pay-amount").value = "";
        document.getElementById("pay-due").value = "";
        loadPayments();
    } catch (e) { toast(e.message); }
};

// To'lovlar (o'quvchi / ota-ona)
async function loadMyPayments() {
    try {
        const list = await api("/payments/mine");
        const box = document.getElementById("my-pay-list");
        box.innerHTML = "";
        if (!list.length) { box.innerHTML = '<p class="note">Hozircha to\'lov eslatmasi yo\'q</p>'; return; }
        const today = todayISO();
        for (const p of list) {
            box.appendChild(payRow(p, today, false));
        }
        enchant(box);
    } catch (e) {}
}

// ==================== PROFIL ====================

function renderProfile() {
    const role = currentUser ? currentUser.role : null;
    const studBox = document.getElementById("profile-student");
    const menuBox = document.getElementById("profile-menu");
    ["profile-student", "profile-menu"].forEach((id) => document.getElementById(id).classList.add("hidden"));
    document.getElementById("profile-title").textContent = currentUser ? ROLE_LABELS[role] || "Profil" : "Mehmon";
    if (!currentUser) { return; }

    if (role === "student") {
        studBox.classList.remove("hidden");
        loadStudentProfile();
        return;
    }

    menuBox.classList.remove("hidden");
    const mgmt = document.getElementById("profile-mgmt");
    let items = [];
    const sub = document.getElementById("profile-sub");
    if (role === "teacher") {
        sub.textContent = "Post va story joylash panelingiz";
        items = [
            ["📝 Post / story joylash", () => { go("create", null); }],
            ["📅 Dars jadvalini ko'rish", () => { go("schedule", null); }],
            ["🍽 Oshxona menyusi", () => { go("canteen", null); }],
        ];
    } else if (role === "canteen") {
        sub.textContent = "Oshxona menyusi siz tomoningizdan boshqariladi";
        items = [
            ["🍽 Menyuni boshqarish", () => { go("canteen", null); }],
            ["📅 Dars jadvalini ko'rish", () => { go("schedule", null); }],
        ];
    } else if (role === "admin" || role === "super") {
        sub.textContent = role === "super"
            ? "Asosiy admin — ilova nomi, admin ochish va boshqaruv"
            : "Admin panel — guruhlar, ustozlar, o'quvchilar, jadval";
        items = [
            ["📢 E'lon yuborish", () => { openAnnTab(); }],
            ["🎓 Hisob ochish (ustoz/o'quvchi/oshxona)", () => { go("create", null); }],
            ["🏫 Guruhlar va O'quvchilar boshqaruvi", () => { show("admin"); loadAdminData(); }],
            ["📅 Dars jadvalini tahrirlash", () => { go("schedule", null); }],
            ["🍽 Oshxona menyusi", () => { go("canteen", null); }],
        ];
        if (role === "super") {
            items.push(["👑 Asosiy admin: ilova nomi, adminlar ro'yxati", () => { show("sadmin"); loadSadminScreen(); }]);
        }
    }
    mgmt.innerHTML = items.map((it) => `<button data-mi="1">${escapeHtml(it[0])}</button>`).join("");
    Array.from(mgmt.querySelectorAll("button")).forEach((b, i) => { b.onclick = items[i][1]; });
    enchant(mgmt);
}

// ==================== O'QUVCHI PROFILI + KARTOCHKA ====================

async function loadStudentProfile() {
    try {
        const data = await api("/students/me");
        currentStudent = data;
        document.getElementById("profile-name").textContent = data.full_name;
        document.getElementById("profile-group").textContent = data.group_name || "-";
        document.getElementById("profile-teacher").textContent = data.teacher_name || data.repetitor_fullname || "-";
        const infoRow = document.getElementById("profile-info-row");
        if (data.info) {
            infoRow.classList.remove("hidden");
            document.getElementById("profile-info").textContent = data.info;
        } else infoRow.classList.add("hidden");

        studentPhotoUrl = "";
        const img = document.getElementById("profile-photo");
        if (data.has_photo) {
            const resp = await fetch(`${API}/students/${data.id}/photo`, { headers: { "Authorization": "Bearer " + token } });
            if (resp.ok) { studentPhotoUrl = URL.createObjectURL(await resp.blob()); img.src = studentPhotoUrl; }
            else img.src = PHOTO_PLACEHOLDER;
        } else img.src = PHOTO_PLACEHOLDER;
    } catch (e) { toast(e.message); }
}

document.getElementById("btn-card").onclick = () => {
    if (!currentStudent) return;
    const s = currentStudent;
    document.getElementById("card-name").textContent = s.full_name;
    document.getElementById("card-number").textContent = "MK-" + String(s.id).padStart(4, "0");
    document.getElementById("card-group").textContent = s.group_name || "-";
    document.getElementById("card-teacher").textContent = s.teacher_name || s.repetitor_fullname || "-";
    document.getElementById("card-subject").textContent = s.repetitor_subject || "-";
    document.getElementById("card-date").textContent = fmtDate(s.repetitor_start_date);
    document.getElementById("card-photo").src = studentPhotoUrl || PHOTO_PLACEHOLDER;
    show("card");
};

document.getElementById("btn-back-card").onclick = () => { show("profile"); renderProfile(); };

// ==================== ADMIN BOSHQARUV ====================

// Admin bo'limlari: tab tugmasi va bo'lim (panel) bir xil "active" klassi bilan boshqariladi
function showAdminTab(id) {
    document.querySelectorAll(".admin-tabs .tab").forEach((t) =>
        t.classList.toggle("active", t.dataset.tab === id)
    );
    document.querySelectorAll(".admin-tab").forEach((p) =>
        p.classList.toggle("active", p.id === id)
    );
}

document.querySelectorAll(".admin-tabs .tab").forEach((tab) => {
    tab.onclick = () => showAdminTab(tab.dataset.tab);
});

async function loadAdminData() {
    try {
        await ensureCreateCaches();
        loadStats();

        try {
            const st = await api("/settings/school");
            document.getElementById("school-name-input").value = st.school_name || "";
            applySettingsNames(appName, st.school_name);
        } catch (e) {}

        const leaderSel = document.getElementById("group-leader");
        leaderSel.innerHTML = '<option value="">Guruh rahbari (ixtiyoriy)</option>' +
            teachersCache.map((t) => `<option value="${t.id}">${escapeHtml(t.full_name)}${t.subject ? " (" + escapeHtml(t.subject) + ")" : ""}</option>`).join("");

        const groups = await api("/groups");
        const glist = document.getElementById("groups-list");
        glist.innerHTML = groups.length ? "" : '<p class="note">Guruh yo\'q</p>';
        for (const g of groups) {
            glist.innerHTML += `<div class="row"><div class="row-head">${escapeHtml(g.name)}</div>
            <div class="row-sub">${g.leader_teacher_name ? "Rahbar: " + escapeHtml(g.leader_teacher_name) : "Rahbar tayinlanmagan"}</div></div>`;
        }

        // O'qituvchilar ro'yxati
        const tlist = document.getElementById("teachers-list");
        tlist.innerHTML = teachersCache.length ? "" : '<p class="note">Ustoz yo\'q — Yangi ➕ bo\'limidan oching.</p>';
        for (const t of teachersCache) {
            tlist.innerHTML += `<div class="row"><div class="row-head">${escapeHtml(t.full_name)}</div>
            <div class="row-sub">${escapeHtml(t.subject || "Fan ko'rsatilmagan")}</div></div>`;
        }

        await loadStudentsList();
        loadCodes();
        loadAccounts();
        loadAnnouncements();
        loadAttendance();
        loadPayments();
        enchant(screens.admin);
    } catch (e) { toast(e.message); }
}

// ==================== OTA-ONA ULASH KODLARI ====================

async function loadCodes() {
    try {
        const list = await api("/link-codes");
        const box = document.getElementById("codes-list");
        box.innerHTML = "";
        const active = list.filter((c) => !c.used_by);
        if (!active.length) {
            box.innerHTML = '<p class="note">Faol kod yo\'q — o\'quvchi qatoridagi 🔗 tugma bilan yarating</p>';
            return;
        }
        for (const c of active) {
            const div = document.createElement("div");
            div.className = "row";
            div.innerHTML = `<div class="row-head">👨‍👦 ${escapeHtml(c.student_name)} <span class="badge">${escapeHtml(c.group_name || "-")}</span></div>
                <div class="row-sub">Kod: <b>${escapeHtml(c.code)}</b> — ota-ona botga «kod ${escapeHtml(c.code)}» deb yozadi</div>`;
            const del = document.createElement("button");
            del.className = "btn-mini";
            del.textContent = "🗑 Bekor qilish";
            del.onclick = async () => {
                try { await api("/link-codes/" + c.id, "DELETE"); loadCodes(); } catch (e) { toast(e.message); }
            };
            div.appendChild(del);
            box.appendChild(div);
        }
        enchant(box);
    } catch (e) {}
}

async function loadStudentsList() {
    const students = await api("/students");    const el = document.getElementById("students-list");
    el.innerHTML = "";
    if (!students.length) { el.innerHTML = '<p class="note">O\'quvchi yo\'q — ➕ bo\'limidan hisob oching.</p>'; return; }
    for (const s of students) {
        const div = document.createElement("div");
        div.className = "row";
        div.innerHTML = `<div class="row-head">${escapeHtml(s.full_name)}
            ${s.has_photo ? '<span class="badge">✅ rasm bor</span>' : '<span class="badge off">❌ rasm yo\'q</span>'}
            ${s.has_parent ? '<span class="badge">👨‍👦 ota-ona ulangan</span>' : ''}</div>
        <div class="row-sub">Login: ${escapeHtml(s.login)} • Guruh: ${escapeHtml(s.group_name || "-")}<br>
        Repetitor: ${escapeHtml(s.teacher_name || s.repetitor_fullname || "-")}${s.repetitor_subject ? " • " + escapeHtml(s.repetitor_subject) : ""}${s.repetitor_start_date ? " • " + escapeHtml(fmtDate(s.repetitor_start_date)) : ""}</div>`;
        if (!s.has_parent) {
            const linkBtn = document.createElement("button");
            linkBtn.className = "btn-mini";
            linkBtn.textContent = "🔗 Ota-ona kodi yaratish";
            linkBtn.onclick = async () => {
                try {
                    const res = await api("/link-codes", "POST", { student_id: s.id });
                    toast("Kod: " + res.code + " — ota-onaga bering");
                    loadCodes();
                } catch (e) { toast(e.message); }
            };
            div.appendChild(linkBtn);
        } else {
            const unBtn = document.createElement("button");
            unBtn.className = "btn-mini";
            unBtn.textContent = "⛔ Ulashni bekor qilish";
            unBtn.onclick = async () => {
                try {
                    await api(`/students/${s.id}/parent`, "DELETE");
                    toast("Ulash bekor qilindi");
                    loadStudentsList();
                    loadCodes();
                } catch (e) { toast(e.message); }
            };
            div.appendChild(unBtn);
        }
        const file = document.createElement("input");
        file.type = "file";
        file.accept = "image/*";
        file.className = "rowm";
        file.onchange = async () => {
            if (!file.files.length) return;
            const fd = new FormData();
            fd.append("file", file.files[0]);
            const resp = await fetch(`${API}/students/${s.id}/photo`, {
                method: "POST",
                headers: { "Authorization": "Bearer " + token },
                body: fd,
            });
            const data = await resp.json().catch(() => ({}));
            if (resp.ok) { toast("3x4 rasm yuklandi ✔"); loadStudentsList(); }
            else toast(data.detail || "Xato");
        };
        div.appendChild(file);
        el.appendChild(div);
    }
}

// ==================== STATISTIKA / ZAXIRA / HISOBLAR ====================

const STAT_CARDS = [
    ["students", "🎒", "O'quvchi"],
    ["teachers", "👩‍🏫", "Ustoz"],
    ["groups", "🏫", "Guruh"],
    ["posts", "📝", "Post"],
    ["likes", "❤️", "Layk"],
    ["comments", "💬", "Izoh"],
    ["lessons", "📅", "Dars"],
    ["menu_items", "🍽", "Taom"],
];

async function loadStats() {
    try {
        const s = await api("/stats");
        const grid = document.getElementById("stats-grid");
        grid.innerHTML = STAT_CARDS.map(([key, icon, label]) =>
            `<div class="stat-card glass"><div class="st-ic">${icon}</div><div class="st-num">${s[key] != null ? s[key] : 0}</div><div class="st-lb">${label}</div></div>`
        ).join("");
        const info = [];
        if (s.last_menu_at) info.push("🍽 menyu: " + String(s.last_menu_at).slice(0, 10));
        if (s.last_post_at) info.push("📝 oxirgi post: " + String(s.last_post_at).slice(0, 10));
        let infoHtml = info.length ? `<p class="note" style="margin-top:8px">${info.join(" • ")}</p>` : "";
        grid.innerHTML += infoHtml;
        enchant(grid);
    } catch (e) { /* statistika muhim emas */ }
}

document.getElementById("btn-backup").onclick = () => {
    try {
        toast("💾 Zaxira fayli yuklanmoqda...");
        fetch(API + "/backup", { headers: { "Authorization": "Bearer " + token } })
            .then(async (resp) => {
                if (!resp.ok) throw new Error("Zaxira yuklab bo'lmadi (" + resp.status + ")");
                const blob = await resp.blob();
                const a = document.createElement("a");
                a.href = URL.createObjectURL(blob);
                a.download = "school-backup.zip";
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(a.href);
            })
            .catch((e) => toast(e.message));
    } catch (e) { toast(e.message); }
};

function appConfirm(msg, cb) {
    if (tg && tg.showConfirm) { tg.showConfirm(msg, (ok) => cb(!!ok)); }
    else { cb(window.confirm(msg)); }
}

document.getElementById("btn-restore").onclick = async () => {
    const fileInput = document.getElementById("restore-file");
    if (!currentUser || currentUser.role !== "super") { toast("Tiklash faqat asosiy admin huquqi"); return; }
    if (!fileInput.files.length) { toast("Avval .zip zaxira faylini tanlang"); return; }
    const f = fileInput.files[0];
    appConfirm("Hozirgi barcha ma'lumotlar zaxiradagi holatga almashtiriladi. Davom etamizmi?", async (ok) => {
        if (!ok) return;
        try {
            toast("⚡ Zaxira tiklanmoqda...");
            const fd = new FormData();
            fd.append("file", f);
            const resp = await fetch(API + "/restore", {
                method: "POST",
                headers: { "Authorization": "Bearer " + token },
                body: fd,
            });
            const data = await resp.json().catch(() => ({}));
            if (resp.ok) {
                toast("✅ Zaxira to'liq tiklandi!");
                setTimeout(() => location.reload(), 1400);
            } else {
                toast(data.detail || "Tiklashda xato");
            }
        } catch (e) { toast("Tiklashda xato: " + e.message); }
    });
};

let pwEditUserId = null;
let accountsCache = [];

async function loadAccounts() {
    try {
        accountsCache = await api("/accounts");
        renderAccounts();
    } catch (e) { /* tab ochilmaganda ham */ }
}

function renderAccounts() {
    const el = document.getElementById("accounts-list");
    const isSuper = currentUser && currentUser.role === "super";
    const MY_ID = currentUser ? currentUser.id : -1;
    const ROLE_IC = { super: "👑", admin: "🏛", teacher: "👩‍🏫", student: "🎒", canteen: "🍽" };
    el.innerHTML = "";
    if (!accountsCache.length) { el.innerHTML = '<p class="note">Hisob yo\'q</p>'; return; }
    for (const a of accountsCache) {
        const controllable = isSuper || a.role === "teacher" || a.role === "student" || a.role === "canteen";
        const self = a.user_id === MY_ID;
        const badge = a.role === "super" ? '<span class="badge">👑</span>' : (a.role === "admin" ? '<span class="badge">🏛</span>' : "");
        const statusBadge = a.is_active ? "" : '<span class="badge off">🔒 bloklangan</span>';
        if (pwEditUserId === a.user_id) {
            el.innerHTML += `
            <div class="row">
                <div class="row-head">${ROLE_IC[a.role] || ""} ${escapeHtml(a.full_name || a.login)}${badge}</div>
                <div class="row-sub">Yangi parol (kamida 4 belgi)</div>
                <div class="newsline" style="display:flex;gap:8px;margin-top:8px;">
                    <input type="password" id="pw-new-${a.user_id}" class="pw-input" style="flex:1;" placeholder="Yangi parol">
                    <button class="btn-mini save" data-save="${a.user_id}">✔</button>
                    <button class="btn-mini canc" data-cancel="1">✖</button>
                </div>
            </div>`;
            continue;
        }
        let buttons = "";
        if (controllable) {
            buttons = `
                <button class="btn-mini" data-pw="${a.user_id}">🔑 Parol</button>
                <button class="btn-mini ${a.is_active ? "danger" : "ok"}" data-active="${a.user_id}" data-val="${a.is_active ? 0 : 1}">
                    ${a.is_active ? "⏻ Bloklash" : "▶️ Faollashtirish"}
                </button>`;
        }
        el.innerHTML += `
        <div class="row">
            <div class="row-head">${ROLE_IC[a.role] || "👤"} ${escapeHtml(a.full_name || a.login)}${badge}
                ${self ? '<span class="badge">siz</span>' : ""}${statusBadge}</div>
            <div class="row-sub">Login: ${escapeHtml(a.login)} • ${ROLE_LABELS[a.role] || a.role}</div>
            <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;">${buttons}</div>
        </div>`;
    }

    el.querySelectorAll("[data-pw]").forEach((b) => {
        b.onclick = () => { pwEditUserId = parseInt(b.dataset.pw); renderAccounts(); const inp = document.getElementById("pw-new-" + pwEditUserId); if (inp) inp.focus(); };
    });
    el.querySelectorAll(".btn-mini.save").forEach((b) => {
        b.onclick = async () => {
            const uid = parseInt(b.dataset.save);
            const val = document.getElementById("pw-new-" + uid).value;
            if (!val || val.length < 4) { toast("Parol kamida 4 belgidan iborat bo'lsin"); return; }
            try {
                await api("/users/" + uid + "/password", "POST", { password: val });
                toast("🔑 Parol yangilandi ✔");
                pwEditUserId = null;
                loadAccounts();
            } catch (e) { toast(e.message); }
        };
    });
    el.querySelectorAll(".btn-mini.canc").forEach((b) => {
        b.onclick = () => { pwEditUserId = null; renderAccounts(); };
    });
    el.querySelectorAll("[data-active]").forEach((b) => {
        b.onclick = async () => {
            const uid = parseInt(b.dataset.active);
            const active = b.dataset.val === "1";
            try {
                await api("/users/" + uid + "/active", "POST", { active });
                toast(active ? "▶️ Hisob faollashtirildi" : "⏻ Hisob bloklandi");
                accountsCache = [];
                loadAccounts();
            } catch (e) { toast(e.message); }
        };
    });
    enchant(el);
}

document.getElementById("btn-save-school").onclick = async () => {
    const name = document.getElementById("school-name-input").value.trim();
    if (!name) { toast("Maktab nomini kiriting"); return; }
    try {
        await api("/settings/school", "POST", { school_name: name });
        applySettingsNames(appName, name);
        toast("Maktab nomi saqlandi ✔");
    } catch (e) { toast(e.message); }
};

document.getElementById("btn-add-group").onclick = async () => {
    const name = document.getElementById("group-name").value.trim();
    const leader = document.getElementById("group-leader").value;
    if (!name) { toast("Guruh nomini kiriting"); return; }
    try {
        await api("/groups", "POST", { name, leader_teacher_id: leader ? parseInt(leader) : null });
        document.getElementById("group-name").value = "";
        toast("Guruh qo'shildi ✔");
        groupsCache = [];
        loadAdminData();
        schedGroupId = null;
    } catch (e) { toast(e.message); }
};

// ==================== ASOSIY ADMIN (SADMIN) ====================

document.getElementById("btn-save-brand").onclick = async () => {
    const val = document.getElementById("brand-input").value.trim();
    if (!val) { toast("Ilova nomi bo'sh bo'lmasin"); return; }
    try {
        const res = await api("/settings/app", "POST", { app_name: val });
        appName = res.app_name;
        renderBrand(appName);
        toast("Ilova nomi o'zgartirildi: " + appName + " ✔");
        loadSadminScreen();
    } catch (e) { toast(e.message); }
};

document.getElementById("btn-sa-create").onclick = async () => {
    const full_name = document.getElementById("sa-name").value.trim();
    const login = document.getElementById("sa-login").value.trim();
    const password = document.getElementById("sa-password").value;
    if (!full_name || !login || !password) { toast("F.I.Sh., login va parolni kiriting"); return; }
    try {
        await api("/users", "POST", { role: "admin", full_name, login, password });
        toast("Admin hisobi ochildi ✔");
        ["sa-name", "sa-login", "sa-password"].forEach((id) => (document.getElementById(id).value = ""));
        loadSadminScreen();
    } catch (e) { toast(e.message); }
};

async function loadSadminScreen() {
    document.getElementById("brand-input").value = appName;
    await loadSadminUsers();
}

async function loadSadminUsers() {
    try {
        const box = document.getElementById("sadmin-users");
        box.innerHTML = '<div class="row"><div class="row-head">Adminlar va oshxona xodimlari</div></div>';
        for (const role of ["admin", "canteen"]) {
            const users = await api("/users?role=" + role);
            users.forEach((u) => {
                box.innerHTML += `<div class="row"><div class="row-head">${role === "admin" ? "🏛" : "🍽"} ${escapeHtml(u.full_name || u.login)}</div>
                <div class="row-sub">${escapeHtml(u.login)} • ${ROLE_LABELS[role] || role}${u.position ? " • " + escapeHtml(u.position) : ""}</div></div>`;
            });
        }
        enchant(box);
    } catch (e) { /* ixtiyoriy */ }
}

// ==================== SEGMENTED CONTROLLER ====================

document.querySelectorAll(".seg").forEach((seg) => {
    const viewPrefix = seg.id === "seg-schedule" ? ["sched-today", "sched-week"] : ["canteen-today", "canteen-week"];
    seg.querySelectorAll("button").forEach((btn) => {
        btn.onclick = () => {
            seg.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            const todayShow = btn.dataset.view === "today";
            document.getElementById(viewPrefix[0]).classList.toggle("hidden", !todayShow);
            document.getElementById(viewPrefix[1]).classList.toggle("hidden", todayShow);
        };
    });
});

// ==================== BOSHLASH ====================

(async function init() {
    await loadPublicNames();
    if (token) {
        try {
            const res = await api("/me");
            applySettingsNames(res.app_name, res.school_name);
            await bootUser({ id: res.user.id, login: res.user.login, role: res.user.role });
            tryAutoLink();
            return;
        } catch (e) {
            token = "";
            localStorage.removeItem("school_token");
        }
    }
    if (urlParams.get("guest") === "1") { enterGuest(); return; }
    show("login");
})();
