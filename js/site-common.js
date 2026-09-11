/* سلوك مشترك لكل الصفحات الثابتة (شاعر/قصيدة/عن الديوان...): زر الرجوع لأعلى
   الصفحة، وزر "عرض كل القصائد" بصفحات الشعراء الطويلة. ملف خارجي (مو inline)
   عشان يمتثل لسياسة script-src 'self' بدون إضعافها بـ unsafe-inline. */

var backToTop = document.getElementById("back-to-top");
if (backToTop) {
  window.addEventListener("scroll", function () {
    backToTop.classList.toggle("visible", window.scrollY > 420);
  });
  backToTop.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

document.addEventListener("click", function (e) {
  var btn = e.target.closest(".show-all-btn");
  if (!btn) return;
  document.querySelectorAll(".poem-card-extra").forEach(function (c) {
    c.hidden = false;
  });
  btn.remove();
});

/* رابط الإبلاغ: الإيميل مُخزَّن مقسَّماً (data-u/data-d) لا كسلسلة "user@domain" متصلة
   بالـHTML — يُبنى الرابط الفعلي فقط هنا وقت الضغط، عشان حاصد الإيميلات الآلي (bot) اللي
   يفحص HTML/JS الثابت مباشرة ما يلقى الإيميل جاهزاً. */
document.addEventListener("click", function (e) {
  var link = e.target.closest("[data-report-link]");
  if (!link) return;
  e.preventDefault();
  var addr = link.dataset.u + "@" + link.dataset.d;
  window.location.href = "mailto:" + addr + "?subject=" + link.dataset.subject + "&body=" + link.dataset.body;
});
