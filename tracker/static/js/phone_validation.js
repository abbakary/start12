// Tanzania phone number validation, UI enhancement, and normalized submission
// Applies to any text input whose name contains "phone" or has a TZ pattern
(function(){
  function normalizeTZ(value){
    if(!value) return '';
    var v = String(value).replace(/[^\d+]/g,'');
    if(v.startsWith('+255')){
      return '+255' + v.replace('+255','').replace(/\D/g,'');
    }
    if(v.startsWith('0')){
      return '+255' + v.slice(1).replace(/\D/g,'');
    }
    // Fallback: if 9 digits provided, assume local without leading 0
    var digits = v.replace(/\D/g,'');
    if(digits.length === 9){ return '+255' + digits; }
    return v;
  }

  function enhanceInput(input){
    if(input.dataset.tzPhoneEnhanced === '1') return;
    input.dataset.tzPhoneEnhanced = '1';

    // Attributes to aid mobile keyboards and validation
    if(!input.getAttribute('inputmode')) input.setAttribute('inputmode','tel');
    if(!input.getAttribute('autocomplete')) input.setAttribute('autocomplete','tel');
    if(!input.getAttribute('placeholder')) input.setAttribute('placeholder','+255 712 345 678');

    // Create/ensure hidden normalized field submitted alongside
    var hiddenName = (input.getAttribute('name') || 'phone') + '_normalized';
    var existingHidden = document.querySelector('input[type="hidden"][name="'+hiddenName+'"]');
    var hidden = existingHidden || document.createElement('input');
    if(!existingHidden){
      hidden.type = 'hidden';
      hidden.name = hiddenName;
    }
    hidden.value = normalizeTZ(input.value);

    // If already wrapped with tz-phone-group (e.g., from server template), don't add another flag
    var parent = input.parentNode;
    var alreadyWrapped = parent && parent.classList && parent.classList.contains('tz-phone-group');
    var hasFlagAddon = alreadyWrapped && parent.querySelector('.tz-flag-addon');

    if(!alreadyWrapped){
      var wrapper = document.createElement('div');
      wrapper.className = 'tz-phone-group';

      var addon = document.createElement('span');
      addon.className = 'tz-flag-addon';
      var img = document.createElement('img');
      img.src = '/static/assets/images/flags/tz.svg';
      img.alt = 'TZ';
      img.className = 'tz-flag';
      addon.appendChild(img);

      parent.insertBefore(wrapper, input);
      wrapper.appendChild(addon);
      wrapper.appendChild(input);
      parent = wrapper;
    } else if(!hasFlagAddon){
      // If wrapper exists but no flag, add one (keeps single flag)
      var addon2 = document.createElement('span');
      addon2.className = 'tz-flag-addon';
      var img2 = document.createElement('img');
      img2.src = '/static/assets/images/flags/tz.svg';
      img2.alt = 'TZ';
      img2.className = 'tz-flag';
      addon2.appendChild(img2);
      parent.insertBefore(addon2, input);
    }

    // Place hidden after the wrapper
    if(!existingHidden){ parent.parentNode.insertBefore(hidden, parent.nextSibling); }

    // Sync hidden normalized on input/blur
    function onInput(e){
      var v = e.target.value.replace(/[^\d+\s]/g,'');
      // If user starts with 0, convert to +255 and keep the rest
      if(v.startsWith('0')){
        v = '+255 ' + v.slice(1);
      }
      // Length guards (max +255 123 456 789 => 16 incl spaces; local 0xx xxx xxx => 14 incl spaces)
      if(v.startsWith('+255')){ if(v.length>16) v = v.substring(0,16); }
      else { if(v.length>14) v = v.substring(0,14); }
      e.target.value = v;
      hidden.value = normalizeTZ(v);
    }
    input.addEventListener('input', onInput);
    input.addEventListener('blur', onInput);

    // Keydown guard
    input.addEventListener('keydown', function(e){
      var allowed = ['Backspace','Delete','Tab','Escape','Enter','ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'];
      if(allowed.includes(e.key) || e.ctrlKey || e.metaKey) return;
      if(!/[\d+\s]/.test(e.key)) e.preventDefault();
    });

    // Paste guard
    input.addEventListener('paste', function(e){
      e.preventDefault();
      var paste = (e.clipboardData||window.clipboardData).getData('text')||'';
      paste = paste.replace(/[^\d+\s]/g,'');
      if(paste.startsWith('0')) paste = '+255 ' + paste.slice(1);
      if(paste.startsWith('+255')) paste = paste.substring(0,16); else paste = paste.substring(0,14);
      input.value = paste; onInput({target: input});
    });
  }

  document.addEventListener('DOMContentLoaded', function(){
    var selector = 'input[type="text"][name*="phone"], input[pattern*="255"], input[name*="whatsapp"]';
    document.querySelectorAll(selector).forEach(enhanceInput);
  });
})();
