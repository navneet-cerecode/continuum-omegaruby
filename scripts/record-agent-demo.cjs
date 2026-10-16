// Record genuine local-model UI inference on the owned lifecycle QA graph.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const graph=fs.readFileSync('.runtime/lifecycle-qa-graph.txt','utf8').trim();
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const context=await browser.newContext({baseURL:'http://127.0.0.1:8000',viewport:{width:1440,height:1050},recordVideo:{dir:'.runtime/agent-video',size:{width:1440,height:1050}}});
 const page=await context.newPage();
 try {
  await page.goto('/?project=project-atlas#context');await page.getByText('FalkorDB connected').waitFor();
  assert.equal((await (await page.request.get('/api/entities/lifecycle-qa-marker')).json()).entity.name,graph);
  const before=await (await page.request.get('/api/overview')).json();
  await page.getByRole('button',{name:'Ask agent',exact:true}).scrollIntoViewIfNeeded();
  const resultPromise=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/agent');
  await page.getByRole('button',{name:'Ask agent',exact:true}).click();
  const response=await resultPromise;assert.equal(response.status(),200);const result=await response.json();
  assert.equal(result.answer.conclusion,'Recorded prerequisites support launch readiness; final approval remains with the launch lead.');
  assert(result.citation_check && !result.citation_check.unavailable_path_source_ids.length);
  await page.getByText('MODEL + GRAPH',{exact:true}).waitFor();
  await page.getByText('Check evidence coverage',{exact:true}).click();
  await page.screenshot({path:'artifacts/release-agent-desktop.png',fullPage:true});
  await new Promise(resolve=>setTimeout(resolve,4000));
  assert.deepEqual(await (await page.request.get('/api/overview')).json(),before);
  fs.writeFileSync('artifacts/release-agent-ui.json',JSON.stringify({verified_at:new Date().toISOString(),live:true,graph,state_unchanged:true,result},null,2));
 } finally {await context.close();fs.copyFileSync(await page.video().path(),'artifacts/CONTINUUM-live-agent-demo.webm');await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
