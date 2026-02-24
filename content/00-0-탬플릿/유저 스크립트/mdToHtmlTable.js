module.exports = async (tp) => {
  const input = await tp.system.clipboard();
  const lines = input.trim().split('\n');

  if (lines.length < 2 || !lines[1].includes('|')) {
    return '⚠️ 마크다운 표가 감지되지 않음.';
  }

  const headers = lines[0].split('|').slice(1, -1).map(h => h.trim());
  const rows = lines.slice(2).map(row =>
    row.split('|').slice(1, -1).map(cell => cell.trim())
  );

  let html = '<table>\n  <thead>\n    <tr>';
  html += headers.map(h => `<th>${h}</th>`).join('');
  html += '</tr>\n  </thead>\n  <tbody>\n';

  for (const row of rows) {
    html += '    <tr>' + row.map(cell => `<td>${cell}</td>`).join('') + '</tr>\n';
  }

  html += '  </tbody>\n</table>';
  await tp.system.clipboard(html);
  return html;
};
