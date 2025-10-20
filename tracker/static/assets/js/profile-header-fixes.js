(function(){
  function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  function enhanceHeader(){
    try{
      var dropdown = document.querySelector('.profile-dropdown');
      if(!dropdown) return;
      // Fix My Profile link
      var anchors = dropdown.querySelectorAll('a');
      anchors.forEach(function(a){
        if(/user-profile\.html$/.test(a.getAttribute('href')||'')){
          a.setAttribute('href', (window.__APP_PREFIX__||'') + '/profile/');
        }
      });
      // Replace Logout anchor with POST
      var logoutBtn = Array.from(anchors).find(function(a){
        return /login\.html$/.test(a.getAttribute('href')||'') || /logout/i.test(a.textContent||'');
      });
      if(logoutBtn){
        logoutBtn.removeAttribute('href');
        logoutBtn.addEventListener('click', function(e){
          e.preventDefault();
          fetch((window.__APP_PREFIX__||'') + '/logout/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
          }).then(function(){ window.location.href = (window.__APP_PREFIX__||'') + '/login/'; })
          .catch(function(){ window.location.href = (window.__APP_PREFIX__||'') + '/login/'; });
        });
      }
    }catch(e){/* no-op */}
  }
  document.addEventListener('DOMContentLoaded', enhanceHeader);
})();
