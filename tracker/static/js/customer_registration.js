(function(){
  // Helper to perform AJAX POST for wizard steps
  function ajaxPostForm(form, onSuccess, onError){
    var formData = new FormData(form);
    var xhr = new XMLHttpRequest();
    xhr.open('POST', window.location.href);
    xhr.setRequestHeader('X-Requested-With','XMLHttpRequest');

    // Set CSRF token header from cookie for Django
    function getCookie(name){
      var cookieValue = null;
      if (document.cookie && document.cookie !== ''){
        var cookies = document.cookie.split(';');
        for (var i=0;i<cookies.length;i++){
          var cookie = cookies[i].trim();
          if (cookie.substring(0, name.length+1) === (name + '=')){
            cookieValue = decodeURIComponent(cookie.substring(name.length+1));
            break;
          }
        }
      }
      return cookieValue;
    }
    var csrftoken = getCookie('csrftoken');
    if(csrftoken){ try{ xhr.setRequestHeader('X-CSRFToken', csrftoken); }catch(e){} }

    xhr.onreadystatechange = function(){
      if(xhr.readyState !== 4) return;
      console.debug('Customer reg AJAX response', xhr.status, xhr.responseText.slice(0,200));
      if(xhr.status >=200 && xhr.status < 300){
        try{
          var data = JSON.parse(xhr.responseText);
        }catch(e){
          if(onError) onError('Invalid server response');
          return;
        }
        if(data.redirect_url){ window.location.href = data.redirect_url; return; }
        if(onSuccess) onSuccess(data);
      }else{
        if(onError) onError('Server error: ' + xhr.status);
      }
    };
    xhr.send(formData);
  }

  function loadStep(step){
    var url = window.location.pathname + '?step=' + step + '&load_step=1';
    fetch(url, {headers: {'X-Requested-With':'XMLHttpRequest'}})
      .then(function(r){ return r.json(); })
      .then(function(data){
        if(data.form_html){
          var container = document.getElementById('registrationWizard');
          container.innerHTML = data.form_html;
          // Re-bind handlers
          bindWizard();
        }
      }).catch(function(e){ console.error('Failed to load step', e); });
  }

  function bindWizard(){
    console.debug('bindWizard: called');
    var form = document.getElementById('customerRegistrationForm');
    if(!form){ console.debug('bindWizard: no form (customerRegistrationForm) found'); }
    // Update progress UI helper
    function updateProgress(){
      var stepInput = document.getElementById('currentStep');
      var displayEl = document.getElementById('currentStepDisplay');
      var step = 1;
      if(stepInput){ step = parseInt(stepInput.value || '1', 10); }
      else if(displayEl){ step = parseInt(displayEl.textContent||'1',10); }
      var total = 4;
      var pct = Math.round((step/total)*100);
      var bar = document.getElementById('registrationProgressBar');
      if(bar){ bar.style.width = pct + '%'; bar.setAttribute('aria-valuenow', step); }
      if(displayEl){ displayEl.textContent = step; }
      var indicators = document.querySelectorAll('#registrationSteps .step-indicator');
      indicators.forEach(function(el, idx){
        var active = (idx+1) === step;
        el.classList.toggle('bg-primary', active);
        el.classList.toggle('bg-secondary', !active);
      });
    }

    if(!form) return;
    var stepInput = document.getElementById('currentStep');
    var step = parseInt(stepInput.value || '1', 10);
    // Ensure progress updates on bind
    updateProgress();

    // Next for step 1
    var nextBtn = document.getElementById('nextStepBtn');
    console.debug('bindWizard: nextBtn=', !!nextBtn);
    if(nextBtn){
      if(!nextBtn.dataset.bound){
        nextBtn.dataset.bound = '1';
        nextBtn.addEventListener('click', function(e){
          e.preventDefault();
          try{
            // ensure save_only is 0
            var saveOnly = document.getElementById('saveOnly'); if(saveOnly) saveOnly.value='0';
            ajaxPostForm(form, function(data){
              try{
                // If server returned form_html with errors, render it
                if(data && data.form_html && (!data.success)){
                  document.getElementById('registrationWizard').innerHTML = data.form_html; bindWizard();
                  return;
                }
                // If server returned form_html for the next step, render it
                if(data && data.form_html && data.success){
                  document.getElementById('registrationWizard').innerHTML = data.form_html; bindWizard();
                  return;
                }
                // Otherwise explicitly load next step
                var cur = parseInt((document.getElementById('currentStep')||{value:1}).value||1,10);
                var next = Math.min(cur+1,4);
                loadStep(next);
              }catch(err){ console.error('Error handling next response', err); }
            }, function(err){ console.error('AJAX error', err); alert('Request failed: ' + err); });
          }catch(err){ console.error('Next click handler error', err); }
        });
      }
    }

    // Save customer quick
    var saveBtn = document.getElementById('saveCustomerBtn');
    if(saveBtn){
      if(!saveBtn.dataset.bound){
        saveBtn.dataset.bound = '1';
        saveBtn.addEventListener('click', function(e){
          e.preventDefault();
          var saveOnly = document.getElementById('saveOnly'); if(saveOnly) saveOnly.value='1';
          ajaxPostForm(form, function(data){
            if(data.redirect_url){ window.location.href = data.redirect_url; }
            else if(data.success && data.message){ alert(data.message); }
          }, function(err){ alert(err); });
        });
      }
    }

    // Back buttons
    var backBtn2 = document.getElementById('backFromStep2');
    if(backBtn2){ backBtn2.addEventListener('click', function(){ loadStep(1); }); }
    var backBtn3 = document.getElementById('backFromStep3');
    if(backBtn3){ backBtn3.addEventListener('click', function(){ loadStep(2); }); }
    var backBtn4 = document.getElementById('backFromStep4');
    if(backBtn4){ backBtn4.addEventListener('click', function(){ loadStep(3); }); }

    // Next from step 2
    var next2 = document.getElementById('nextStep2');
    if(next2){ next2.addEventListener('click', function(e){ e.preventDefault(); ajaxPostForm(form, function(data){ try{ if(data && data.form_html && (!data.success)){ document.getElementById('registrationWizard').innerHTML = data.form_html; bindWizard(); return; } if(data && data.form_html && data.success){ document.getElementById('registrationWizard').innerHTML = data.form_html; bindWizard(); return; } var cur = parseInt((document.getElementById('currentStep')||{value:2}).value||2,10); var next = Math.min(cur+1,4); loadStep(next); }catch(err){ console.error('Error handling step2 response', err); } }, function(err){ console.error('AJAX error', err); alert('Request failed: ' + err); }); }); }

    // Next from step3
    var next3 = document.getElementById('nextServiceBtn');
    if(next3){ next3.addEventListener('click', function(e){ 
      e.preventDefault(); 
      // Store vehicle data before submitting
      storeVehicleData();
      ajaxPostForm(form, function(data){ 
        try{ 
          if(data && data.form_html && (!data.success)){ 
            document.getElementById('registrationWizard').innerHTML = data.form_html; 
            bindWizard(); 
            return; 
          } 
          if(data && data.form_html && data.success){ 
            document.getElementById('registrationWizard').innerHTML = data.form_html; 
            bindWizard(); 
            // Restore vehicle data in step 4
            setTimeout(function() {
              restoreVehicleData();
              if (typeof updateVehicleSummary === 'function') {
                updateVehicleSummary();
              }
            }, 200);
            return; 
          } 
          var cur = parseInt((document.getElementById('currentStep')||{value:3}).value||3,10); 
          var next = Math.min(cur+1,4); 
          loadStep(next); 
        }catch(err){ console.error('Error handling step3 response', err); } 
      }, function(err){ console.error('AJAX error', err); alert('Request failed: ' + err); }); 
    }); }

    // Intent and service selection visual toggles
    window.selectIntent = function(intentValue){
      document.querySelectorAll('.intent-card').forEach(function(card){ card.classList.remove('border-primary','bg-light'); });
      var clicked = event.currentTarget || event.target;
      if(clicked) clicked.classList.add('border-primary','bg-light');
      var radio = document.querySelector('input[name="intent"][value="'+intentValue+'"]');
      if(radio){ radio.checked = true; }
      var next = document.getElementById('nextStep2'); if(next) next.disabled = false;
    };

    window.selectServiceType = function(serviceValue){
      document.querySelectorAll('.service-card').forEach(function(card){ card.classList.remove('border-primary','bg-light'); });
      var clicked = event.currentTarget || event.target;
      if(clicked) clicked.classList.add('border-primary','bg-light');
      var radio = document.querySelector('input[name="service_type"][value="'+serviceValue+'"]');
      if(radio){ radio.checked = true; }
      var next = document.getElementById('nextServiceBtn'); if(next) next.disabled = false;
    };

    // If step4, bind order form interactions similar to order_create
    if(step === 4){
      var typeEl = document.querySelector('[name="type"]') || document.getElementById('id_type');
      function updateSections(){
        var t = (typeEl && (typeEl.value || (typeEl.options && typeEl.options[typeEl.selectedIndex] && typeEl.options[typeEl.selectedIndex].value))) || '';
        var s1 = document.getElementById('section-service'); if(s1) s1.style.display = (t==='service')? 'block':'none';
        var s2 = document.getElementById('section-sales'); if(s2) s2.style.display = (t==='sales')? 'block':'none';
        var s3 = document.getElementById('section-consultation'); if(s3) s3.style.display = (t==='consultation')? 'block':'none';
      }
      if(typeEl){ typeEl.addEventListener('change', updateSections); updateSections(); }

      // Auto-select brand when item changes using data-brands mapping
      var itemEl = document.getElementById('id_item_name');
      var brandEl = document.getElementById('id_brand');
      if(itemEl && brandEl){
        var mapping = {};
        try{ mapping = JSON.parse(itemEl.getAttribute('data-brands') || '{}'); }catch(e){ mapping = {}; }
        itemEl.addEventListener('change', function(){ var bn = mapping[this.value]; if(!bn) return; for(var i=0;i<brandEl.options.length;i++){ if(brandEl.options[i].text === bn || brandEl.options[i].value === bn){ brandEl.selectedIndex = i; break; } } });
      }

      // Vehicle select enabling when customer vehicles available (not needed here)
    }

  }

  // Initialize on DOM ready
  document.addEventListener('DOMContentLoaded', function(){ bindWizard(); });

  // Vehicle data preservation functions
  function storeVehicleData() {
    try {
      var vehicleData = {
        plate_number: (document.getElementById('id_plate_number') || {}).value || '',
        make: (document.getElementById('id_make') || {}).value || '',
        model: (document.getElementById('id_model') || {}).value || '',
        vehicle_type: (document.getElementById('id_vehicle_type') || {}).value || ''
      };
      sessionStorage.setItem('customerRegVehicleData', JSON.stringify(vehicleData));
    } catch(e) { console.debug('Failed to store vehicle data', e); }
  }
  
  function restoreVehicleData() {
    try {
      var stored = sessionStorage.getItem('customerRegVehicleData');
      if (!stored) return;
      
      var vehicleData = JSON.parse(stored);
      
      // Restore form fields if they exist
      var plateEl = document.getElementById('id_plate_number');
      var makeEl = document.getElementById('id_make');
      var modelEl = document.getElementById('id_model');
      var typeEl = document.getElementById('id_vehicle_type');
      
      if (plateEl) plateEl.value = vehicleData.plate_number || '';
      if (makeEl) makeEl.value = vehicleData.make || '';
      if (modelEl) modelEl.value = vehicleData.model || '';
      if (typeEl) typeEl.value = vehicleData.vehicle_type || '';
      
      // Update summary display
      if (typeof updateVehicleSummary === 'function') {
        updateVehicleSummary();
      }
      
      // Clear stored data
      sessionStorage.removeItem('customerRegVehicleData');
    } catch(e) { console.debug('Failed to restore vehicle data', e); }
  }

  // Expose a flag so inline progressive enhancement knows AJAX is active
  window.__CUSTOMER_REG_AJAX = true;
})();