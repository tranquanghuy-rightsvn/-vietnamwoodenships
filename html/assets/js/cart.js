/* Hoa Tay Việt — shopping cart + checkout (client-side demo).
   Cart and orders live in localStorage; nothing is sent to a server. */
(function () {
  'use strict';

  var CART_KEY = 'hty-cart', ORDER_KEY = 'hty-orders';

  // Pages come in two languages (vi / en); the cart itself is shared.
  var EN = document.documentElement.lang === 'en';
  var T = EN ? {
    contact: 'Contact us', dec: 'Decrease', inc: 'Increase', qty: 'Quantity', remove: 'Remove',
    removeItem: function (n) { return 'Remove ' + n + ' from cart'; },
    errName: 'Please enter your full name.', errPhone: 'Invalid phone number.',
    errEmail: 'Invalid email address.', errAddress: 'Please enter your delivery address.',
    payQr: 'Please scan the QR code below to pay. We will confirm your order as soon as payment is received.',
    payCod: 'You will pay in cash on delivery. Our staff will call you to confirm the order.',
    product: '/product/', locale: 'en-US'
  } : {
    contact: 'Liên hệ', dec: 'Giảm', inc: 'Tăng', qty: 'Số lượng', remove: 'Xóa',
    removeItem: function (n) { return 'Xóa ' + n + ' khỏi giỏ hàng'; },
    errName: 'Vui lòng nhập họ và tên.', errPhone: 'Số điện thoại không hợp lệ.',
    errEmail: 'Email không hợp lệ.', errAddress: 'Vui lòng nhập địa chỉ nhận hàng.',
    payQr: 'Vui lòng quét mã QR bên dưới để thanh toán. Chúng tôi sẽ xác nhận đơn ngay khi nhận được tiền.',
    payCod: 'Bạn sẽ thanh toán bằng tiền mặt khi nhận hàng. Nhân viên sẽ liên hệ xác nhận đơn qua điện thoại.',
    product: '/sp/', locale: 'vi-VN'
  };
  // English names / URLs of products (assets/js/catalog.js, English pages only)
  var CATALOG = (EN && window.HTY_CATALOG) || {};
  function itemName(i) { return CATALOG[i.slug] ? CATALOG[i.slug].name : i.name; }
  function itemUrl(i) {
    return T.product + (CATALOG[i.slug] ? CATALOG[i.slug].slug : i.slug) + '/';
  }

  // carts saved before the move hold 'assets/...' paths
  function imgUrl(src) { return src && !/^(\/|https?:|data:)/.test(src) ? '/' + src : src; }

  function each(list, fn) { Array.prototype.forEach.call(list, fn); }
  function $(sel, root) { return (root || document).querySelector(sel); }

  function read(key) {
    try { var v = JSON.parse(localStorage.getItem(key)); return Array.isArray(v) ? v : []; }
    catch (e) { return []; }
  }
  function write(key, val) { try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) {} }

  var cart = read(CART_KEY);
  function save() { write(CART_KEY, cart); updateHeader(); }

  function fmt(n) { return n.toLocaleString(T.locale) + ' ₫'; }
  function count() { return cart.reduce(function (s, i) { return s + i.qty; }, 0); }
  function totals() {
    var sum = 0, contact = false;
    cart.forEach(function (i) {
      if (typeof i.price === 'number') sum += i.price * i.qty; else contact = true;
    });
    return { sum: sum, contact: contact };
  }
  function clampQty(n) { n = parseInt(n, 10); return isNaN(n) || n < 1 ? 1 : Math.min(n, 99); }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  /* ---- header badge -------------------------------------------------- */
  function updateHeader() {
    var t = totals();
    each(document.querySelectorAll('.cart-price'), function (n) { n.textContent = fmt(t.sum); });
    each(document.querySelectorAll('.cart-glyph'), function (n) { n.setAttribute('data-icon-label', String(count())); });
  }

  function addItem(item, qty) {
    var found = cart.filter(function (i) { return i.slug === item.slug; })[0];
    if (found) found.qty = clampQty(found.qty + qty);
    else cart.push({ slug: item.slug, name: item.name, img: item.img, priceText: item.priceText,
                     price: item.price, qty: clampQty(qty) });
    save();
  }

  /* ---- product page -------------------------------------------------- */
  (function productPage() {
    var box = $('[data-product]');
    if (!box) return;
    var input = $('[data-qty-input]', box);
    function item() {
      var p = box.getAttribute('data-price');
      return { slug: box.getAttribute('data-slug'), name: box.getAttribute('data-name'),
               img: box.getAttribute('data-img'), priceText: box.getAttribute('data-price-text'),
               price: p ? parseInt(p, 10) : null };
    }
    $('[data-qty-minus]', box).addEventListener('click', function () { input.value = clampQty(input.value - 1); });
    $('[data-qty-plus]', box).addEventListener('click', function () { input.value = clampQty(+input.value + 1); });
    input.addEventListener('change', function () { input.value = clampQty(input.value); });

    $('[data-add-to-cart]', box).addEventListener('click', function () {
      addItem(item(), clampQty(input.value));
      var note = $('[data-added-note]');
      if (note) note.hidden = false;
    });
    $('[data-buy-now]', box).addEventListener('click', function () {
      addItem(item(), clampQty(input.value));   // then follow the link to checkout
    });
  })();

  /* ---- "+" button on product cards ------------------------------------ */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('[data-card-add]') : null;
    if (!btn) return;
    e.preventDefault();
    var p = btn.getAttribute('data-price');
    addItem({ slug: btn.getAttribute('data-slug'), name: btn.getAttribute('data-name'),
              img: btn.getAttribute('data-img'), priceText: btn.getAttribute('data-price-text'),
              price: p ? parseInt(p, 10) : null }, 1);
    var mark = btn.querySelector('strong');
    if (mark) {
      mark.textContent = '✓';
      btn.classList.add('is-added');
      clearTimeout(btn._t);
      btn._t = setTimeout(function () { mark.textContent = '+'; btn.classList.remove('is-added'); }, 1300);
    }
    each(document.querySelectorAll('.cart-glyph'), function (g) {
      g.classList.remove('bump'); void g.offsetWidth; g.classList.add('bump');
    });
  });

  /* ---- cart page ----------------------------------------------------- */
  // the price text is stored in the language of the page it was added from
  function priceText(i) {
    return !i.priceText || i.priceText === 'Liên hệ' || i.priceText === 'Contact us' ? T.contact : i.priceText;
  }
  function priceLabel(i) { return typeof i.price === 'number' ? fmt(i.price) : priceText(i); }

  (function cartPage() {
    var list = $('#cart-items');
    if (!list) return;

    function render() {
      var empty = !cart.length;
      $('#cart-empty').hidden = !empty;
      $('#cart-full').hidden = empty;
      list.textContent = '';
      cart.forEach(function (i, idx) {
        var row = el('div', 'cart-row');
        var a = el('a', 'cart-thumb'); a.href = itemUrl(i);
        var img = el('img'); img.src = imgUrl(i.img); img.alt = itemName(i); a.appendChild(img);
        row.appendChild(a);

        var info = el('div', 'cart-info');
        var nm = el('a', 'cart-name', itemName(i)); nm.href = a.href;
        info.appendChild(nm);
        info.appendChild(el('div', 'cart-unit', priceLabel(i)));
        row.appendChild(info);

        var q = el('div', 'qty-box');
        var minus = el('button', null, '−'), plus = el('button', null, '+'), inp = el('input');
        minus.type = plus.type = 'button';
        minus.setAttribute('aria-label', T.dec); plus.setAttribute('aria-label', T.inc);
        inp.type = 'number'; inp.min = 1; inp.max = 99; inp.value = i.qty;
        inp.setAttribute('aria-label', T.qty);
        function set(v) { i.qty = clampQty(v); save(); render(); }
        minus.addEventListener('click', function () { set(i.qty - 1); });
        plus.addEventListener('click', function () { set(i.qty + 1); });
        inp.addEventListener('change', function () { set(inp.value); });
        q.appendChild(minus); q.appendChild(inp); q.appendChild(plus);
        row.appendChild(q);

        var rm = el('button', 'cart-remove'); rm.type = 'button';
        rm.setAttribute('aria-label', T.removeItem(itemName(i)));
        rm.title = T.remove;
        rm.innerHTML = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
          '<path d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>';
        rm.addEventListener('click', function () { cart.splice(idx, 1); save(); render(); });
        row.appendChild(rm);
        list.appendChild(row);
      });
      var t = totals();
      $('#cart-subtotal').textContent = fmt(t.sum);
      $('#cart-total').textContent = fmt(t.sum);
      $('#cart-contact-note').hidden = !t.contact;
    }
    render();
  })();

  /* ---- checkout page ------------------------------------------------- */
  (function checkoutPage() {
    var form = $('#checkout-form');
    if (!form) return;

    var qrPanel = $('#qr-panel');
    function render() {
      var empty = !cart.length;
      $('#checkout-empty').hidden = !empty;
      form.hidden = empty;
      var lines = $('#order-lines'); lines.textContent = '';
      cart.forEach(function (i) {
        var li = el('li');
        li.appendChild(el('span', null, itemName(i) + ' × ' + i.qty));
        li.appendChild(el('span', null, typeof i.price === 'number' ? fmt(i.price * i.qty) : priceText(i)));
        lines.appendChild(li);
      });
      var t = totals();
      $('#co-subtotal').textContent = fmt(t.sum);
      $('#co-total').textContent = fmt(t.sum);
      $('#co-contact-note').hidden = !t.contact;
    }
    render();

    each(form.elements.pay, function (r) {
      r.addEventListener('change', function () { qrPanel.hidden = form.elements.pay.value !== 'qr'; });
    });

    function setErr(name, msg) {
      var p = $('[data-err="' + name + '"]', form);
      if (p) p.textContent = msg || '';
      var f = form.elements[name];
      if (f) f.setAttribute('aria-invalid', msg ? 'true' : 'false');
      return !msg;
    }

    function validate() {
      var f = form.elements, ok = true, first = null;
      function check(name, msg) {
        var good = setErr(name, msg);
        if (!good && !first) first = f[name];
        ok = ok && good;
      }
      check('name', f.name.value.trim().length < 2 ? T.errName : '');
      var phone = f.phone.value.replace(/[\s.\-]/g, '');
      check('phone', /^(0|\+84)\d{9,10}$/.test(phone) ? '' : T.errPhone);
      var mail = f.email.value.trim();
      check('email', !mail || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail) ? '' : T.errEmail);
      check('address', f.address.value.trim().length < 5 ? T.errAddress : '');
      if (first) first.focus();
      return ok;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!cart.length || !validate()) return;
      var f = form.elements, t = totals();
      var code = 'HTV' + new Date().toISOString().slice(2, 10).replace(/-/g, '') +
                 String(Math.floor(Math.random() * 9000) + 1000);
      var method = f.pay.value;
      var orders = read(ORDER_KEY);
      orders.push({
        code: code, date: new Date().toISOString(), method: method, total: t.sum, hasContactPrice: t.contact,
        customer: { name: f.name.value.trim(), phone: f.phone.value.trim(), email: f.email.value.trim(),
                    address: f.address.value.trim(), note: f.note.value.trim() },
        items: cart.map(function (i) { return { slug: i.slug, name: i.name, qty: i.qty, price: i.price }; })
      });
      write(ORDER_KEY, orders);

      cart = []; save();
      form.hidden = true;
      $('#done-code').textContent = code;
      var msg = method === 'qr' ? T.payQr : T.payCod;
      $('#done-msg').textContent = msg;
      $('#done-qr').hidden = method !== 'qr';
      $('#done-transfer').textContent = code;
      var done = $('#order-done'); done.hidden = false; done.focus();
      window.scrollTo(0, 0);
    });
  })();

  updateHeader();
})();
