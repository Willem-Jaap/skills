// Capture a page with headless Google Chrome for a pull request description.
//
// Copy this file to a scratch dir, run `npm i playwright-core` there, then:
//   node screenshot.mjs <url> <out.png> [--width 1440] [--height 900] [--scale 2]
//     [--full] [--dark] [--selector <css>] [--wait <css>] [--delay <ms>] [--storage <state.json>]
//
// --selector crops to the first matching element, --wait blocks until a selector is
// visible (use it to get past skeletons), --storage loads a Playwright storageState
// file for pages behind a login. Extend a copy for clicks or other setup.
import { chromium } from 'playwright-core';

const [url, out, ...rest] = process.argv.slice(2);

if (!url || !out) {
    console.error('usage: node screenshot.mjs <url> <out.png> [options]');
    process.exit(1);
}

const flag = name => rest.includes(`--${name}`);
const option = (name, fallback) => {
    const index = rest.indexOf(`--${name}`);

    return index === -1 ? fallback : rest[index + 1];
};

// Prefer the installed Google Chrome. Without it (a Linux box), fall back to Playwright's
// own Chromium, which `npx playwright-core install chromium` downloads once.
const browser = await chromium.launch({ channel: 'chrome' }).catch(() => chromium.launch());

try {
    const page = await browser.newPage({
        viewport: { width: Number(option('width', 1440)), height: Number(option('height', 900)) },
        deviceScaleFactor: Number(option('scale', 2)),
        colorScheme: flag('dark') ? 'dark' : 'light',
        storageState: option('storage'),
    });

    await page.goto(url, { waitUntil: 'load' });
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});

    const wait = option('wait');
    if (wait) {
        await page.locator(wait).first().waitFor({ state: 'visible' });
    }

    await page.waitForTimeout(Number(option('delay', 500)));

    const selector = option('selector');
    if (selector) {
        await page.locator(selector).first().screenshot({ path: out, animations: 'disabled' });
    } else {
        await page.screenshot({ path: out, fullPage: flag('full'), animations: 'disabled' });
    }

    console.log(out);
} finally {
    await browser.close();
}
