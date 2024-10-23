function filterTable() {
  const dataFilter = document.getElementById('data-filter').value.toLowerCase();
  const rows = document.querySelectorAll('#main-table tbody tr');

  let visibleRows = [];
  let visibleRowIndex = 0;

  rows.forEach(row => {
    if (!row.dataset.filterData) {
      const rowData = Array.from(row.querySelectorAll('.data-col'))
        .map(col => col.innerText.toLowerCase())
        .join(' ');
      row.dataset.filterData = rowData;
    }

    if (row.dataset.filterData.includes(dataFilter)) {
      row.style.display = '';
      row.classList.remove('bg-white', 'even:bg-gray-200', 'bg-gray-200');
      visibleRows.push(row);

      if (visibleRowIndex % 2 === 0) {
        row.classList.add('bg-white');
      } else {
        row.classList.add('bg-gray-200');
      }
      visibleRowIndex++;
    } else {
      row.style.display = 'none';
    }
  });
}

let filterTimeout;
document.getElementById('data-filter').addEventListener('keyup', () => {
  clearTimeout(filterTimeout);
  filterTimeout = setTimeout(filterTable, 200);
});

function changeSeason() {
  const seasonSelect = document.getElementById('season-select');
  const selectedValue = seasonSelect.value;
  const baseUrl = seasonSelect.getAttribute('data-base-url');

  if (selectedValue === "all") {
    window.location.href = `${baseUrl}`;
  } else {
    window.location.href = `${baseUrl}?year=${selectedValue}`;
  }
}
