// Real two-cycle UI verification; requires the owned lifecycle QA server on 8000.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const graph=fs.readFileSync('.runtime/lifecycle-qa-graph.txt','utf8').trim();assert(/^continuum_lifecycle_[a-f0-9]{32}$/.test(graph));
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const context=await browser.newContext({baseURL:'http://127.0.0.1:8000',viewport:{width:1440,height:1050},...(process.env.RECORD_DEMO==='1'?{recordVideo:{dir:'.runtime/cycles-video',size:{width:1440,height:1050}}}:{})});
  const page=await context.newPage(),errors=[],responses=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.url().includes('/api/'))responses.push({path:new URL(r.url()).pathname,status:r.status()});});
  await page.addInitScript(()=>{window.__csp=[];document.addEventListener('securitypolicyviolation',e=>window.__csp.push(e.violatedDirective));});
  await page.goto('/');await page.getByText('FalkorDB connected').waitFor();
  assert.equal((await (await page.request.get('/api/entities/lifecycle-qa-marker')).json()).entity.name,graph);
  if(process.argv.includes('--display-only')){
   const saved=JSON.parse(fs.readFileSync('artifacts/browser-cycles.json','utf8'));assert.equal(saved.graph,graph);
   await page.getByRole('button',{name:'Change investigation',exact:true}).click();
   await page.getByRole('combobox',{name:'Incident history',exact:true}).selectOption(saved.events[0]);
   await page.waitForFunction(id=>new URL(location.href).searchParams.get('event')===id,saved.events[0]);
   await page.getByText('HISTORICAL DEPENDENCY PATH',{exact:true}).waitFor();
   await page.getByRole('columnheader',{name:'Owner at withdrawal',exact:true}).waitFor();
   await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'artifacts/cycles-historical-desktop.png',fullPage:true});
   await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'artifacts/cycles-historical-mobile.png',fullPage:true});
   assert.deepEqual(errors,[]);assert.deepEqual(await page.evaluate(()=>window.__csp),[]);assert(responses.every(r=>r.status===200));
   fs.writeFileSync('artifacts/browser-cycles-display.json',JSON.stringify({verified_at:new Date().toISOString(),graph,final_build:true,historical_graph_label:true,owner_at_withdrawal_label:true,mobile_no_overflow:true,page_errors:errors,csp_violations:[]},null,2));console.log('Final historical graph and ownership labels verified.');return;
  }
  assert.equal((await (await page.request.get('/api/overview')).json()).history.length,0);
  const events=[],tasks=[];
  async function finishCycle(cycle){
   await page.getByRole('heading',{name:'7 connected items need review.'}).waitFor();
   const view=await (await page.request.get('/api/overview?project_id=project-atlas')).json();events.push(view.context.event_id);
   await page.getByRole('button',{name:'Generate response plan',exact:true}).click();
   await page.getByRole('heading',{name:'Review before creating work.'}).waitFor();
   const boxes=page.getByRole('checkbox');for(let i=1;i<await boxes.count();i++)await boxes.nth(i).uncheck();
   await page.getByRole('button',{name:'Approve selected tasks',exact:true}).click();
   await page.getByText('Selected internal tasks persisted in FalkorDB. No messages were sent.').waitFor();
   const work=await (await page.request.get('/api/overview?project_id=project-atlas')).json();tasks.push(work.actions.find(a=>a.event_id===events[cycle-1]).action.id);
   await page.getByRole('button',{name:'Complete',exact:true}).click();
   await page.getByRole('dialog',{name:'Complete follow-up'}).getByRole('button',{name:'Mark complete',exact:true}).click();
   await page.getByText('Follow-up completed. Prerequisite approval still needs review.').waitFor();
   await page.getByRole('button',{name:'Change investigation',exact:true}).click();
   const panel=page.locator('.restoration-panel');
   await panel.getByLabel('I confirm this synthetic review explicitly approves the selected prerequisite.').check();
   await panel.getByRole('button',{name:'Record evidence for review',exact:true}).click();
   await panel.getByRole('heading',{name:'Review the evidence and affected items.'}).waitFor();
   await page.waitForFunction(()=>!document.querySelector('.replacement-review fieldset')?.disabled);
   const checks=panel.locator('fieldset input[type=checkbox]');assert.equal(await checks.count(),8);
   for(let i=0;i<7;i++){assert(!(await checks.nth(i).isChecked()));await checks.nth(i).check();}
   await panel.getByLabel('Revalidation rationale').fill('Synthetic launch-owner review revalidated every affected item for cycle '+cycle+' using the replacement evidence.');await checks.last().check();
   await panel.getByRole('button',{name:'Revalidate and resolve withdrawal',exact:true}).click();
   await page.getByRole('heading',{name:'Approval restored. History retained.'}).waitFor();
   assert.equal((await (await page.request.get('/api/readiness')).json()).status,'supported');
  }
  await page.getByRole('button',{name:'Introduce security update',exact:true}).click();await finishCycle(1);
  const firstSnapshot=(await (await page.request.get('/api/events/'+events[0])).json()).impact;
  await page.getByRole('button',{name:'Record another update',exact:true}).click();
  await page.getByRole('heading',{name:'7 connected items need review.'}).waitFor();
  const secondView=await (await page.request.get('/api/overview?project_id=project-atlas')).json();const second=secondView.context.event_id;
  assert.notEqual(second,events[0]);assert.equal(secondView.history[0].event.cycle_index,2);
  await page.getByRole('combobox',{name:'Incident history',exact:true}).selectOption(events[0]);
  await page.waitForFunction(id=>new URL(location.href).searchParams.get('event')===id,events[0]);
  await page.getByText('Historical incident · event-time snapshot. Current project readiness: review_required. Inspecting this incident does not change the active prerequisite.',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Generate response plan',exact:true}).count(),0);
  assert.equal(await page.getByRole('button',{name:'Record another update',exact:true}).count(),0);
  assert.deepEqual((await (await page.request.get('/api/events/'+events[0])).json()).impact,firstSnapshot);
  await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'artifacts/cycles-historical-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'artifacts/cycles-historical-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1050});
  const fresh=await context.newPage();await fresh.goto('/?project=project-atlas&event='+events[0]+'#investigation');
  await fresh.getByText('FalkorDB connected').waitFor();assert.equal(await fresh.getByRole('combobox',{name:'Incident history',exact:true}).inputValue(),events[0]);
  await fresh.getByText('Historical incident · event-time snapshot. Current project readiness: review_required. Inspecting this incident does not change the active prerequisite.',{exact:true}).waitFor();await fresh.close();
  await page.getByRole('combobox',{name:'Incident history',exact:true}).selectOption('');
  await page.waitForFunction(()=>!new URL(location.href).searchParams.has('event'));
  await finishCycle(2);assert.deepEqual(events,[events[0],second]);assert.notEqual(tasks[0],tasks[1]);
  const final=await (await page.request.get('/api/overview?project_id=project-atlas')).json();
  assert.equal(final.project_history.length,2);assert(final.actions.every(a=>a.action.state==='completed'));assert.equal(final.actions.length,2);
  await page.getByRole('combobox',{name:'Incident history',exact:true}).selectOption(events[0]);
  await page.waitForFunction(id=>new URL(location.href).searchParams.get('event')===id,events[0]);
  await page.getByText('Historical incident · event-time snapshot. Current project readiness: supported. Inspecting this incident does not change the active prerequisite.',{exact:true}).waitFor();
  await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'artifacts/cycles-both-resolved-desktop.png',fullPage:true});
  assert.deepEqual(errors,[]);const csp=await page.evaluate(()=>window.__csp);assert.deepEqual(csp,[]);assert(responses.every(r=>r.status===200),JSON.stringify(responses));
  fs.writeFileSync('artifacts/browser-cycles.json',JSON.stringify({verified_at:new Date().toISOString(),graph,events,tasks,real_database:true,browser:'Installed Chrome',two_cycles_completed:true,old_snapshot_unchanged:true,historical_read_only_during_active_withdrawal:true,fresh_history_selection:true,mobile_no_overflow:true,page_errors:errors,csp_violations:csp,api_responses:responses},null,2));console.log(JSON.stringify({events,tasks,two_cycles_completed:true,old_snapshot_unchanged:true,historical_read_only_during_active_withdrawal:true,fresh_history_selection:true,mobile_no_overflow:true}));
  if(process.env.RECORD_DEMO==='1'){await context.close();fs.copyFileSync(await page.video().path(),'artifacts/CONTINUUM-two-cycle-demo.webm');}
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
