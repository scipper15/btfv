let sortDirection = 'asc';
let lastSortedColumn = null;

// Sorting Functionality
function sortTable(column, type = 'string', headerElement) {
  const table = document.getElementById('main-table');
  const tbody = table.querySelector('tbody');

  // Cache rows as a single array
  const rows = Array.from(tbody.rows);

  // Preprocess row values once
  rows.forEach(row => {
    const cellValue = row.querySelector(`.${column}`).innerText.trim();
    row.dataset.sortValue = (type === 'number') ? parseFloat(cellValue) || 0 : cellValue.toLowerCase();
  });

  // Sort the rows based on the dataset value
  rows.sort((a, b) => {
    const aData = (type === 'number') ? parseFloat(a.dataset.sortValue) : a.dataset.sortValue;
    const bData = (type === 'number') ? parseFloat(b.dataset.sortValue) : b.dataset.sortValue;

    if (aData < bData) return sortDirection === 'asc' ? -1 : 1;
    if (aData > bData) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  // Rebuild the DOM in a more efficient way
  const fragment = document.createDocumentFragment();
  rows.forEach(row => fragment.appendChild(row));
  tbody.innerHTML = ''; // Clear the table body
  tbody.appendChild(fragment); // Append the sorted rows in one go

  // Toggle sorting direction for next click
  sortDirection = (sortDirection === 'asc') ? 'desc' : 'asc';

  // Manage Carets: Reset previous caret, add new one
  if (lastSortedColumn && lastSortedColumn !== headerElement) {
    lastSortedColumn.querySelector('.caret').textContent = ''; // Clear the previous column's caret
  }

  const caretSymbol = sortDirection === 'asc' ? '▲' : '▼';
  headerElement.querySelector('.caret').textContent = caretSymbol;
  lastSortedColumn = headerElement; // Keep track of the currently sorted column
  // Reapply alternating background classes
  applyAlternatingBackground(rows);
}

// Set initial sort state on page load
window.onload = function() {
  const initialSortColumn = document.querySelector('th[onclick*="rating-combined-col"]');
  lastSortedColumn = initialSortColumn; // Set the last sorted column to "Combined"
  initialSortColumn.querySelector('.caret').textContent = '▲'; // Indicate it's sorted in ascending order

  // Apply alternating background colors initially
  const rows = Array.from(document.querySelectorAll('#main-table tbody tr'));
  applyAlternatingBackground(rows);
};

// Function to apply alternating background colors
function applyAlternatingBackground(rows) {
  let visibleRowIndex = 0;  // To track the visible rows' index

  rows.forEach(row => {
    if (row.style.display !== 'none') {  // Only consider visible rows
      row.classList.remove('bg-gray-200', 'even:bg-gray-200');
      if (visibleRowIndex % 2 !== 0) {
        row.classList.add('bg-gray-200');  // Apply 'bg-gray-200' to even rows
      }
      visibleRowIndex++;
    }
  });
}
