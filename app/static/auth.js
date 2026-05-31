// 공통 인증 유틸

function getToken() { return localStorage.getItem('jwt'); }
function getUser() {
  try { return JSON.parse(localStorage.getItem('user')); } catch { return null; }
}

function logout() {
  localStorage.removeItem('jwt');
  localStorage.removeItem('user');
  location.href = '/login';
}

// 헤더에 유저 아바타 삽입
function renderUserBadge(containerId) {
  const user = getUser();
  const el = document.getElementById(containerId);
  if (!el) return;
  if (user) {
    el.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;cursor:pointer" onclick="toggleUserMenu()">
        <img src="${user.picture}" style="width:28px;height:28px;border-radius:50%;border:1.5px solid #ddd" onerror="this.src=''">
        <span style="font-size:13px;color:#111;font-weight:600;max-width:80px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${user.name.split(' ')[0]}</span>
      </div>
      <div id="userMenu" style="display:none;position:absolute;top:52px;right:16px;background:#fff;border:1px solid #eee;border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,0.1);z-index:200;padding:8px 0;min-width:140px">
        <div style="padding:10px 16px;font-size:13px;color:#888;border-bottom:1px solid #f0f0f0">${user.email}</div>
        <div onclick="logout()" style="padding:10px 16px;font-size:13px;color:#e74c3c;cursor:pointer">로그아웃</div>
      </div>`;
  } else {
    el.innerHTML = `<a href="/login" style="font-size:13px;color:#1a73e8;font-weight:600;text-decoration:none">로그인</a>`;
  }
}

function toggleUserMenu() {
  const menu = document.getElementById('userMenu');
  if (menu) menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}

document.addEventListener('click', e => {
  const menu = document.getElementById('userMenu');
  if (menu && !e.target.closest('#authArea')) menu.style.display = 'none';
});

// 서버 북마크 동기화 (로그인 상태일 때) — 로컬 + 서버 합치기
async function syncBookmarks() {
  const token = getToken();
  if (!token) return;
  try {
    const res = await fetch('/api/auth/bookmarks', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const serverBookmarks = await res.json();
      const local = JSON.parse(localStorage.getItem('bookmarks') || '[]');
      const merged = [...new Set([...local, ...serverBookmarks])];
      localStorage.setItem('bookmarks', JSON.stringify(merged));
      if (merged.length !== serverBookmarks.length) {
        await pushBookmarks(merged);
      }
    }
  } catch {}
}

async function pushBookmarks(bookmarks) {
  const token = getToken();
  if (!token) return;
  try {
    await fetch('/api/auth/bookmarks', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ bookmarks }),
    });
  } catch {}
}
