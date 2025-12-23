import { createApp } from 'vue'
import { createPinia } from 'pinia'
import '@tabler/core/dist/css/tabler.min.css'
import './assets/dropdown.css'
import './assets/button-fix.css'
import './assets/alert-fix.css'
import './assets/page-layout.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

app.mount('#app')



