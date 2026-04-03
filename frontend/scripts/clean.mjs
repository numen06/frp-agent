/**
 * 清理 Vite 预构建缓存与生产构建目录，避免多项目/多分支混用旧缓存。
 */
import { rmSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const frontendRoot = join(here, '..')
const paths = [
  join(frontendRoot, 'node_modules', '.vite'),
  join(frontendRoot, '..', 'dist')
]

for (const p of paths) {
  if (existsSync(p)) {
    rmSync(p, { recursive: true, force: true })
    console.log('已删除:', p)
  } else {
    console.log('跳过（不存在）:', p)
  }
}
