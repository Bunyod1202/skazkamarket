// Telegram WebApp storefront script (clean version)
(function(){
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) tg.expand();
  // Ensure all alert modals include tid for debugging
  if (typeof getQueryTid !== 'function'){
    window.getQueryTid = function(){
      try{
        const q = new URLSearchParams(location.search);
        const tid = q.get('tid');
        return tid && /^\d+$/.test(tid) ? tid : null;
      }catch(e){ return null; }
    }
  }
  if (tg && typeof tg.showAlert === 'function' && !tg.__wrappedShowAlert){
    const __orig = tg.showAlert.bind(tg);
    tg.showAlert = function(message){
      const tid = (typeof getQueryTid === 'function') ? (getQueryTid() || '') : '';
      const finalMsg = tid ? String(message || '') + "\nTID: " + tid : String(message || '');
      return __orig(finalMsg);
    };
    tg.__wrappedShowAlert = true;
  }

  const $categories = document.getElementById('categories');
  const $products = document.getElementById('products');
  const $total = document.getElementById('total');
  const $checkout = document.getElementById('checkout');
  const $comment = document.getElementById('comment');
  const $address = document.getElementById('address');
  const $whatsapp = document.getElementById('whatsapp');
  const $email = document.getElementById('email');

  const cart = new Map(); // productId -> { product, qty }
  let language = 'UZ';
  let allProducts = [];
  let allCategories = [];
  let selectedCategory = 'all';

  function detectLanguage(){
    if (!tg || !tg.initDataUnsafe || !tg.initDataUnsafe.user) return 'UZ';
    const code = (tg.initDataUnsafe.user.language_code || 'uz').toLowerCase();
    if (code.startsWith('ru')) return 'RU';
    if (code.startsWith('en')) return 'EN';
    if (code.startsWith('uz')) return 'UZ';
    return 'EN';
  }
  function t(uz, ru, en){ return language==='RU' ? ru : (language==='EN' ? en : uz); }
  function fmt(v){ return Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 }); }

  function updateTotal(){
    let sum = 0;
    for (const [, {product, qty}] of cart) sum += Number(product.price) * qty;
    if ($total) $total.textContent = fmt(sum) + ' UZS';
    if ($checkout) $checkout.disabled = sum <= 0;
  }

  function renderCategories(){
    if (!$categories) return;
    $categories.innerHTML = '';
    const make = (id, name, count) => {
      const el = document.createElement('div');
      el.className = 'cat' + (selectedCategory===id ? ' active' : '');
      el.dataset.id = id;
      const cat = allCategories.find(c => String(c.id)===String(id));
      const thumb = (cat && cat.image) ? cat.image : 'https://via.placeholder.com/56x56?text=%20';
      el.innerHTML = `<img class="thumb" src="${thumb}" alt=""><div class="name">${name}</div><div class="count">${count}</div>`;
      el.addEventListener('click', () => { selectedCategory = id; renderCategories(); renderProducts(); });
      return el;
    };
    $categories.appendChild(make('all', t('Barchasi','Все','All'), allProducts.length));
    allCategories.forEach(c => {
      const name = language==='RU' ? c.name_ru : (language==='EN' ? (c.name_en || c.name_uz) : c.name_uz);
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
        <img src="${p.image || 'https://via.placeholder.com/300x200?text=No+Image'}" alt="">
        <div class="content">
          <div class="name">${language==='RU'?p.name_ru:(language==='EN'?(p.name_en||p.name_uz):p.name_uz)}</div>
          <div class="price">${fmt(p.price)} UZS</div>
          <div class="qty">
            <button class="dec">-</button>
            <input type="text" class="q" value="${cart.get(p.id)?.qty || 0}" readonly />
            <button class="inc">+</button>
          </div>
        </div>`;
      const q = card.querySelector('.q');
      const inc = card.querySelector('.inc');
      const dec = card.querySelector('.dec');
      function setQty(n){ n=Math.max(0,n); q.value=n; if(n===0) cart.delete(p.id); else cart.set(p.id,{product:p,qty:n}); updateTotal(); }
      inc.addEventListener('click', ()=>setQty((parseInt(q.value)||0)+1));
      dec.addEventListener('click', ()=>setQty((parseInt(q.value)||0)-1));
      $products.appendChild(card);
    });
  }

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
    }catch(e){ console.error('Failed to load data', e); }
  }

  async function upsertUser(){
    try{
      const user = tg && tg.initDataUnsafe ? tg.initDataUnsafe.user : null;
      if (!user) return;
      await fetch('/api/user', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          telegram_id: String(user.id),
          language,
          full_name: user.first_name + (user.last_name?(' '+user.last_name):''),
          username: user.username || ''
        })
      });
    }catch(e){ /* ignore */ }
  }

  function parseUserFromInitData(){
    try{
      if (!tg || !tg.initData) return null;
      const params = new URLSearchParams(tg.initData);
      const raw = params.get('user');
      if (!raw) return null;
      return JSON.parse(decodeURIComponent(raw));
    }catch(e){ return null; }
  }

  async function getTelegramUserWithRetry(){
    // Try immediate, then retry briefly to allow Telegram to populate initDataUnsafe
    let u = (tg && tg.initDataUnsafe) ? tg.initDataUnsafe.user : null;
    if (u && u.id) return u;
    // Try parsing initData string as fallback
    u = parseUserFromInitData();
    if (u && u.id) return u;
    await new Promise(r => setTimeout(r, 200));
    u = (tg && tg.initDataUnsafe) ? tg.initDataUnsafe.user : null;
    if (u && u.id) return u;
    // Final fallback: use tid passed from bot
    const tid = (typeof getQueryTid === 'function') ? getQueryTid() : null;
    if (tid) return { id: Number(tid) };
    return parseUserFromInitData();
  }

  async function submitOrder(){
    const items = Array.from(cart.values()).map(({product, qty})=>({product_id:product.id, quantity:qty}));
    if (!items.length) return;
    const user = await getTelegramUserWithRetry();
    if (!user || !user.id){
      if (tg) tg.showAlert(t('Iltimos, meni botdagi tugma orqali oching','Откройте через кнопку в боте','Please open via the bot button'));
      return;
    }
    const payload = {
      telegram_id: user ? String(user.id) : '',
      language,
      phone: '',
      full_name: user ? (user.first_name + (user.last_name?(' '+user.last_name):'')) : '',
      username: user && user.username ? user.username : '',
      comment: ($comment?.value || ''),
      address: ($address?.value || ''),
      whatsapp: ($whatsapp?.value || ''),
      email: ($email?.value || ''),
      items
    };
    try{
      $checkout.disabled = true;
      const res = await fetch(`${window.API_BASE}/order`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      if (!res.ok){
        const txt = await res.text().catch(()=> '');
        if (tg) tg.showAlert((txt && txt.length < 200 ? txt : t('Xatolik. Qayta urinib ko‘ring.','Ошибка. Попробуйте снова.','Error. Please try again.')));
        return;
      }
      const data = await res.json().catch(()=>({status:'error'}));
      if (data.status==='ok'){
        if (tg) tg.showAlert(t('✅ Buyurtma qabul qilindi!','✅ Заказ принят!','✅ Order placed!'));
        if (tg) tg.close();
      } else {
        if (tg) tg.showAlert(t('Xatolik. Qayta urinib ko‘ring.','Ошибка. Попробуйте снова.','Error. Please try again.'));
      }
    }catch(e){
      console.error('Order failed', e);
      if (tg) tg.showAlert(t('Xatolik yuz berdi','Произошла ошибка','An error occurred'));
    }finally{ $checkout.disabled = false; }
  }

  function initTexts(){
    const title = document.getElementById('title');
    const totalLabel = document.getElementById('totalLabel');
    if (language==='RU'){
      if (title) title.textContent='Каталог';
      if (totalLabel) totalLabel.textContent='Итого:';
      if ($checkout) $checkout.textContent='Оформить заказ';
      if ($comment) $comment.placeholder='Комментарий';
      if ($address) $address.placeholder='Адрес';
    } else if (language==='EN'){
      if (title) title.textContent='Catalog';
      if (totalLabel) totalLabel.textContent='Total:';
      if ($checkout) $checkout.textContent='Checkout';
      if ($comment) $comment.placeholder='Comment';
      if ($address) $address.placeholder='Address';
    } else {
      if (title) title.textContent='Katalog';
      if (totalLabel) totalLabel.textContent='Jami:';
      if ($checkout) $checkout.textContent='Buyurtma berish';
      if ($comment) $comment.placeholder='Izoh';
      if ($address) $address.placeholder='Manzil';
    }
  }

  // boot
  (async function(){
    language = detectLanguage();
    initTexts();
    await upsertUser();
    await loadAll();
  })();

  if ($checkout) $checkout.addEventListener('click', submitOrder);
})();
