module.exports = async (tp) => {
  const input = await tp.system.clipboard();
  const parser = new DOMParser();
  const doc = parser.parseFromString(input, 'text/html');
  const table = doc.querySelector('table');

  if (!table) return '⚠️ HTML <table> 없음.';

  const rows = Array.from(table.querySelectorAll('tr'));
  const cells = rows.map(row => Array.from(row.children).map(cell => cell.textContent.trim()));

  const header = cells[0];
  const separator = header.map(() => '---');
  const body = cells.slice(1);

  const md = [
    `| ${header.join(' | ')} |`,
    `| ${separator.join(' | ')} |`,
    ...body.map(row => `| ${row.join(' | ')} |`)
  ].join('\n');

  await tp.system.clipboard(md);
  return md;
};
