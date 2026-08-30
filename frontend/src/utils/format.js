export function asciiBar(percentage, width = 10) {
  const filled = Math.max(0, Math.min(width, Math.round((percentage / 100) * width)));
  return '█'.repeat(filled) + ' '.repeat(width - filled);
}

export function padLabel(label, width) {
  return label.length >= width ? `${label} ` : label.padEnd(width, ' ');
}
