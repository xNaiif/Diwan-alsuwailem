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
