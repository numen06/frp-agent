/** 判断代理是否为 SSH 升级候选（与后端规则一致） */
export function isSshCandidateProxy(proxy) {
  return (
    proxy &&
    proxy.proxy_type === 'tcp' &&
    proxy.local_port === 22 &&
    proxy.remote_port != null &&
    proxy.status === 'online'
  )
}
