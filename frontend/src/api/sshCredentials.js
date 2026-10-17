import api from './index'

export const sshCredentialsApi = {
  list() {
    return api.get('/ssh-credentials')
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
