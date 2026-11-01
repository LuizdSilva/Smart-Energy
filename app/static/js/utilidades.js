const CSRF = document.querySelector('meta[name="csrf-token"]').content;

const seletorAno = document.getElementById('ano-sel');
if (seletorAno) {
  seletorAno.addEventListener('change', () => {
    const url = new URL(location.href);
    url.searchParams.set('ano', seletorAno.value);
    location.href = url;
  });
}

async function apiPost(url, corpo) {
  const resposta = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {'Content-Type': 'application/json', 'X-CSRF-Token': CSRF},
    body: JSON.stringify(corpo),
  });
  let data = {};
  try {
    data = await resposta.json();
  } catch (erro) {
  }
  return {ok: resposta.ok, status: resposta.status, data};
}

if (window.Chart) {
  Chart.defaults.font.family = '"Segoe UI", system-ui, sans-serif';
}
