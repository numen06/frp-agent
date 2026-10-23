export function formatBytes(value) {
  if (value === null || value === undefined) return '未采集'
  const bytes = Number(value)
  if (!Number.isFinite(bytes) || bytes < 0) return '未采集'
  if (bytes < 1024) return `${bytes} B`
  const unit = Math.min(4, Math.floor(Math.log(bytes) / Math.log(1024)))
  return `${(bytes / 1024 ** unit).toFixed(2)} ${['B', 'KiB', 'MiB', 'GiB', 'TiB'][unit]}`
}
