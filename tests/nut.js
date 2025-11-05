console.log("Running Nut Test.");

const cruises = ["ar77", "en617", "hrs2303", "ae2426", "at46"];

// Expected line counts - ae2426 has no data
const lineCounts = { ar77: 143, en617: 157, hrs2303: 141, ae2426: 1, at46: 143 };

var myArgs = process.argv.slice(1);

async function getData() {
    let url;

    if (myArgs[1] == 'public') {
        url = `https://nes-lter-api.whoi.edu`;
    }
    else {
        url = `http://localhost:8000`;
    }

    for (const cruise of cruises) {
        try {
            const response = await fetch(`${url}/api/nut/${cruise}`);
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
                console.log(`${cruise} Nut Get test successful.`);
            }
            else {
                console.log(`${cruise} Nut values are missing.`);
                console.log(`${cruise} Nut Get test failed.`);
            }
        } catch (err) {
            console.log(`${cruise} Nut Get test failed.`);
            console.error('Error:', err);
        }
    }

try {
    const response = await fetch(`${url}/api/nut/all`);
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }

    const data = await response.text();

    const lines = data
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);

    if (process.env.GITHUB_ACTIONS === 'true') {
        if (lines.length == 581) {  // only 5 test cruises
            console.log('Nut Get All test successful.');
        }
        else {
            console.log('Nut Get All values are missing.');
            console.log('Nut Get All test failed.');
        }
    }
    else {
        if (lines.length == 4434) {
            console.log('Nut Get All test successful.');
        }
        else {
            console.log('Nut Get All values are missing.');
            console.log('Nut Get All test failed.');
        }
    }
  } catch (err) {
    console.log('Nut Get All test failed.');
    console.error('Error:', err);
  }
}

getData();
