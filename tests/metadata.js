console.log("Running Metadata Test.");

const cruises = ["ar77", "en617", "hrs2303", "ae2426", "at46"];

// Expected line counts
const lineCounts = { ar77: 36, en617: 36, hrs2303: 13, ae2426: 18, at46: 24 };

var myArgs = process.argv.slice(2);

async function getData(cruise) {

    if (myArgs[0] == 'public') {
        url = `https://nes-lter-api.whoi.edu`;
    }
    else {
        url = `http://localhost:8000`;
    }

    try {
        const response = await fetch(`${url}/api/ctd/metadata/${cruise}`);
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }

        const data = await response.text();

        const lines = data
            .split("\n")
            .map(line => line.trim())
            .filter(line => line.length > 0);

        const expected = lineCounts[cruise];

        if (lines.length === expected) {
            console.log(`${cruise} Metadata test successful.`);
        } else {
            console.log(`${cruise} Metadata test missing data.`);
            console.log(`${cruise} Metadata test failed. (Expected ${expected}, got ${lines.length})`);
        }
    } catch (err) {
        console.log(`${cruise} Metadata test failed.`);
        console.error("Error:", err);
    }
}

async function runAll() {
    for (const cruise of cruises) {
        await getData(cruise);
    }
}

runAll();

