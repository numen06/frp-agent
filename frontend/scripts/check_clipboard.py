"""Copy actual fixture values via native Clipboard API and dialog-safe fallback."""
import sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright,expect
import capture_screenshots as demo

OUT=Path(__file__).resolve().parents[2]/".codex-remote-attachments/clipboard"
OUT.mkdir(exist_ok=True)
INIT="""
localStorage.setItem('auth_token',btoa('demo-admin:demo-only'));
const read = navigator.clipboard.readText.bind(navigator.clipboard);
window.__readClipboard = () => read();
window.__copyMode = 'native';
const write = navigator.clipboard.writeText.bind(navigator.clipboard);
Object.defineProperty(navigator.clipboard,'writeText',{value: text => window.__copyMode==='native' ? write(text) : Promise.reject(new DOMException('Test denied','NotAllowedError'))});
const exec = document.execCommand.bind(document);
document.execCommand=(...args)=>window.__copyMode==='blocked' ? false : exec(...args);
window.__copyContexts=[];
document.addEventListener('copy',()=>window.__copyContexts.push({inDialog:Boolean(document.activeElement?.closest('[role=dialog]')),value:document.activeElement?.value}));
"""

def main():
 errors=[]
 def intercept(route):
  u=urlparse(route.request.url)
  if u.netloc!='127.0.0.1:4173':errors.append('External request');route.abort();return
  if not u.path.startswith('/api/'):route.continue_();return
  if u.path.startswith('/api/api-keys/') and u.path.endswith('/full-key'):
   route.fulfill(json=dict(key='dummy-test-only-key-for-clipboard'));return
  if u.path.startswith('/api/api-keys/') and u.path.rsplit('/',1)[-1].isdigit():
   route.fulfill(json=dict(key='dummy-test-only-key-for-clipboard'));return
  data=demo.demo_response(u)
  if data is None:errors.append('Missing fixture '+u.path)
  route.fulfill(json=data or {})
 with sync_playwright() as p:
  b=p.chromium.launch();ctx=b.new_context(permissions=['clipboard-read','clipboard-write'],reduced_motion='reduce',has_touch=True)
  ctx.add_init_script(INIT);ctx.route('**/*',intercept)
  page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  for width in [390,1280]:
   page.set_viewport_size(dict(width=width,height=844))
   for mode in ['native','denied','unavailable','blocked']:
    page.goto(demo.BASE+'/hosts');expect(page.locator('article')).to_have_count(len(demo.HOSTS))
    page.evaluate("(mode)=>{window.__copyMode=mode;if(mode==='unavailable')Object.defineProperty(navigator,'clipboard',{value:undefined,configurable:true});}",mode)
    card=page.locator('article').filter(has_text='production-linux');card.get_by_role('button',name='连接详情',exact=True).click()
    dialog=page.get_by_role('dialog');button=dialog.get_by_role('button',name='复制网关地址',exact=True)
    expected=button.locator('xpath=..').locator('code').inner_text().strip();button.click()
    if '--expect-failure' in sys.argv and mode=='denied':
     expect(page.locator('[data-sonner-toast]').first).to_contain_text('复制失败');print('Reproduced: denied Clipboard API causes failure despite a usable browser copy command',flush=True);b.close();return
    if mode=='blocked':
     expect(page.locator('[data-sonner-toast]')).to_have_count(1);expect(page.locator('[data-sonner-toast]')).to_contain_text('复制失败')
     expect(page.get_by_text('已复制',exact=True)).to_have_count(0)
    else:
     expect(page.locator('[data-sonner-toast]')).to_have_count(1);expect(page.get_by_text('已复制',exact=True)).to_be_visible()
     assert page.evaluate('window.__readClipboard()')==expected,'Clipboard must contain exactly the displayed fixture value'
     if mode!='native':
      assert page.evaluate('window.__copyContexts.at(-1).inDialog'),'Fallback must stay inside the active dialog'
      assert button.evaluate('el=>document.activeElement===el'),'Focus must return to the copy button'
    assert page.locator('[data-clipboard-copy]').count()==0,'Temporary copied content must be removed'
    expect(dialog).to_be_visible();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    print(f'Clipboard {mode} path passed: {width}px',flush=True)
   # Copy long multiline content from a modal, preserving all line breaks.
   page.goto(demo.BASE+'/hosts');page.evaluate("window.__copyMode='denied'")
   page.get_by_role('button',name='AI / curl 添加提示词',exact=True).click();dialog=page.get_by_role('dialog')
   expected=dialog.locator('textarea').input_value();dialog.get_by_role('button',name='复制提示词',exact=True).click()
   expect(page.get_by_text('已复制',exact=True)).to_be_visible();actual=page.evaluate('window.__readClipboard()');assert actual.replace('\r\n','\n')==expected.replace('\r\n','\n'),'Multiline clipboard text must be complete (Windows uses CRLF)'
   # Fetch a fixture key asynchronously before copying from the list.
   dialog.get_by_role('button',name='关闭',exact=True).last.click();page.goto(demo.BASE+'/api-keys');page.evaluate("window.__copyMode='denied'")
   page.get_by_role('button',name='复制完整密钥',exact=True).filter(visible=True).first.click()
   expect(page.get_by_text('已复制',exact=True)).to_be_visible();assert page.evaluate('window.__readClipboard()')=='dummy-test-only-key-for-clipboard'
   if width==390:page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
  assert not errors,errors
  b.close()
if __name__=='__main__':main()
