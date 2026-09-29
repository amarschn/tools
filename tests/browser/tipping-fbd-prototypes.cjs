/* Serve the repo on port 8157. These checks target the detached-arrow regression. */
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/opt/homebrew/lib/node_modules/@playwright/test');
const base=process.env.TIPPING_FBD_URL||'http://127.0.0.1:8157/tools/tipping-stability/prototypes/';
const output='/private/tmp/tipping-fbd-prototypes';

(async()=>{
    await fs.mkdir(output,{recursive:true});
    const browser=await chromium.launch({headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
    try{
        const context=await browser.newContext({viewport:{width:1500,height:1050},colorScheme:'light'});
        await context.grantPermissions(['clipboard-read','clipboard-write']);
        await context.route('**/www.googletagmanager.com/**',(route)=>route.fulfill({body:'',contentType:'application/javascript'}));
        await context.route('**/google-analytics.com/**',(route)=>route.fulfill({body:''}));
        const page=await context.newPage(),errors=[];
        page.on('pageerror',(e)=>errors.push(e.message));
        page.on('console',(m)=>{if(m.type()==='error')errors.push(m.text());});
        await page.goto(base);
        await page.locator('#prototype-main[data-state="ready"]').waitFor({timeout:30000});
        await page.waitForTimeout(300);
        const boot=await page.evaluate(()=>({threeError:window.FbdStudies?.threeError,board:!!window.FbdStudies?.board,boardMessage:document.getElementById('jsx-board').textContent,assembly:!!window.FbdStudies?.assembly}));
        await page.screenshot({path:`${output}/boot.png`,fullPage:true});
        assert.ok(boot.assembly&&boot.board,JSON.stringify({boot,errors}));
        const check=async()=>{
            const problems=await page.evaluate(()=>{
                const failures=[],near=(a,b)=>Math.abs(a-b)<1e-6;
                for(const id of ['a','d','g','h-section']){
                    const scene=document.getElementById('scene-'+id);
                    for(const [force,point,anchorEnd] of [['W','G','1'],['N','R','2']]){
                        const line=scene.querySelector(`[data-force="${force}"] .shaft`),mark=scene.querySelector(`[data-point="${point}"]`);
                        if(!line)continue;
                        if(!near(+line.getAttribute('x'+anchorEnd),+mark.getAttribute('cx'))||!near(+line.getAttribute('y'+anchorEnd),+mark.getAttribute('cy')))failures.push(`${id}: ${force} detached from ${point}`);
                    }
                    if(/NaN|Infinity/.test(scene.innerHTML))failures.push(`${id}: nonfinite geometry`);
                }
                const studies=window.FbdStudies;
                const weight=studies.scenes.b.items.find((p)=>p.type==='arrow'&&p.id==='W');
                if(!near(weight.a[0],weight.b[0])||weight.b[1]<=weight.a[1])failures.push('Canvas: gravity is not vertically down');
                for(const force of studies.assembly.forceArrows){
                    const actual=force.headAtAnchor?force.origin.clone().addScaledVector(force.direction,force.length):force.origin;
                    if(actual.distanceTo(force.anchor)>1e-10)failures.push(`Three.js: ${force.force.id} detached`);
                    const expected=force.force.point;
                    if(actual.toArray().some((x,i)=>Math.abs(x-expected[i])>1e-10))failures.push(`Three.js: ${force.force.id} moved from solver point`);
                }
                if(!studies.board)failures.push('JSXGraph board missing');
                if(document.documentElement.scrollWidth>innerWidth+1)failures.push('Page overflows');
                return failures;
            });
            assert.deepEqual(problems,[]);
        };
        await check();
        await page.screenshot({path:`${output}/gallery-light.png`,fullPage:true});
        for(const scale of ['schematic','proportional']){
            await page.locator('#scale-select').selectOption(scale);
            for(const load of ['level','slope','push','turn','oblique','crowded','threshold','beyond']){
                await page.locator('#case-select').selectOption(load);
                const edges=await page.locator('#edge-select option').evaluateAll((options)=>options.map((o)=>o.value));
                for(const edge of edges){await page.locator('#edge-select').selectOption(edge);await check();}
            }
        }
        await page.locator('#scale-select').selectOption('schematic');
        await page.locator('#case-select').selectOption('level');
        await page.locator('#scene-a [data-force="W"]').focus();
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('#force-select').inputValue(),'W');
        await page.locator('#force-select').selectOption('all');
        await page.locator('#anchor-guides').check();
        await check();
        await page.locator('#anchor-guides').uncheck();
        await page.locator('#case-select').selectOption('slope');
        for(const id of ['a','b','c','d','e','f','g','h']){
            await page.locator(`[data-expand="${id}"]`).click();
            await page.locator(`[data-study="${id}"]`).screenshot({path:`${output}/study-${id}-light.png`});
            await page.locator('#show-all').click();
        }
        const before=await page.evaluate(()=>window.FbdStudies.assembly.camera.position.toArray());
        await page.locator('#camera-right').click();
        const after=await page.evaluate(()=>window.FbdStudies.assembly.camera.position.toArray());
        assert.notDeepEqual(before,after);
        await page.locator('#camera-reset').click();
        const zoom=await page.evaluate(()=>window.FbdStudies.board.zoomX);
        await page.locator('#board-in').click();
        assert.ok(await page.evaluate((old)=>window.FbdStudies.board.zoomX>old,zoom));
        await page.locator('#board-reset').click();
        await page.locator('#study-select').selectOption('h');
        await page.locator('[data-plan-edge="E1"]').focus();
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('#edge-select').inputValue(),'E1');
        assert.equal(await page.locator('#scene-h-section').getAttribute('data-edge'),'E1');
        assert.equal(await page.locator('[data-plan-edge="E1"]').getAttribute('aria-pressed'),'true');
        await page.locator('#show-all').click();
        await page.locator('#case-select').selectOption('crowded');
        await page.locator('#study-select').selectOption('g');
        await page.locator('#scene-g text[data-force="P1"]').focus();
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('#force-select').inputValue(),'P1');
        assert.equal(await page.locator('#scene-g text[data-force="P1"]').evaluate((el)=>el===document.activeElement),true);
        await page.locator('[data-study="g"]').screenshot({path:`${output}/study-g-crowded.png`});
        await page.locator('#show-all').click();
        await page.locator('#force-select').selectOption('all');
        await page.screenshot({path:`${output}/gallery-crowded.png`,fullPage:true});
        await page.locator('#settings-open').click();
        await page.locator('#theme-select').selectOption('dark');
        await page.locator('#settings-close').click();
        await check();
        await page.screenshot({path:`${output}/gallery-dark.png`,fullPage:true});
        await page.locator('#case-select').selectOption('oblique');
        await page.screenshot({path:`${output}/gallery-oblique.png`,fullPage:true});
        // An acceleration along the selected edge must retain its dot/cross and zero moment.
        await page.locator('#case-select').selectOption('turn');
        await page.locator('#edge-select').selectOption('E2');
        await page.locator('#force-select').selectOption('I');
        await check();
        assert.match(await page.locator('#moment-note').innerText(),/projected tipping moment is zero/);
        await page.locator('#case-select').selectOption('oblique');
        await page.locator('#force-select').selectOption('all');
        await page.setViewportSize({width:390,height:844});
        await page.waitForTimeout(300);
        await check();
        await page.screenshot({path:`${output}/gallery-mobile.png`,fullPage:true});
        await page.locator('[data-expand="h"]').click();
        await page.locator('[data-study="h"]').screenshot({path:`${output}/study-h-mobile.png`});
        await page.locator('#scale-select').selectOption('proportional');
        await page.locator('#copy-link').click();
        assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),page.url());
        const saved=page.url();await page.goto(saved);
        await page.locator('#prototype-main[data-state="ready"]').waitFor();
        assert.equal(await page.locator('#case-select').inputValue(),'oblique');
        assert.equal(await page.locator('#scale-select').inputValue(),'proportional');
        assert.equal(await page.locator('[data-study="b"]').isVisible(),false);
        assert.equal(await page.locator('body').getAttribute('data-theme'),'dark');
        assert.deepEqual(errors,[]);
        console.log(JSON.stringify({passed:true,studies:8,cases:8,edgeCases:31,scaleCombinations:62,engines:['SVG','Canvas 2D','Three.js','JSXGraph'],screenshots:output},null,2));
    }finally{await browser.close();}
})().catch((error)=>{console.error(error);process.exitCode=1;});
