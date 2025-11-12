console.log("Running Chl Test.");

const cruises = ["ar77", "en617", "hrs2303", "ae2426", "at46"];

// Expected line counts - hrs2303 & ae2426 have no data
const lineCounts = { ar77: 315, en617: 339, hrs2303: 1, ae2426: 1, at46: 327 };

var myArgs = process.argv.slice(2);

async function getData() {

    if (myArgs[0] == 'public') {
        url = `https://nes-lter-api.whoi.edu`;
    }
    else {
        url = `http://localhost:8000`;
    }

    for (const cruise of cruises) {
        try {
            const response = await fetch(`${url}/api/chl/${cruise}`);
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
                console.log(`${cruise} Chl Get test successful.`);
            }
            else {
                console.log(`${cruise} Chl values are missing.`);
                console.log(`${cruise} Chl Get test failed.`);
            }
        } catch (err) {
            console.log(`${cruise} Chl Get test failed.`);
            console.error('Error:', err);
        }
    }

    try {
        const response = await fetch(`${url}/api/chl/all`);
        if (!response.ok) {
            throw new Error('HTTP error ' + response.status);
        }

        const data = await response.text();

        const lines = data
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0);

        if (process.env.GITHUB_ACTIONS === 'true') {
            if (lines.length == 979) {
                console.log('Chl Get All test successful.');
            }
            else {
                console.log('Chl Get All values are missing.');
                console.log('Chl Get All test failed.');
            }
        }
        else {
            if (lines.length == 7259) {
                console.log('Chl Get All test successful.');
            }
            else {
                console.log('Chl Get All values are missing.');
                console.log('Chl Get All test failed.');
            }
        }
    } catch (err) {
        console.log('Chl Get All test failed.');
        console.error('Error:', err);
    }
}

getData();
