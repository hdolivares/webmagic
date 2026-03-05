"""
E-commerce cart modal injection.

Appends JavaScript to enable a simulated cart on generated e-commerce sites.
When the user clicks Add to Cart or the nav cart icon, items are tracked and
a modal displays the cart with remove, quantity controls, and a non-functional
checkout button.
"""
import json
import logging

logger = logging.getLogger(__name__)


_CART_TEMPLATE = """
// WebMagic E-commerce Cart Simulation
(function() {
  window.__wmCart = window.__wmCart || [];
  var CART_BTN_SEL = '#nav-cart-btn';
  var ADD_BTN_SEL = '.add-to-cart-btn';
  var currencySymbol = __CURRENCY__;

  function getCartCount() {
    return window.__wmCart.reduce(function(s, i) { return s + (i.qty || 1); }, 0);
  }

  function updateBadge() {
    var btn = document.querySelector(CART_BTN_SEL);
    if (!btn) return;
    var badge = btn.querySelector('.wm-cart-badge');
    var n = getCartCount();
    if (n > 0) {
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'wm-cart-badge';
        badge.style.cssText = 'position:absolute;top:-4px;right:-4px;min-width:16px;height:16px;padding:0 4px;font-size:11px;font-weight:700;line-height:16px;text-align:center;background:var(--color-primary,#1e40af);color:#fff;border-radius:8px;';
        btn.style.position = 'relative';
        btn.appendChild(badge);
      }
      badge.textContent = n > 99 ? '99+' : n;
      badge.style.display = '';
    } else if (badge) {
      badge.style.display = 'none';
    }
  }

  function addToCart(id, name, price) {
    var existing = window.__wmCart.find(function(i) { return i.id === id; });
    if (existing) {
      existing.qty = (existing.qty || 1) + 1;
    } else {
      window.__wmCart.push({ id: id, name: name, price: parseFloat(price) || 0, qty: 1 });
    }
    updateBadge();
  }

  function removeFromCart(id) {
    window.__wmCart = window.__wmCart.filter(function(i) { return i.id !== id; });
    updateBadge();
  }

  function changeQty(id, delta) {
    var item = window.__wmCart.find(function(i) { return i.id === id; });
    if (!item) return;
    item.qty = Math.max(0, (item.qty || 1) + delta);
    if (item.qty <= 0) removeFromCart(id);
    updateBadge();
  }

  function openCartModal() {
    if (document.getElementById('wm-cart-modal')) return;
    var total = window.__wmCart.reduce(function(s, i) {
      return s + (i.price * (i.qty || 1));
    }, 0);
    var itemsHtml = window.__wmCart.map(function(i) {
      return '<div class="wm-cart-item" data-id="' + i.id + '">' +
        '<div class="wm-cart-item-name">' + escapeHtml(i.name) + '</div>' +
        '<div class="wm-cart-item-price">' + currencySymbol + (i.price * (i.qty || 1)).toFixed(2) + '</div>' +
        '<div class="wm-cart-item-actions">' +
        '<button type="button" class="wm-cart-qty-btn" data-delta="-1">−</button>' +
        '<span class="wm-cart-qty">' + (i.qty || 1) + '</span>' +
        '<button type="button" class="wm-cart-qty-btn" data-delta="1">+</button>' +
        '<button type="button" class="wm-cart-remove">Remove</button>' +
        '</div></div>';
    }).join('') || '<p class="wm-cart-empty">Your cart is empty.</p>';
    var modal = document.createElement('div');
    modal.id = 'wm-cart-modal';
    modal.style.cssText = 'position:fixed;inset:0;z-index:10002;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.6);font-family:system-ui,sans-serif;';
    modal.innerHTML = '<div class="wm-cart-drawer" style="background:var(--color-surface,#fff);color:var(--color-text,#1f2937);border-radius:12px;max-width:420px;width:90%;max-height:85vh;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 25px 50px rgba(0,0,0,0.25);">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid var(--color-text-muted,#e5e7eb);">' +
      '<h3 style="margin:0;font-size:18px;">Shopping Cart</h3>' +
      '<button type="button" id="wm-cart-close" style="background:none;border:none;font-size:24px;cursor:pointer;color:var(--color-text-muted,#6b7280);line-height:1;">×</button>' +
      '</div>' +
      '<div class="wm-cart-items" style="flex:1;overflow-y:auto;padding:16px;">' + itemsHtml + '</div>' +
      '<div style="padding:16px 20px;border-top:1px solid var(--color-text-muted,#e5e7eb);">' +
      '<div style="display:flex;justify-content:space-between;margin-bottom:12px;font-weight:700;">' +
      '<span>Total</span><span>' + currencySymbol + total.toFixed(2) + '</span>' +
      '</div>' +
      '<button type="button" id="wm-cart-checkout" style="width:100%;padding:14px;background:var(--color-primary,#1e40af);color:#fff;border:none;border-radius:8px;font-weight:700;font-size:16px;cursor:pointer;">Checkout</button>' +
      '<p style="margin:8px 0 0;font-size:12px;color:var(--color-text-muted,#6b7280);">Checkout is a demo — no payment will be processed.</p>' +
      '</div></div>';
    document.body.appendChild(modal);
    document.getElementById('wm-cart-close').onclick = function() { modal.remove(); };
    modal.onclick = function(e) { if (e.target === modal) modal.remove(); };
    document.getElementById('wm-cart-checkout').onclick = function() {
      alert('Checkout is a demo. No payment will be processed.');
    };
    modal.querySelectorAll('.wm-cart-qty-btn').forEach(function(btn) {
      btn.onclick = function() {
        var item = btn.closest('.wm-cart-item');
        if (item) changeQty(item.dataset.id, parseInt(btn.dataset.delta, 10));
        modal.remove();
        openCartModal();
      };
    });
    modal.querySelectorAll('.wm-cart-remove').forEach(function(btn) {
      btn.onclick = function() {
        var item = btn.closest('.wm-cart-item');
        if (item) removeFromCart(item.dataset.id);
        modal.remove();
        if (getCartCount() > 0) openCartModal();
      };
    });
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  document.addEventListener('click', function(e) {
    var addBtn = e.target.closest(ADD_BTN_SEL);
    if (addBtn) {
      e.preventDefault();
      var id = addBtn.dataset.productId || 'item';
      var name = addBtn.dataset.productName || 'Product';
      var price = addBtn.dataset.productPrice || '0';
      addToCart(id, name, price);
    }
    var cartBtn = e.target.closest(CART_BTN_SEL);
    if (cartBtn) {
      e.preventDefault();
      openCartModal();
    }
  });

  document.addEventListener('DOMContentLoaded', function() {
    updateBadge();
  });
})();
"""


def _cart_js(currency_symbol: str = "$") -> str:
    return _CART_TEMPLATE.replace("__CURRENCY__", json.dumps(currency_symbol))


def inject_ecommerce_cart_js(js: str, currency_symbol: str = "$") -> str:
    """
    Append the e-commerce cart simulation script to the site's JavaScript.

    The script listens for clicks on .add-to-cart-btn (with data-product-id,
    data-product-name, data-product-price) and #nav-cart-btn, maintains an
    in-memory cart, and shows a modal with items, quantity controls, and
    a non-functional checkout button.
    """
    return (js or "") + "\n" + _cart_js(currency_symbol)
