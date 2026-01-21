console.log("Running HPLC Test.");

const cruises = ["ar77", "en617", "hrs2303", "ae2426", "at46"];

// Expected line counts
const lineCounts = { ar77: 34, en617: 30, hrs2303: 32, ae2426: 1, at46: 30 };

var myArgs = process.argv.slice(2);

async function getData(cruise) {

  if (myArgs[0] == 'public') {
      url = `https://nes-lter-api.whoi.edu`;
  }
  else {
      url = `http://localhost:8000`;
    }

  try {
    const response = await fetch(`${url}/api/hplc/${cruise}`);
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
      }

    const data = await response.text();

    const lines = data
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0); 

    const expected = lineCounts[cruise];

    if (lines.length === expected) {
        console.log(`${cruise} HPLC Get test successful.`);
    }
    else {
        console.log(`${cruise} HPLC are missing.`);
        console.log(`${cruise} HPLC Get test failed.`);
    }
  } catch (err) {
    console.log(`${cruise} HPLC Get test failed.`);
    console.error('Error:', err);
    }

}

async function runAll() {
    for (const cruise of cruises) {
        await getData(cruise);
    }
    try {
        const response = await fetch(`${url}/api/hplc/readme`);
        if (!response.ok) {
            throw new Error('HTTP error ' + response.status);
        }
        const data = await response.text();

        if (data.includes('2024-12-10 Taylor - no readme prior to this date. ')) {
            console.log(`HPLC Get README test successful.`);
        } else {
            console.log(`HPLC Get README test failed.`);
        }
    } catch (err) {
        console.log(`HPLC Get README test failed.`);
        console.error('Error:', err);
    }
}

runAll();
