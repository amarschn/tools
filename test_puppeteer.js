const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));

  await page.goto('http://localhost:8000/tools/rotor-balance/', { waitUntil: 'networkidle' });
  
  // wait for calculate button to say "Calculate"
  await page.waitForFunction(() => document.getElementById('calculate-btn').textContent === 'Calculate', { timeout: 10000 }).catch(e => console.log('Timeout waiting for button'));
  
  console.log('Button text:', await page.textContent('#calculate-btn'));
  
  await page.click('#calculate-btn');
  
  // Wait a moment for rendering
  await page.waitForTimeout(1000);
  
  console.log('Results:', await page.innerHTML('#results-display'));
  
  await browser.close();
})();
