/* Real constrained dragging and production Python results for the final JSXGraph trial. */
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const path = require('node:path');

module.exports = async function verifyJsxLab(context, galleryBase, output) {
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    page.on('console', (message) => {if (message.type() === 'error') errors.push(message.text());});
    page.setDefaultTimeout(15000);
    const ready = async () => {
        await page.waitForFunction(() => {
            const main=document.getElementById('lab-main');
            return main?.dataset.state==='error'||main?.dataset.solveState==='error'||(main?.dataset.state==='ready'&&main?.dataset.solveState==='ready');
        },null,{timeout:120000});
        assert.equal(await page.locator('#lab-main').getAttribute('data-solve-state'),'ready',await page.locator('#solve-status').innerText());
    };
    const data = () => page.evaluate(() => {
        const lab = window.JsxFbdLab;
        return {state:lab.state,inputs:lab.physicalInputs(),result:lab.result};
    });
    const near = (actual,expected,tolerance=1e-7) => assert.ok(Math.abs(actual-expected)<tolerance, actual+' ≈ '+expected);
    const reference = async () => {
        const sample = await data();
        const expected = JSON.parse(execFileSync('python3', ['-c',
            'import json, sys\nfrom pycalcs.stability import evaluate_stability, free_body_diagram\ne = evaluate_stability(**json.load(sys.stdin))\nprint(json.dumps({"equilibrium":e,"free_body":free_body_diagram(e)}))'
        ], {input:JSON.stringify(sample.inputs),cwd:path.resolve(__dirname,'../..'),encoding:'utf8'}));
        near(sample.result.equilibrium.normal_reaction,expected.equilibrium.normal_reaction);
        near(sample.result.free_body.sections.E3.reaction[0],expected.free_body.sections.E3.reaction[0]);
        for (const actual of sample.result.free_body.sections.E3.forces) {
            const force = expected.free_body.sections.E3.forces.find((item)=>item.id===actual.id);
            near(actual.restoring_moment,force.restoring_moment);
        }
    };
    const geometry = async () => {
        const failures = await page.evaluate(() => {
            const l=window.JsxFbdLab,failures=[],close=(a,b)=>Math.abs(a-b)<1e-7;
            if(!close(l.application.X(),.4))failures.push('A left the mast');
            if(l.application.Y()<.15-1e-8||l.application.Y()>1.2+1e-8)failures.push('A escaped the segment');
            if(!close(l.application.Dist(l.direction),.38))failures.push('Direction escaped the circle');
            if(l.primaryArrow.point1!==l.application)failures.push('Force is not attached to A');
            const vector=[l.forceTip.X()-l.application.X(),l.forceTip.Y()-l.application.Y()];
            const angle=l.state.angle*Math.PI/180,length=Math.hypot(...vector);
            if(!close(vector[0]/length,Math.cos(angle))||!close(vector[1]/length,Math.sin(angle)))failures.push('Drawn force direction differs from solver input');
            const arm=[l.foot.X()-l.pivot.X(),l.foot.Y()-l.pivot.Y()];
            const toFoot=[l.foot.X()-l.application.X(),l.foot.Y()-l.application.Y()];
            if(!close(vector[0]*arm[0]+vector[1]*arm[1],0))failures.push('Arm is not perpendicular');
            if(!close(vector[0]*toFoot[1]-vector[1]*toFoot[0],0))failures.push('Foot left the line of action');
            for(const force of l.forceArrows) {
                if(force.reaction && force.arrow.point2!==l.reactionPoint)failures.push(force.id+' detached from R');
            }
            if(l.solvedRevision!==l.revision)failures.push('Stale result');
            if(document.documentElement.scrollWidth>innerWidth+1)failures.push('Page overflows');
            return failures;
        });
        assert.deepEqual(failures,[]);
    };
    const slider = async (id,value) => {
        const pending = await page.locator('#'+id).evaluate((input,value)=>{
            input.value=String(value);input.dispatchEvent(new Event('input',{bubbles:true}));
            return {hidden:!window.JsxFbdLab.reactionPoint.visPropCalc.visible,moment:document.getElementById('moment-value').textContent};
        },value);
        assert.equal(pending.hidden,true,'Hide the old reaction while a changed load is calculating');
        assert.equal(pending.moment,'…');
        await ready();
    };
    const drag = async (pointName, target) => {
        const points = await page.evaluate(({pointName,target})=>{
            const lab=window.JsxFbdLab,box=document.getElementById('lab-board').getBoundingClientRect();
            const point=lab[pointName];
            const coordinates=new window.JXG.Coords(window.JXG.COORDS_BY_USER,target,lab.board);
            return {
                start:[box.x+point.coords.scrCoords[1],box.y+point.coords.scrCoords[2]],
                end:[box.x+coordinates.scrCoords[1],box.y+coordinates.scrCoords[2]],
            };
        },{pointName,target});
        await page.mouse.move(...points.start);
        await page.mouse.down();
        await page.mouse.move(...points.end,{steps:12});
        // JSXGraph limits pointer updates to its animation cadence.
        await page.waitForTimeout(60);
        await page.mouse.move(...points.end);
        await page.waitForTimeout(60);
        await page.mouse.up();
        await page.waitForTimeout(120);
        await ready();
    };

    await page.goto(new URL('jsxgraph-lab.html',galleryBase).href);
    await ready();
    await page.locator('#settings-open').click();
    await page.locator('#theme-select').selectOption('light');
    await page.locator('#settings-close').click();
    await geometry();
    await reference();
    assert.ok(await page.locator('.lab-measure').isVisible(),'The native measurement label must be visible');
    await page.screenshot({path:output+'/jsx-lab-light.png',fullPage:true});
    const initialAngle=(await data()).state.angle;
    await drag('application',[.4,1.08]);
    near((await data()).state.height,1.08,.015);
    near((await data()).state.angle,initialAngle,.1);
    await geometry();
    await drag('direction',[.78,1.08]);
    const angle=(await data()).state.angle;
    assert.ok(angle<2||angle>358,'The direction handle must rotate the force');
    await geometry();
    await reference();

    // Native segment constraints must stop a drag above the allowed mast.
    await drag('application',[.4,1.5]);
    near((await data()).state.height,1.2,.005);
    await page.locator('#preset-through').click();
    await ready();
    near(await page.evaluate(()=>window.JsxFbdLab.pivot.Dist(window.JsxFbdLab.foot)),0);
    near((await data()).result.free_body.sections.E3.forces.find((f)=>f.id==='P1').restoring_moment,0);
    assert.equal(await page.locator('#moment-kind').innerText(),'Zero moment');
    await geometry();

    // Vertical, horizontal, restoring and tipping directions, including outside reactions.
    for (const angle of [0,90,180,270,359]) {
        await slider('load-angle',angle);
        await slider('load-force',600);
        await geometry();
        await reference();
    }
    await slider('load-height',1);
    await slider('load-angle',180);
    assert.equal((await data()).result.equilibrium.status,'beyond');
    assert.equal(await page.locator('#solve-status').getAttribute('data-status'),'beyond');

    await page.locator('#preset-crowded').click();
    await ready();
    assert.equal((await data()).result.free_body.sections.E3.forces.filter((f)=>Math.hypot(...f.vector)>1e-7).length,6);
    await page.screenshot({path:output+'/jsx-lab-crowded-auto.png',fullPage:true});
    await page.locator('#auto-labels').uncheck();
    assert.equal(await page.evaluate(()=>window.JsxFbdLab.labeledObjects.every(({object})=>!object.label.visProp.autoposition)),true);
    await page.screenshot({path:output+'/jsx-lab-crowded-fixed.png',fullPage:true});
    await page.locator('#auto-labels').check();
    await page.locator('#show-construction').uncheck();
    assert.equal(await page.evaluate(()=>window.JsxFbdLab.arm.visPropCalc.visible),false);
    await page.locator('#show-construction').check();
    const zoom=await page.evaluate(()=>window.JsxFbdLab.board.zoomX);
    await page.locator('#zoom-in').click();
    assert.ok(await page.evaluate((before)=>window.JsxFbdLab.board.zoomX>before,zoom));
    await page.locator('#fit-board').click();
    await page.locator('#load-height').focus();
    const beforeHeight=(await data()).state.height;
    await page.keyboard.press('ArrowRight');
    await ready();
    near((await data()).state.height,beforeHeight+.01,.001);
    assert.equal(await page.evaluate(()=>window.JsxFbdLab.application.label.plaintext),'A');
    await page.locator('#settings-open').click();
    await page.locator('#theme-select').selectOption('dark');
    await page.locator('#settings-close').click();
    await geometry();
    await page.screenshot({path:output+'/jsx-lab-dark.png',fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.waitForTimeout(150);
    await geometry();
    await page.screenshot({path:output+'/jsx-lab-mobile.png',fullPage:true});
    await page.locator('#copy-link').click();
    assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),page.url());
    const saved=(await data()).state;
    await page.reload();
    await ready();
    near((await data()).state.height,saved.height,.0001);
    near((await data()).state.angle,saved.angle,.0001);
    assert.equal((await data()).state.crowded,true);
    assert.equal(await page.locator('body').getAttribute('data-theme'),'dark');
    await slider('load-height',1.2);
    await slider('load-force',600);
    await slider('load-angle',0);
    await page.locator('#fit-board').click();
    assert.equal(await page.evaluate(()=>{
        const lab=window.JsxFbdLab,[left,top,right,bottom]=lab.board.getBoundingBox();
        return lab.forceArrows.every(({arrow})=>[arrow.point1,arrow.point2].every((point)=>
            point.X()>=left&&point.X()<=right&&point.Y()>=bottom&&point.Y()<=top));
    }),true,'Fit must include outside reaction arrows on a narrow screen');
    await page.locator('#preset-reset').click();
    await ready();
    near((await data()).state.height,.85);
    assert.equal((await data()).state.crowded,false);
    await geometry();
    assert.deepEqual(errors,[]);
    await page.close();
    return {passed:true,realDragging:true,pythonReference:true,labels:true,keyboard:true,mobile:true};
};
