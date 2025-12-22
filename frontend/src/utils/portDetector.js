// 端口自动识别映射表（使用数组保持顺序，长关键字优先）
const PORT_MAPPINGS = [
  // 先检查长关键字和特殊关键字
  ['elasticsearch', 9200],
  ['postgresql', 5432],
  ['prometheus', 9090],
  ['minecraft', 25565],
  ['mariadb', 3306],
  ['mongodb', 27017],
  ['terraria', 7777],
  // HTTPS 必须在 HTTP 之前检查
  ['https', 443],
  // VNC 必须在 remote 之前检查
  ['vnc', 5900],
  // 远程桌面
  ['rdp', 3389],
  ['mstsc', 3389],
  ['remote', 3389],
  // SSH
  ['ssh', 22],
  ['sftp', 22],
  // HTTP/Web
  ['http', 80],
  ['web', 80],
  ['nginx', 80],
  ['apache', 80],
  // Docker
  ['docker', 9000],
  // MySQL
  ['mysql', 3306],
  // PostgreSQL
  ['postgres', 5432],
  ['pgsql', 5432],
  // Redis
  ['redis', 6379],
  // MongoDB
  ['mongo', 27017],
  // FTP
  ['ftp', 21],
  // SMTP
  ['smtps', 465],
  ['smtp', 25],
  // IMAP/POP3
  ['imaps', 993],
  ['imap', 143],
  ['pop3s', 995],
  ['pop3', 110],
  // DNS
  ['dns', 53],
  // NTP
  ['ntp', 123],
  // Game servers
  ['csgo', 27015],
  ['cs', 27015],
  ['mc', 25565],
  // Other common services
  ['es', 9200],
  ['kibana', 5601],
  ['grafana', 3000],
  ['jenkins', 8080],
  ['tomcat', 8080]
]

// 根据代理名称自动识别本地端口
export function autoDetectLocalPort(proxyName) {
  if (!proxyName) return 0
  
  const nameLower = proxyName.toLowerCase()
  
  // 先检查是否包含端口号（例如：dlyy_http_8080）
  const portPattern = /_(\d{2,5})$/
  const match = nameLower.match(portPattern)
  if (match) {
    const port = parseInt(match[1])
    if (port >= 1 && port <= 65535) {
      return port
    }
  }
  
  // 先尝试完整单词匹配（使用下划线或开头/结尾作为边界）
  for (const [keyword, port] of PORT_MAPPINGS) {
    const pattern = new RegExp(`(^|_)${keyword}($|_)`)
    if (pattern.test(nameLower)) {
      return port
    }
  }
  
  // 如果没有完整单词匹配，再尝试包含匹配（按顺序，长关键字优先）
  for (const [keyword, port] of PORT_MAPPINGS) {
    if (nameLower.includes(keyword)) {
      return port
    }
  }
  
  return 0
}

