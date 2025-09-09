// Test script to verify performance improvements in record loading
// This script will measure the time it takes to load the records page

const puppeteer = require('puppeteer');

async function testRecordLoadingPerformance() {
  console.log('🚀 Starting performance test for record loading...\n');
  
  const browser = await puppeteer.launch({ 
    headless: false,
    devtools: true 
  });
  
  const page = await browser.newPage();
  
  // Enable request interception to track API calls
  await page.setRequestInterception(true);
  
  const apiCalls = [];
  
  page.on('request', (request) => {
    const url = request.url();
    if (url.includes('/api/')) {
      apiCalls.push({
        url: url.replace('http://localhost:8000', ''),
        method: request.method(),
        timestamp: Date.now()
      });
    }
    request.continue();
  });
  
  // Navigate to login page first
  console.log('1. Navigating to login page...');
  await page.goto('http://localhost:3000/login');
  
  // Login (you'll need to update these credentials)
  console.log('2. Logging in...');
  await page.waitForSelector('input[name="email"]');
  await page.type('input[name="email"]', 'admin@oneo.com');
  await page.type('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  
  // Wait for navigation to complete
  await page.waitForNavigation();
  console.log('3. Login successful, navigating to pipelines...\n');
  
  // Clear API calls from login
  apiCalls.length = 0;
  
  // Navigate to pipelines page
  await page.goto('http://localhost:3000/pipelines');
  await page.waitForSelector('[data-testid="pipeline-card"], .pipeline-item, a[href*="/pipelines/"]', { timeout: 10000 });
  
  // Click on first pipeline
  console.log('4. Clicking on first pipeline...');
  const startTime = Date.now();
  
  // Click on the first pipeline link to go to records
  await Promise.all([
    page.waitForNavigation(),
    page.click('a[href*="/pipelines/"]:first-child')
  ]);
  
  // Wait for records page to fully load
  await page.waitForSelector('.record-table, [data-testid="record-list"], table', { timeout: 10000 });
  
  const loadTime = Date.now() - startTime;
  
  console.log('\n📊 Performance Results:');
  console.log('=======================');
  console.log(`Total load time: ${loadTime}ms`);
  console.log(`\nAPI Calls Made (${apiCalls.length} total):`);
  
  // Group API calls by endpoint
  const groupedCalls = {};
  apiCalls.forEach(call => {
    const endpoint = call.url.split('?')[0];
    if (!groupedCalls[endpoint]) {
      groupedCalls[endpoint] = [];
    }
    groupedCalls[endpoint].push(call);
  });
  
  Object.entries(groupedCalls).forEach(([endpoint, calls]) => {
    console.log(`\n  ${endpoint}:`);
    calls.forEach((call, index) => {
      const relativeTime = call.timestamp - startTime;
      console.log(`    - ${call.method} at +${relativeTime}ms`);
    });
  });
  
  // Check if there's a loading spinner visible
  const hasLoadingSpinner = await page.evaluate(() => {
    const spinners = document.querySelectorAll('.animate-spin, [data-testid="loading-spinner"], .loading-spinner');
    return spinners.length > 0;
  });
  
  console.log(`\n✅ Loading spinner visible: ${hasLoadingSpinner ? 'YES ❌' : 'NO ✅'}`);
  
  if (loadTime < 500) {
    console.log('✅ Excellent! Page loads in under 500ms');
  } else if (loadTime < 1000) {
    console.log('✅ Good! Page loads in under 1 second');
  } else {
    console.log('⚠️  Page takes over 1 second to load');
  }
  
  // Test pagination (should be instant)
  console.log('\n5. Testing pagination (should be instant)...');
  const paginationStart = Date.now();
  
  // Try to find and click next page button
  try {
    await page.click('[data-testid="next-page"], button:has-text("Next"), button[aria-label="Next page"]');
    await page.waitForTimeout(500); // Wait a bit for any loading
    const paginationTime = Date.now() - paginationStart;
    console.log(`Pagination load time: ${paginationTime}ms`);
    
    if (paginationTime < 100) {
      console.log('✅ Excellent! Pagination is instant');
    }
  } catch (e) {
    console.log('ℹ️  No pagination available (might be only one page of records)');
  }
  
  await browser.close();
  
  console.log('\n🎉 Performance test complete!');
}

// Run the test
testRecordLoadingPerformance().catch(console.error);