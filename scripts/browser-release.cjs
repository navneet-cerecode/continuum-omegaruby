// Actual account UI, scoped API and import flow; credentials stay in ignored QA files.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const qa=JSON.parse(fs.readFileSync('.runtime/release-qa.json','utf8'));
 assert(qa.graphs.every(name=>/^continuum_releaseqa_[a-f0-9]{32}$/.test(name)));
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const context=await browser.newContext({baseURL:'http://127.0.0.1:8000',viewport:{width:1440,height:1050},recordVideo:{dir:'.runtime/release-video',size:{width:1440,height:1050}}});
 const page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{window.__csp=[];document.addEventListener('securitypolicyviolation',e=>window.__csp.push(e.violatedDirective));});
 try {
  await page.goto('/');await page.getByRole('heading',{name:'Sign in to your company context.'}).waitFor();
  assert.equal((await page.request.get('/api/overview')).status(),401);
  async function login(username){
   await page.getByLabel('Username',{exact:true}).fill(username);await page.getByLabel('Password',{exact:true}).fill(qa.password);
   await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.getByText('FalkorDB connected').waitFor();
   const session=await (await page.request.get('/api/auth/session')).json();
   assert(session.authenticated && session.username===username);
   assert.equal((await (await page.request.get('/api/entities/release-qa-marker')).json()).entity.name,qa.graphs[username==='other'?1:0]);
   return session;
  }
  const reader=await login('reader');
  assert.equal((await page.request.post('/api/changes/withdraw-security',{headers:{'X-CSRF-Token':reader.csrf}})).status(),403);
  await page.getByRole('button',{name:'Workspace library',exact:true}).click();
  await page.getByText('Synthetic QA paging record',{exact:true}).first().waitFor();
  assert.equal(await page.getByRole('button',{name:'Import sources',exact:true}).count(),0);
  assert.equal(await page.locator('.library-records article').count(),25);
  await page.getByRole('button',{name:'Load older records',exact:true}).click();
  await page.waitForFunction(()=>document.querySelectorAll('.library-records article').length===35);
  await page.getByRole('button',{name:'Close workspace library'}).click();
  await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.getByRole('heading',{name:'Sign in to your company context.'}).waitFor();
  const admin=await login('admin');
  assert.equal((await page.request.post('/api/changes/withdraw-security')).status(),403);
  await page.getByRole('button',{name:'Workspace library',exact:true}).click();await page.getByRole('button',{name:'Import sources',exact:true}).click();
  const meta={id:'doc-browser-onboard-v1',document_id:'doc-browser-onboard',title:'Synthetic browser onboarding review',version:1,valid_from:'2026-10-17T01:00:00Z',authority:'product',synthetic:true,subjects:['project-atlas']};
  const markdown='---json\n'+JSON.stringify(meta,null,2)+'\n---\nSynthetic review for source onboarding. This excerpt records context and does not grant launch approval.';
  await page.getByLabel('Markdown source 1',{exact:true}).fill(markdown);
  await page.getByRole('button',{name:'Preview sources',exact:true}).click();await page.getByRole('heading',{name:'Review the complete batch'}).waitFor();
  assert(await page.getByRole('button',{name:'Import reviewed batch',exact:true}).isDisabled());
  await page.screenshot({path:'artifacts/release-import-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'artifacts/release-import-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1050});
  if(process.argv.includes('--display-only')) { fs.writeFileSync('artifacts/browser-release-display.json',JSON.stringify({verified_at:new Date().toISOString(),final_build:true,mobile_no_overflow:true,page_errors:errors,csp_violations:await page.evaluate(()=>window.__csp)},null,2)); console.log('Final library display checked.'); return; }
  await page.getByRole('checkbox',{name:'I reviewed the excerpts, authority, dates and subject mappings.'}).check();
  await page.getByRole('button',{name:'Import reviewed batch',exact:true}).click();await page.getByRole('status').filter({hasText:'1 source versions imported.'}).waitFor();
  const imported=await (await page.request.get('/api/entities/doc-browser-onboard-v1')).json();assert.equal(imported.entity.imported_by,'admin');
  await page.getByRole('button',{name:'Close workspace library'}).click();
  await page.reload();await page.getByText('FalkorDB connected').waitFor();
  assert.equal((await (await page.request.get('/api/auth/session')).json()).username,'admin');
  await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.getByRole('heading',{name:'Sign in to your company context.'}).waitFor();
  await login('other');assert.equal((await page.request.get('/api/entities/doc-browser-onboard-v1')).status(),409);
  assert.equal((await (await page.request.get('/api/readiness?project_id=project-atlas')).json()).status,'supported');
  await page.screenshot({path:'artifacts/release-account-desktop.png',fullPage:true});
  assert.deepEqual(errors,[]);assert.deepEqual(await page.evaluate(()=>window.__csp),[]);
  fs.writeFileSync('artifacts/browser-release.json',JSON.stringify({verified_at:new Date().toISOString(),real_database:true,account_sessions:true,role_denial:true,csrf_denial:true,company_isolation:true,preview_before_import:true,import_actor_recorded:true,paged_35_records:true,fresh_authenticated_session:true,mobile_no_overflow:true,page_errors:errors,csp_violations:[]},null,2));
  console.log('Account, role, CSRF, paging, import, fresh-session and company-isolation browser checks passed.');
 } finally { await context.close(); const video=await page.video().path();if(!process.argv.includes('--display-only'))fs.copyFileSync(video,'artifacts/CONTINUUM-account-onboarding-demo.webm');await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1)});
