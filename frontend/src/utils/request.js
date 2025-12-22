// 请求工具函数，用于调试
export function logRequest(config) {
  console.log('Request:', {
    method: config.method?.toUpperCase(),
    url: config.url,
    baseURL: config.baseURL,
    fullURL: `${config.baseURL || ''}${config.url}`,
    headers: config.headers
  })
}

export function logResponse(response) {
  console.log('Response:', {
    status: response.status,
    statusText: response.statusText,
    data: response.data
  })
}

export function logError(error) {
  console.error('Request Error:', {
    message: error.message,
    code: error.code,
    response: error.response ? {
      status: error.response.status,
      statusText: error.response.statusText,
      data: error.response.data
    } : null
  })
}

