(function(){
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) tg.expand();

  const $categories = document.getElementById('categories');
  const $products = document.getElementById('products');
  const $total = document.getElementById('total');
  const $checkout = document.getElementById('checkout');
  const $comment = document.getElementById('comment');

  const cart = new Map(); // productId -> {product, qty}
  let language = 'UZ';
  let allProducts = [];
  let allCategories = [];
  let selectedCategory = 'all';

  function detectLanguage(){
    if (!tg || !tg.initDataUnsafe || !tg.initDataUnsafe.user) return 'UZ';
    const code = (tg.initDataUnsafe.user.language_code || 'uz').toLowerCase();
    if (code.startsWith('ru')) return 'RU';
    if (code.startsWith('uz')) return 'UZ';
    return 'UZ';
  }

  function formatPrice(v){
    return Number(v).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  }

  function updateTotal(){
    let sum = 0;
    for (const [, {product, qty}] of cart){
      sum += Number(product.price) * qty;
    }
    $total.textContent = formatPrice(sum) + ' UZS';
    $checkout.disabled = sum <= 0;
  }

  function renderCategories(){
    if (!$categories) return;
    $categories.innerHTML = '';
    const makeCat = (id, name, count) => {
      const item = document.createElement('div');
      item.className = 'cat' + (selectedCategory === id ? ' active' : '');
      item.dataset.id = id;
      item.innerHTML = `<div class="name">${name}</div><div class="count">${count}</div>`;
      item.addEventListener('click', () => {
        selectedCategory = id;
        renderCategories();
        renderProducts();
      });
      return item;
    };
    const totalCount = allProducts.length;
    $categories.appendChild(makeCat('all', language==='RU'?'Все':'Barchasi', totalCount));
    allCategories.forEach(c => {
      const name = language==='RU' ? c.name_ru : c.name_uz;
      $categories.appendChild(makeCat(String(c.id), name, c.count));
    });
  }

  function renderProducts(){
    $products.innerHTML = '';
    const list = allProducts.filter(p => selectedCategory==='all' ? true : String(p.category_id)===String(selectedCategory));
    list.forEach(p => {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `
        <img src="${p.image || 'https://via.placeholder.com/300x200?text=No+Image'}" alt="">
        <div class="content">
          <div class="name">${language === 'RU' ? p.name_ru : p.name_uz}</div>
          <div class="price">${formatPrice(p.price)} UZS</div>
          <div class="qty">
            <button class="dec">-</button>
            <input type="text" class="q" value="${cart.get(p.id)?.qty || 0}" readonly />
            <button class="inc">+</button>
          </div>
        </div>
      `;
      const q = card.querySelector('.q');
      const dec = card.querySelector('.dec');
      const inc = card.querySelector('.inc');

      function setQty(n){
        n = Math.max(0, n);
        q.value = n;
        if (n === 0) cart.delete(p.id); else cart.set(p.id, {product: p, qty: n});
        updateTotal();
      }

      inc.addEventListener('click', () => setQty((parseInt(q.value)||0) + 1));
      dec.addEventListener('click', () => setQty((parseInt(q.value)||0) - 1));

      $products.appendChild(card);
    });
  }

  async function loadAll(){
    try{
      const [catsRes, prodRes] = await Promise.all([
        fetch(`${window.API_BASE}/categories`),
        fetch(`${window.API_BASE}/products`),
      ]);
      const cats = await catsRes.json();
      const prods = await prodRes.json();
      allCategories = cats.categories || [];
      allProducts = prods.products || [];
      renderCategories();
      renderProducts();
    }catch(e){
      console.error('Failed to load data', e);
    }
  }

  async function submitOrder(){
    const items = Array.from(cart.values()).map(({product, qty}) => ({ product_id: product.id, quantity: qty }));
    if (!items.length) return;
    const user = tg && tg.initDataUnsafe ? tg.initDataUnsafe.user : null;
    const payload = {
      telegram_id: user ? String(user.id) : '',
      language,
      phone: '',
      full_name: user ? (user.first_name + (user.last_name ? (' ' + user.last_name) : '')) : '',
      comment: $comment.value || '',
      items
    };
    try{
      $checkout.disabled = true;
      const res = await fetch(`${window.API_BASE}/order`, { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify(payload) });
      const data = await res.json();
      if (data.status === 'ok'){
        if (tg) tg.showAlert('✅ Buyurtma qabul qilindi!');
        if (tg) tg.close();
      }else{
        if (tg) tg.showAlert('Xatolik. Qayta urinib ko‘ring.');
      }
    }catch(e){
      console.error('Order failed', e);
      if (tg) tg.showAlert('Xatolik yuz berdi');
    }finally{
      $checkout.disabled = false;
    }
  }

  function initTexts(){
    const title = document.getElementById('title');
    const totalLabel = document.getElementById('totalLabel');
    if (language === 'RU'){
      title.textContent = 'Каталог';
      totalLabel.textContent = 'Итого:';
      $checkout.textContent = 'Оформить заказ';
      $comment.placeholder = 'Комментарий';
    } else {
      title.textContent = 'Katalog';
      totalLabel.textContent = 'Jami:';
      $checkout.textContent = 'Buyurtma berish';
      $comment.placeholder = 'Izoh';
    }
  }

  language = detectLanguage();
  initTexts();
  loadAll();
  $checkout.addEventListener('click', submitOrder);
})();
