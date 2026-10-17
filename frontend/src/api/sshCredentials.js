import api from './index'

export const sshCredentialsApi = {
  get(id) { return api.get(`/ssh-credentials/${id}`) },
  list(params = {}) {
    return api.get('/ssh-credentials', { params })
  },

  create(data) {
    return api.post('/ssh-credentials', data)
  },

  update(id, data) {
    return api.put(`/ssh-credentials/${id}`, data)
  },

  remove(id) {
    return api.delete(`/ssh-credentials/${id}`)
  }
}
