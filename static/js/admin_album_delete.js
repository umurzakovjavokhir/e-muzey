/* Admin: fotoalbom / video qatoridagi «O'chirish» tugmasi — elementni darhol o'chiradi. */
(function () {
  function csrf() {
    var el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
  }
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.album-del-btn');
    if (!btn) return;
    e.preventDefault();
    var label = btn.getAttribute('data-kind') === 'video' ? 'videoni' : 'rasmni';
    if (!confirm('Ushbu ' + label + " o'chirishni tasdiqlaysizmi? Bu amalni qaytarib bo'lmaydi.")) return;
    btn.disabled = true;
    fetch(btn.getAttribute('data-url'), {
      method: 'POST',
      headers: {'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest'},
      credentials: 'same-origin'
    }).then(function (r) { return r.json().catch(function () { return {ok: false}; }); })
      .then(function (d) {
        if (!d.ok) { btn.disabled = false; alert(d.error || "O'chirib bo'lmadi"); return; }
        var row = btn.closest('tr');
        if (row) {
          /* Formset buzilmasligi uchun qator yashiriladi va DELETE belgilanadi */
          var del = row.querySelector('input[type=checkbox][name$="-DELETE"]');
          if (del) del.checked = true;
          row.style.display = 'none';
        }
      })
      .catch(function () { btn.disabled = false; alert("Tarmoq xatosi, qayta urinib ko'ring"); });
  });
})();
