// Real browser/API/FalkorDB verification. Requires the owned lifecycle QA server.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs');const assert=require('node:assert/strict');
(async()=>{
 const graph=fs.readFileSync('.runtime/lifecycle-qa-graph.txt','utf8').trim();
 assert(/^continuum_lifecycle_[a-f0-9]{32}$/.test(graph));
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const context=await browser.newContext({baseURL:'http://127.0.0.1:8000',viewport:{width:1440,height:1050}});
  const page=await context.newPage();const errors=[],responses=[];const scenarios=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('response',r=>{if(r.url().includes('/api/'))responses.push({path:new URL(r.url()).pathname,status:r.status()});});
  await page.addInitScript(()=>{window.__csp=[];document.addEventListener('securitypolicyviolation',e=>window.__csp.push(e.violatedDirective));});
  await page.goto('/');await page.getByText('FalkorDB connected').waitFor();
  assert.equal((await (await page.request.get('/api/entities/lifecycle-qa-marker')).json()).entity.name,graph);
  if(process.argv.includes('--display-only')){
   for(const [slug,name] of [['atlas','Export service security approval'],['beacon','Beacon accessibility checks passed'],['orbit','Orbit identity rollout controls confirmed']]){
    await page.getByRole('combobox',{name:'Project',exact:true}).selectOption('project-'+slug);
    await page.waitForFunction(id=>new URL(location.href).searchParams.get('project')===id,'project-'+slug);
    await page.getByRole('button',{name:'Change investigation',exact:true}).click();
    await page.getByRole('heading',{name,exact:true}).waitFor();
    await page.getByRole('heading',{name:'Prerequisite update',exact:true}).waitFor();
    await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'artifacts/multi-'+slug+'-desktop.png',fullPage:true});
    await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:'artifacts/multi-'+slug+'-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1050});
   }
   assert.deepEqual(errors,[]);assert.deepEqual(await page.evaluate(()=>window.__csp),[]);assert(responses.every(r=>r.status===200));
   fs.writeFileSync('artifacts/browser-multi-display.json',JSON.stringify({verified_at:new Date().toISOString(),graph,read_only:true,final_build:true,all_projects:true,page_errors:errors,csp_violations:[],mobile_no_overflow:true},null,2));
   console.log('Final build display verified for all three projects.');return;
  }
  assert.equal((await (await page.request.get('/api/overview')).json()).history.length,0);
  for(const [slug,count,authority] of [['atlas',7,'security'],['beacon',3,'product'],['orbit',3,'platform']]){
   await page.getByRole('button',{name:'Company context',exact:true}).click();
   const project='project-'+slug;
   await page.getByRole('combobox',{name:'Project',exact:true}).selectOption(project);
   await page.waitForFunction(id=>new URL(location.href).searchParams.get('project')===id,project);
   await page.locator('.launch-title h2').filter({hasText:'Project '+slug[0].toUpperCase()+slug.slice(1)}).waitFor();
   assert.equal((await (await page.request.get('/api/readiness?project_id='+project)).json()).status,'supported');
   await page.getByRole('button',{name:slug==='atlas'?'Introduce security update':'Introduce prerequisite update',exact:true}).click();
   await page.getByRole('heading',{name:count+' connected items need review.'}).waitFor();
   const changed=await (await page.request.get('/api/overview?project_id='+project)).json();
   assert.equal(changed.history.length,1);const event=changed.context.event_id;
   for(const other of ['atlas','beacon','orbit'].filter(x=>x!==slug))assert.equal((await (await page.request.get('/api/readiness?project_id=project-'+other)).json()).status,'supported');
   await page.getByRole('button',{name:'Generate response plan',exact:true}).click();
   await page.getByRole('heading',{name:'Review before creating work.'}).waitFor();
   const boxes=page.getByRole('checkbox');for(let i=1;i<await boxes.count();i++)await boxes.nth(i).uncheck();
   await page.getByRole('button',{name:'Approve selected tasks',exact:true}).click();
   await page.getByText('Selected internal tasks persisted in FalkorDB. No messages were sent.').waitFor();
   const queue=await (await page.request.get('/api/overview?project_id='+project)).json();
   assert.equal(queue.actions.length,1);assert.equal(queue.actions[0].event_id,event);
   await page.getByRole('button',{name:'Change investigation',exact:true}).click();
   const panel=page.locator('.restoration-panel');
   await panel.getByLabel('I confirm this synthetic review explicitly approves the selected prerequisite.').check();
   await panel.getByRole('button',{name:'Record evidence for review',exact:true}).click();
   await panel.getByText('Close the event’s open follow-ups before resolving the withdrawal.',{exact:true}).waitFor();
   assert(await panel.getByRole('button',{name:'Revalidate and resolve withdrawal'}).isDisabled());
   await panel.getByRole('button',{name:'Open follow-up queue',exact:true}).click();
   await page.getByRole('button',{name:'Complete',exact:true}).click();
   await page.getByRole('dialog',{name:'Complete follow-up'}).getByRole('button',{name:'Mark complete',exact:true}).click();
    await page.getByText('Follow-up completed. Prerequisite approval still needs review.').waitFor();
   await page.getByRole('button',{name:'Change investigation',exact:true}).click();
   await panel.getByRole('button',{name:'Refresh review',exact:true}).click();
   await page.waitForFunction(()=>!document.querySelector('.replacement-review fieldset')?.disabled);
   const confirms=panel.locator('fieldset input[type=checkbox]');assert.equal(await confirms.count(),count+1);
   for(let i=0;i<count;i++){assert(!(await confirms.nth(i).isChecked()));await confirms.nth(i).check();}
   await panel.getByLabel('Revalidation rationale').fill('Synthetic project-owner review revalidated this project’s replacement evidence and every affected dependency.');
   await confirms.last().check();
   const staged=(await (await page.request.get('/api/overview?project_id='+project)).json()).restorations[0];
   const source=await (await page.request.get('/api/entities/'+staged.source_id)).json();assert.equal(source.entity.authority,authority);
   await panel.getByRole('button',{name:'Revalidate and resolve withdrawal',exact:true}).click();
   await page.getByRole('heading',{name:'Approval restored. History retained.'}).waitFor();
   await page.getByRole('heading',{name:count+' connected items revalidated.'}).waitFor();
   assert.equal((await (await page.request.get('/api/readiness?project_id='+project)).json()).status,'supported');
   await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'artifacts/multi-'+slug+'-desktop.png',fullPage:true});
   await page.setViewportSize({width:390,height:844});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:'artifacts/multi-'+slug+'-mobile.png',fullPage:true});
   await page.setViewportSize({width:1440,height:1050});
   scenarios.push({project,impact_count:count,authority,full_lifecycle:true,unrelated_projects_supported:true,scoped_tasks:true,mobile_no_overflow:true});
  }
  const fresh=await context.newPage();await fresh.goto('/?project=project-beacon#context');
  await fresh.getByText('FalkorDB connected').waitFor();
  assert.equal(await fresh.getByRole('combobox',{name:'Project',exact:true}).inputValue(),'project-beacon');
  await fresh.locator('.launch-title').getByText('Supported',{exact:true}).waitFor();
  const recap=await (await fresh.request.get('/api/recap?project_id=project-beacon')).json();
  assert.equal(recap.changes.length,1);assert.equal(recap.changes[0].event.state,'resolved');
  assert.deepEqual(errors,[]);const csp=await page.evaluate(()=>window.__csp);assert.deepEqual(csp,[]);
  assert(responses.every(r=>r.status===200),JSON.stringify(responses));
  const report={verified_at:new Date().toISOString(),graph,real_database:true,browser:'Installed Chrome',scenarios,fresh_project_session:true,page_errors:errors,csp_violations:csp,api_responses:responses};
  fs.writeFileSync('artifacts/browser-multi-project.json',JSON.stringify(report,null,2));console.log(JSON.stringify({scenarios,fresh_project_session:true,page_errors:errors,csp_violations:csp},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
