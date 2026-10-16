import {chromium} from '../../.tools/node_modules/playwright/index.mjs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
const here=dirname(fileURLToPath(import.meta.url));
const browser=await chromium.launch({headless:true});
try {const page=await browser.newPage({viewport:{width:1400,height:1400}});await page.goto('file://'+resolve(here,'link-stl-card.html'));await page.locator('img').evaluate(e=>e.decode());await page.screenshot({path:resolve(here,'../../public/img/products/kit-listings-01/lc-stl-v2-native.png')});}finally{await browser.close()}
