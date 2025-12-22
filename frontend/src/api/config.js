import api from './index'

export const configApi = {
  // 生成配置
  generateConfig(data) {
    return api.post('/config/generate', data)
  },
  
  // 导入配置（文件上传）
  importConfig(formData) {
    return api.post('/config/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  // 导入配置（文本）
  importConfigText(data) {
    return api.post('/config/import/text', data)
  },
  
  // 导入配置（直接，推荐）
  importConfigDirect(format, serverName, content) {
    return api.post(`/config/import/${format}/${serverName}`, content, {
      headers: {
        'Content-Type': 'text/plain'
      }
    })
  },
  
  // INI 转 TOML
  convertIniToToml(iniContent) {
    return api.post('/frpc/convert/ini-to-toml/direct', iniContent, {
      headers: {
        'Content-Type': 'text/plain'
      }
    })
  }
}



