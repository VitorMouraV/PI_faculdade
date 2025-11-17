document.addEventListener('DOMContentLoaded', function () {
  const professionalSelect = document.getElementById('professional_id');
  const serviceSelect = document.getElementById('service_id');
  const dateInput = document.getElementById('date');
  const timeSelect = document.getElementById('time');

  function resetServices() {
    if (!serviceSelect) return;
    serviceSelect.innerHTML = '';
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'Selecione primeiro um profissional';
    serviceSelect.appendChild(opt);
    serviceSelect.disabled = true;
  }

  function resetTimes(message) {
    if (!timeSelect) return;
    timeSelect.innerHTML = '';
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = message || 'Selecione a data e o profissional';
    timeSelect.appendChild(opt);
    timeSelect.disabled = true;
  }

  if (professionalSelect && serviceSelect) {
    professionalSelect.addEventListener('change', function () {
      const professionalId = professionalSelect.value;
      resetTimes('Selecione a data e o profissional');

      if (!professionalId) {
        resetServices();
        return;
      }

      fetch(`/api/servicos?professional_id=${encodeURIComponent(professionalId)}`)
        .then(response => response.json())
        .then(data => {
          const services = data.services || [];
          serviceSelect.innerHTML = '';

          if (services.length === 0) {
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = 'Nenhum módulo cadastrado para este profissional';
            serviceSelect.appendChild(opt);
            serviceSelect.disabled = true;
          } else {
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = 'Selecione um módulo';
            serviceSelect.appendChild(placeholder);

            services.forEach(s => {
              const opt = document.createElement('option');
              opt.value = s.id;
              opt.textContent = s.name;
              serviceSelect.appendChild(opt);
            });

            serviceSelect.disabled = false;
          }
        })
        .catch(err => {
          console.error('Erro ao carregar serviços', err);
          resetServices();
        });
    });
  }

  function loadSlots() {
    if (!dateInput || !timeSelect || !professionalSelect) return;

    const dateValue = dateInput.value.trim();
    const professionalId = professionalSelect.value;

    timeSelect.innerHTML = '';

    if (!dateValue || !professionalId) {
      resetTimes('Selecione a data e o profissional');
      return;
    }

    const params = new URLSearchParams({
      date: dateValue,
      professional_id: professionalId
    });

    fetch(`/api/horarios?${params.toString()}`)
      .then(response => response.json())
      .then(data => {
        const slots = data.slots || [];
        timeSelect.innerHTML = '';

        if (slots.length === 0) {
          const opt = document.createElement('option');
          opt.value = '';
          opt.textContent = 'Nenhum horário disponível para esta data/profissional';
          timeSelect.appendChild(opt);
          timeSelect.disabled = true;
        } else {
          const placeholder = document.createElement('option');
          placeholder.value = '';
          placeholder.textContent = 'Selecione um horário';
          timeSelect.appendChild(placeholder);

          slots.forEach(slot => {
            const opt = document.createElement('option');
            opt.value = slot;
            opt.textContent = slot;
            timeSelect.appendChild(opt);
          });

          timeSelect.disabled = false;
        }
      })
      .catch(err => {
        console.error('Erro ao carregar horários', err);
        resetTimes('Erro ao carregar horários');
      });
  }

  if (dateInput) {
    dateInput.addEventListener('change', loadSlots);
    dateInput.addEventListener('blur', loadSlots);
    dateInput.addEventListener('keyup', function (e) {
      if (e.key === 'Enter') {
        loadSlots();
      }
    });
  }

  if (professionalSelect) {
    professionalSelect.addEventListener('change', loadSlots);
  }

  // Estado inicial
  resetServices();
  resetTimes();
});
