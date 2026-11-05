"""Local-only mobile discovery, pending lifecycle, layered RDP errors and SSH status."""
import json
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from playwright.sync_api import sync_playwright,expect
import capture_screenshots as demo

OUT=Path(__file__).resolve().parents[2]/".codex-remote-attachments/discovery"
OUT.mkdir(exist_ok=True)

def main():
 errors=[];state={"import_fail":True,"scan_fail":False,"test_pass":False,"member":False};hosts=[];writes=[]
 candidates=[dict(proxy_id=i,name=name,server_name="节点-"*8,host_type=kind,address="192.0.2.8",port=6000+i,available=ok,existing_host_id=5 if i==4 else None,message=msg,docker_use_tls=True) for i,name,kind,ok,msg in [(1,"识别主机-"*14,"ssh",True,"SSH 握手正常，未验证登录"),(2,"office_rdp","rdp",True,"RDP TLS正常"),(3,"offline_ssh","ssh",False,"穿透服务器不可达"),(4,"existing_ssh","ssh",False,"已加入")]]
 def intercept(route):
  u=urlparse(route.request.url);path=u.path;method=route.request.method
  if u.netloc!="127.0.0.1:4173":errors.append("external request");route.abort();return
  if not path.startswith("/api/"):route.continue_();return
  if path=="/api/settings/user":route.fulfill(json=dict(username="demo",role="user" if state["member"] else "admin"));return
  if path=="/api/managed-hosts/context" and state["member"]:route.fulfill(json=dict(is_admin=False,actor_type="user",actor_name="demo"));return
  if path=="/api/managed-hosts/discovery/scan":
   route.fulfill(status=503 if state["scan_fail"] else 200,json={"detail":"识别失败，请重试"} if state["scan_fail"] else {"items":candidates});return
  if path=="/api/managed-hosts/discovery/import":
   body=route.request.post_data_json;writes.append(body)
   if state["import_fail"]:route.fulfill(status=409,json={"detail":"代理状态已变化，请重新检测"});return
   ids=[]
   for pid in body["proxy_ids"]:
    row=next(c for c in candidates if c["proxy_id"]==pid);host=deepcopy(demo.HOSTS[0]);host.update(id=50+pid,name=row["name"],host_type=row["host_type"],is_active=False,activation_pending=True,credential_id=None,credential_name="未配置凭据",last_status="unknown",last_message="代理导入，未激活");hosts.append(host);ids.append(host["id"])
   route.fulfill(json={"created_ids":ids,"existing_ids":[]});return
  if path=="/api/managed-hosts":
   query=parse_qs(u.query);rows=hosts
   if query.get("host_id"):rows=[h for h in rows if h["id"]==int(query["host_id"][0])]
   route.fulfill(json={"items":rows,"total":len(rows),"page":1,"page_size":20});return
  if path.startswith("/api/managed-hosts/5") and method=="PUT":
   h=next(h for h in hosts if h["id"]==int(path.rsplit("/",1)[-1]));h.update(route.request.post_data_json);h["activation_pending"]=True;h["is_active"]=False;route.fulfill(json=h);return
  if path.endswith("/test"):
   hid=int(path.split("/")[-2]);h=next(h for h in hosts if h["id"]==hid)
   if h["host_type"]=="rdp":route.fulfill(status=503,json={"detail":"穿透服务器“node”无法连接，请先检查穿透服务；尚未检查目标主机或证书。"});return
   h.update(is_active=state["test_pass"],activation_pending=not state["test_pass"],last_status="online" if state["test_pass"] else "error")
   route.fulfill(json=dict(success=state["test_pass"],exit_code=0 if state["test_pass"] else 1,stdout="Linux" if state["test_pass"] else "",stderr="" if state["test_pass"] else "认证失败",duration_ms=5));return
  if path=="/api/managed-hosts/ssh-protection":route.fulfill(json=dict(native_metrics=dict(counts=dict(auth_failures=21,auth_successes=3),collected_at=1793720000,first_log_at="2026-11-02T00:00:00Z"),metrics_error="",collected_at=1793720000,bans=[dict(ip="192.0.2.99",until=1793721800)],policy=dict(max_auth_attempts=3,window_seconds=300,ban_threshold=10,ban_seconds=1800,max_sessions=64,max_sessions_per_ip=24,handshake_timeout=10,auth_timeout=20),webssh=dict(active=2,max_sessions=16,max_per_user=4,max_age=3600,idle_timeout=900)));return
  if path=="/api/system/overview":route.fulfill(json=dict(latest=None,probes=[],history=[]));return
  data=demo.demo_response(u)
  if data is None:errors.append("missing fixture "+path)
  route.fulfill(json=data or {})
 with sync_playwright() as p:
  browser=p.chromium.launch();ctx=browser.new_context(has_touch=True,is_mobile=True,reduced_motion="reduce")
  ctx.add_init_script("localStorage.setItem('auth_token',btoa('demo-admin:demo-only'))");ctx.route("**/*",intercept)
  page=ctx.new_page();page.on("pageerror",lambda e:errors.append(str(e)))
  for width in [320,390,1280]:
   hosts.clear();writes.clear();state.update(import_fail=True,scan_fail=False,test_pass=False,member=False)
   page.set_viewport_size(dict(width=width,height=844));page.goto(demo.BASE+"/hosts")
   page.get_by_role("button",name="代理导入",exact=True).click();dialog=page.get_by_role("dialog")
   expect(dialog.locator("article")).to_have_count(2)
   dialog.get_by_label("选择当前筛选结果").check();expect(dialog.get_by_role("button",name="批量导入（2）",exact=True)).to_be_enabled()
   dialog.get_by_role("button",name="批量导入（2）",exact=True).click();expect(dialog.get_by_role("alert")).to_contain_text("代理状态已变化")
   expect(dialog.get_by_role("button",name="批量导入（2）",exact=True)).to_be_enabled()
   state["import_fail"]=False;dialog.get_by_role("button",name="批量导入（2）",exact=True).click();expect(dialog.get_by_role("status")).to_contain_text("已导入 2 台未激活主机")
   assert set(writes[-1]["proxy_ids"])=={1,2}
   assert dialog.evaluate("el=>el.scrollWidth<=el.clientWidth")
   buttons=dialog.locator("button").evaluate_all("els=>els.filter(e=>e.innerText.trim() && e.getClientRects().length && e.scrollWidth>e.clientWidth+1).map(e=>e.innerText)")
   assert not buttons,buttons
   dialog.get_by_role("button",name="关闭",exact=True).last.click();expect(page.locator("article")).to_have_count(2)
   card=page.locator("article").filter(has_text=candidates[0]["name"]);expect(card).to_contain_text("未激活");expect(card.get_by_role("button",name="配置主机",exact=True)).to_be_visible()
   card.get_by_role("button",name="配置主机",exact=True).click();expect(page.get_by_role("status")).to_contain_text("此主机尚未激活");expect(page.get_by_label("启用资源",exact=True)).to_have_count(0);page.get_by_role("button",name="取消",exact=True).first.click();expect(card).to_contain_text("未激活")
   card.get_by_role("button",name="连接测试",exact=True).click();expect(card).to_contain_text("未激活")
   state["test_pass"]=True;card.get_by_role("button",name="连接测试",exact=True).click();expect(card).to_contain_text("连接正常")
   rdp=page.locator("article").filter(has_text="office_rdp");rdp.get_by_role("button",name="连接测试",exact=True).click();problem=page.get_by_role("dialog");expect(problem.get_by_role("alert",name="上游穿透连接异常",exact=True)).to_be_visible();expect(problem.get_by_role("link",name="检查穿透服务",exact=True)).to_be_visible();expect(problem.get_by_role("button",name="核验并编辑主机",exact=True)).to_have_count(0)
   problem.get_by_role("button",name="关闭",exact=True).last.click()
   if width==390:page.screenshot(path=str(OUT/"pending-hosts.png"),full_page=True)
   page.goto(demo.BASE+"/operations?tab=ssh");expect(page.get_by_role("heading",name="SSH 网关与 Web SSH 防护",exact=True)).to_be_visible();expect(page.get_by_text("192.0.2.99",exact=True)).to_be_visible();expect(page.get_by_text("21",exact=True)).to_be_visible();expect(page.locator('[aria-label="SSH 防护状态"]').get_by_text("未采集",exact=True)).to_have_count(0);expect(page.get_by_text("当前终端连接：2 / 16",exact=True)).to_be_visible();assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
   if width==390:page.screenshot(path=str(OUT/"ssh-protection.png"),full_page=True)
   page.goto(demo.BASE+"/hosts");state["scan_fail"]=True;page.get_by_role("button",name="代理导入",exact=True).click();dialog=page.get_by_role("dialog");expect(dialog.get_by_role("alert")).to_contain_text("识别失败");expect(dialog.get_by_text("没有识别到",exact=False)).to_have_count(0);state["scan_fail"]=False;dialog.get_by_role("button",name="重新检测",exact=True).click();expect(dialog.locator("article")).to_have_count(2)
   if width==390:page.screenshot(path=str(OUT/"discovery.png"),full_page=True)
   dialog.get_by_role("button",name="关闭",exact=True).last.click()
   print(f"Discovery selection, import failure/retry, pending activation, upstream RDP and SSH protection passed: {width}px",flush=True)
  state["member"]=True;page.reload();expect(page.get_by_role("button",name="代理导入",exact=True)).to_have_count(0)
  assert not errors,errors
  browser.close()
if __name__=="__main__":main()
