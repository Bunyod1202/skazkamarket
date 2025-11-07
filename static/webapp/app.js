// Telegram WebApp storefront script (repaired version)
(function(){
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) tg.expand();

  // Helpers ---------------------------------------------------------------
  function getQueryParam(name){
    try{ return new URLSearchParams(location.search).get(name) }catch(e){ return null }
  }
  function getQueryTid(){
    const v = getQueryParam('tid');
    return v && /^\d+$/.test(v) ? v : null;
  }
  function detectLanguage(){
    const q = (getQueryParam('lang')||'').toUpperCase();
    if (q==='UZ' || q==='RU' || q==='EN') return q;
    try{
      const lc = tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.language_code
        ? tg.initDataUnsafe.user.language_code
        : (navigator.language || navigator.userLanguage || 'en');
      const l = String(lc||'en').toLowerCase();
      if (l.startsWith('ru')) return 'RU';
      if (l.startsWith('uz')) return 'UZ';
      return 'EN';
    }catch(e){ return 'EN' }
  }
  function t(uz, ru, en){ return lang==='RU' ? ru : (lang==='EN' ? en : uz) }
  function fmt(v){ return Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 }) }
  function absMedia(u){
    try{
      if(!u) return '';
      // Already absolute
      if(/^https?:\/\//i.test(u)){
        const url = new URL(u, location.origin);
        if(location.protocol==='https:' && url.protocol==='http:' && url.host===location.host){
          return 'https://' + url.host + url.pathname + url.search;
        }
        return url.toString();
      }
      // Relative -> make absolute to current origin
      if(u[0] !== '/') u = '/' + u;
      return location.origin + u;
    }catch(e){ return u || '' }
  }
  function parseUserFromInitData(){
    try{
      if (!tg || !tg.initData) return null;
      const params = new URLSearchParams(tg.initData);
      const raw = params.get('user');
      if (!raw) return null;
      return JSON.parse(decodeURIComponent(raw));
    }catch(e){ return null }
  }
  async function getTelegramUserWithRetry(){
    let u = tg && tg.initDataUnsafe ? tg.initDataUnsafe.user : null;
    if (u && u.id) return u;
    u = parseUserFromInitData();
    if (u && u.id) return u;
    await new Promise(r => setTimeout(r, 200));
    u = tg && tg.initDataUnsafe ? tg.initDataUnsafe.user : null;
    if (u && u.id) return u;
    const tid = getQueryTid();
    return tid ? { id: Number(tid) } : null;
  }

  // Elements --------------------------------------------------------------
  const $categories = document.getElementById('categories');
  const $products = document.getElementById('products');
  const $total = document.getElementById('total');
  const $totalBarSum = document.getElementById('totalBarSum');
  const $totalBarLabel = document.getElementById('totalBarLabel');
  const $cartPanel = document.getElementById('cartPanel');
  const $cartBtn = document.getElementById('cartBtn');
  const $themeToggle = document.getElementById('themeToggle');
  const $checkout = document.getElementById('checkout');
  const $comment = document.getElementById('comment');
  const $address = document.getElementById('address');
  const $whatsapp = document.getElementById('whatsapp');
  const $email = document.getElementById('email');

  // State -----------------------------------------------------------------
  const cart = new Map(); // id -> {product, qty}
  let lang = detectLanguage();
  let allProducts = [];
  let allCategories = [];
  let selectedCategory = 'all';

  // UI texts --------------------------------------------------------------
  function initTexts(){
    const $title = document.getElementById('title');
    if (lang==='RU'){
      if ($title) $title.textContent='Каталог';
      if ($totalBarLabel) $totalBarLabel.textContent='Итого:';
      const lbl = document.getElementById('totalLabel'); if (lbl) lbl.textContent='Итого:';
      if ($checkout) $checkout.textContent='Оформить заказ';
      if ($comment) $comment.placeholder='Комментарий';
      if ($address) $address.placeholder='Адрес';
      if ($whatsapp) $whatsapp.placeholder='WhatsApp (опционально)';
      if ($email) $email.placeholder='Email (опционально)';
    } else if (lang==='EN'){
      if ($title) $title.textContent='Catalog';
      if ($totalBarLabel) $totalBarLabel.textContent='Total:';
      const lbl = document.getElementById('totalLabel'); if (lbl) lbl.textContent='Total:';
      if ($checkout) $checkout.textContent='Checkout';
      if ($comment) $comment.placeholder='Comment';
      if ($address) $address.placeholder='Address';
      if ($whatsapp) $whatsapp.placeholder='WhatsApp (optional)';
      if ($email) $email.placeholder='Email (optional)';
    } else {
      if ($title) $title.textContent='Katalog';
      if ($totalBarLabel) $totalBarLabel.textContent='Jami:';
      const lbl = document.getElementById('totalLabel'); if (lbl) lbl.textContent='Jami:';
      if ($checkout) $checkout.textContent='Buyurtma berish';
      if ($comment) $comment.placeholder='Izoh';
      if ($address) $address.placeholder='Manzil';
      if ($whatsapp) $whatsapp.placeholder='WhatsApp (ixtiyoriy)';
      if ($email) $email.placeholder='Email (ixtiyoriy)';
    }
  }

  function updateTotal(){
    let sum = 0, count = 0;
    for (const [, {product, qty}] of cart){ sum += Number(product.price) * qty; count += qty; }
    if ($total) $total.textContent = fmt(sum) + ' UZS';
    if ($totalBarSum) $totalBarSum.textContent = fmt(sum) + ' UZS';
    if ($checkout) $checkout.disabled = sum <= 0;
    if ($cartBtn){
      $cartBtn.textContent = t(`🛒 Savat (${count})`, `🛒 Корзина (${count})`, `🛒 Cart (${count})`);
      $cartBtn.disabled = count <= 0;
    }
  }

  // Rendering -------------------------------------------------------------
  function renderCategories(){
    if (!$categories) return;
    $categories.innerHTML = '';
    const make = (id, name, count) => {
      const el = document.createElement('div');
      el.className = 'cat' + (selectedCategory===id ? ' active' : '');
      el.dataset.id = id;
      const cat = allCategories.find(c => String(c.id)===String(id));
      const thumb = (id==='all')
        ? 'https://i.postimg.cc/4NXyxzcT/supplies.png'
        : absMedia((cat && cat.image) ? cat.image : 'https://via.placeholder.com/56x56?text=%20');
      el.innerHTML = `<img class="thumb" src="${thumb}" alt=""><div class="name">${name}</div><div class="count">${count}</div>`;
      const img = el.querySelector('img.thumb');
      if (img) img.addEventListener('error', () => { img.src = 'https://via.placeholder.com/56x56?text=%20'; });
      el.addEventListener('click', () => { selectedCategory = id; renderCategories(); renderProducts(); });
      return el;
    };
    $categories.appendChild(make('all', t('Barchasi','Все','All'), allProducts.length));
    allCategories.forEach(c => {
      const name = (lang==='RU') ? c.name_ru : (lang==='EN' ? (c.name_en || c.name_uz) : c.name_uz);
      $categories.appendChild(make(String(c.id), name, c.count));
    });
  }

  function renderProducts(){
    if (!$products) return;
    $products.innerHTML = '';
    const list = allProducts.filter(p => selectedCategory==='all' || String(p.category_id)===String(selectedCategory));
    list.forEach(p => {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `
        <img src="${absMedia(p.image) || 'https://via.placeholder.com/300x200?text=No+Image'}" alt="">
        <div class="content">
          <div class="name">${lang==='RU'?p.name_ru:(lang==='EN'?(p.name_en||p.name_uz):p.name_uz)}</div>
          <div class="price">${fmt(p.price)} UZS</div>
          <div class="qty">
            <button class="dec">-</button>
            <input type="text" class="q" value="${cart.get(p.id)?.qty || 0}" readonly />
            <button class="inc">+</button>
          </div>
        </div>`;
      const img = card.querySelector('img');
      if (img) img.addEventListener('error', () => { img.src = 'https://via.placeholder.com/300x200?text=No+Image'; });
      const q = card.querySelector('.q');
      const inc = card.querySelector('.inc');
      const dec = card.querySelector('.dec');
      function setQty(n){ n=Math.max(0,n); q.value=n; if(n===0) cart.delete(p.id); else cart.set(p.id,{product:p,qty:n}); updateTotal(); }
      inc.addEventListener('click', ()=>setQty((parseInt(q.value)||0)+1));
      dec.addEventListener('click', ()=>setQty((parseInt(q.value)||0)-1));
      $products.appendChild(card);
    });
  }

  // Data ------------------------------------------------------------------
  async function loadAll(){
    try{
      const [cr, pr] = await Promise.all([
        fetch(`${window.API_BASE}/categories`),
        fetch(`${window.API_BASE}/products`)
      ]);
      const cats = await cr.json();
      const prods = await pr.json();
      allCategories = cats.categories || [];
      allProducts = prods.products || [];
      renderCategories();
      renderProducts();
      updateTotal();
    }catch(e){ console.error('Failed to load data', e); }
  }

  async function upsertUser(){
    try{
      let user = tg && tg.initDataUnsafe ? tg.initDataUnsafe.user : null;
      if (!user || !user.id){ const parsed = parseUserFromInitData(); if (parsed && parsed.id) user = parsed; }
      if (!user || !user.id){ const tid = getQueryTid(); if (tid) user = { id: Number(tid) }; }
      if (!user || !user.id) return;
      const first = user.first_name || '';
      const last = user.last_name ? (' ' + user.last_name) : '';
      await fetch('/api/user', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          telegram_id: String(user.id),
          language: lang,
          full_name: (first + last).trim(),
          username: user.username || ''
        })
      });
    }catch(e){ /* ignore */ }
  }

  // Submit ----------------------------------------------------------------
  async function submitOrder(){
    const items = Array.from(cart.values()).map(({product, qty})=>({product_id:product.id, quantity:qty}));
    if (!items.length) return;
    const user = await getTelegramUserWithRetry();
    if (!user || !user.id){ if (tg) tg.showAlert(t('Iltimos, botdagi tugma orqali oching','Пожалуйста, откройте через кнопку бота','Please open via the bot button')); return; }
    const first = user.first_name || ''; const last = user.last_name ? (' ' + user.last_name) : '';    // Validate required address
    const addr = ($address?.value || '').trim();
    if (!addr){
      if (tg) tg.showAlert(t('Manzilni kiriting','Введите адрес','Please enter address'));
      if($cartPanel && !$cartPanel.classList.contains('open')){
        $cartPanel.classList.add('open');
        document.body.classList.add('cart-open');
      }
      try{ $address && $address.focus(); }catch(e){}
      return;
    }
    const payload = {
      telegram_id: String(user.id),
      language: lang,
      phone: '',
      full_name: (first + last).trim(),
      username: user.username || '',
      comment: ($comment?.value || ''),
      address: ($address?.value || ''),
      whatsapp: ($whatsapp?.value || ''),
      email: ($email?.value || ''),
      items
    };
    try{
      if ($checkout) $checkout.disabled = true;
      const res = await fetch(`${window.API_BASE}/order`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      if (!res.ok){ const txt = await res.text().catch(()=> ''); if (tg) tg.showAlert((txt && txt.length < 200 ? txt : t('Xatolik. Qayta urinib ko\'ring.','Ошибка. Пожалуйста, попробуйте ещё раз.','Error. Please try again.'))); return; }
      const data = await res.json().catch(()=>({status:'error'}));
      if (data.status==='ok'){ if (tg) tg.showAlert(t('Buyurtma qabul qilindi!','Заказ принят!','Order placed!')); if (tg) tg.close(); }
      else { if (tg) tg.showAlert(t('Xatolik. Qayta urinib ko\'ring.','Ошибка. Пожалуйста, попробуйте ещё раз.','Error. Please try again.')); }
    }catch(e){ console.error('Order failed', e); if (tg) tg.showAlert(t('Xatolik yuz berdi','Произошла ошибка','An error occurred')); }
    finally{ if ($checkout) $checkout.disabled = false; }
  }

  // Boot ------------------------------------------------------------------
  // Theme handling --------------------------------------------------------
  function detectTheme(){
    const saved = localStorage.getItem('theme');
    if (saved==='light' || saved==='dark') return saved;
    if (tg && tg.colorScheme) return tg.colorScheme === 'dark' ? 'dark' : 'light';
    try{ return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'; }catch(e){ return 'dark' }
  }
  function applyTheme(th){
    document.body.classList.remove('theme-light');
    if (th==='light') document.body.classList.add('theme-light');
    localStorage.setItem('theme', th);
    if ($themeToggle) $themeToggle.textContent = (th==='light' ? '🌙' : '☀️');
  }

  initTexts();
  applyTheme(detectTheme());
  upsertUser();
  loadAll();
  if ($cartBtn){
    $cartBtn.addEventListener('click', ()=>{ if($cartPanel){ $cartPanel.classList.toggle('open'); } });
    updateTotal();
  }
  if ($themeToggle){
    $themeToggle.addEventListener('click', ()=>{
      const cur = localStorage.getItem('theme') || (document.body.classList.contains('theme-light') ? 'light' : 'dark');
      applyTheme(cur==='light' ? 'dark' : 'light');
    });
  }
  if ($checkout) $checkout.addEventListener('click', submitOrder);
})();



