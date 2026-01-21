
const fs = require('fs/promises');
const path = require('path');
console.log("Running Cruise Test.");

let expectedCruiseNames;
if (__dirname === "/tests") {
    expectedCruiseNames = [
        "ar77", "en617", "hrs2303", "ae2426", "at46"
    ];
}
else {
    expectedCruiseNames = [
        "ae2426", "ar16", "ar22", "ar24a", "ar24b", "ar24c", "ar28a", "ar28b", "ar31a","ar31b",
        "ar31c", "ar32", "ar34a", "ar34b", "ar38", "ar39a", "ar39b", "ar44", "ar48a", "ar48b",
        "ar52a", "ar52b", "ar61a", "ar61b", "ar62", "ar63", "ar66a", "ar66b", "ar70b", "ar75",
        "ar77", "ar78", "ar79", "ar80", "ar82a", "ar82b", "ar87a", "ar87b", "ar88", "ar91",
        "ar92", "ar95", "ar96", "ar98a", "ar98b", "at46",
        "en608", "en617", "en627", "en644", "en649", "en655", "en657", "en661", "en668",
        "en685", "en687", "en688", "en695", "en706", "ae2426",  "en712", "en715", "en720", "en727", "hrs2303"
    ];
}

const readme = {
    ar77: '08-08-2025 Taylor', en617: 'README EN617', hrs2303: ' hrs2303_###.as',
    ae2426: '5/9/2025 - Taylor', 'at46': 'README for cruise AT46'
};

var myArgs = process.argv.slice(2);

async function getData() {
    try {

        if (myArgs[0] == 'public') {
            url = `https://nes-lter-api.whoi.edu`;
        }
        else {
            url = `http://localhost:8000`;
        }

        const response = await fetch(`${url}/api/ctd/cruises/get/all`);
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }

        const data = await response.text();

        const missing = [];

        for (const cruiseName of expectedCruiseNames) {
            if (!data.includes(cruiseName.toUpperCase())) {
                missing.push(cruiseName);
            }
        }

        if (missing.length === 0) {
            console.log("All expected cruise names were found.");
            console.log("Cruise Get All test successful.");
        } else {
            console.log("Missing cruise names:", missingCruises);
            console.log("Cruise Get All test failed.");
        }

    } catch (error) {
        console.error("Error fetching cruise data:", error);
    }


    for (const cruise of expectedCruiseNames) {
        error = false;
        try {
            const response = await fetch(`${url}/api/ctd/cruises/get/${encodeURIComponent(cruise)}`);
            if (!response.ok) {
                throw new Error('HTTP error ' + response.status);
            }

            const data = await response.json();

            if (data.name && data.name.includes(cruise)) {
                console.log(`Cruise Get test for "${cruise}" successful.`);
            } else {
                error = true;
                console.log(`Cruise Get test for "${cruise}" failed.`);
            }

        } catch (err) {
            console.error(`Error fetching "${cruise}":`, err.message);
        }
    }

    if (error) {
        console.log(`Cruise Get test for all cruises failed.`);
    } else {
        console.log(`Cruise Get test for all cruises successful.`);
    }

    for (const cruise of Object.keys(readme)) {
        try {
            const response = await fetch(`${url}/api/ctd/cruises/readme/${cruise}`);
            if (!response.ok) {  
                throw new Error('HTTP error ' + response.status);
            }
            const data = await response.text();

            if (data.includes(readme[cruise])) {
                console.log(`${cruise} Cruise Get README test successful.`);
            } else {
                console.log(`${cruise} Cruise Get README test failed.`);
            }
        } catch (err) {
            console.log(`${cruise} Cruise Get README test failed.`);
            console.error('Error:', err);
        }
    }

    try {
        const response = await fetch(`${url}/api/ctd/cruises/readme`);
        if (!response.ok) {
            throw new Error('HTTP error ' + response.status);
        }
        const data = await response.text();

        if (data.includes('README raw subfolder in ims_data_root folder in nes-lter shared storage')) {
            console.log(`Cruise Get All README test successful.`);
        } else {
            console.log(`Cruise Get All README test failed.`);
        }
    } catch (err) {
        console.log(`Cruise Get All README test failed.`);
        console.error('Error:', err);
    }

    var token;
    const tokenPath = path.resolve(__dirname, 'token.txt');
    if (__dirname === "/tests") {
        token = (await fs.readFile("/data/token.txt", 'utf-8')).trim();
    }
    else {
        const dataPath = tokenPath.replace('\\tests\\', '\\data\\');
        token = (await fs.readFile(dataPath, 'utf-8')).trim();
    }    

    try {
        const response = await fetch(`${url}/api/ctd/cruises/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                "name": 'test',
                "vessel_name": 'Neil Armstrong',
                "start_time": '2021-11-03 21:20:00+00:00',
                "end_time": '2022-11-03 21:20:00+00:00'
            })
        });

        const data = await response.json();

        if (!response.ok) {
            console.log(data.detail)
            throw new Error('HTTP error ' + response.status);
        }

        if (data.status == 'success') {
            console.log('Add Cruise test successful.');
        } else {
            console.log('Add Cruise test failed.');
        }

    }
    catch (err) {
        console.log('Add Cruise test failed.');
        console.error('Error:', err);
    }

    try {
        const response = await fetch(`${url}/api/ctd/cruises/update/test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                "vessel_name": 'Endeavor',
                "start_time": '2021-11-03 21:20:00+00:00',
                "end_time": '2022-11-03 21:20:00+00:00'
            })
        });

        const data = await response.json();

        if (!response.ok) {
            console.log(data.detail);
            throw new Error('HTTP error ' + response.status);
        }

        if (data.vessel_name == 'Endeavor') {
            console.log('Modify Cruise test successful.');
        } else {
            console.log('Modify Cruise test failed.');
        }

    }
    catch (err) {
        console.log('Modify Cruise test failed.');
        console.error('Error:', err);
    }

    try {
        const response = await fetch(`${url}/api/ctd/cruises/delete/test`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) {
            throw new Error('HTTP error ' + response.status);
        }
        const data = await response.json();

        if (data.message == "Cruise test deleted.") {
            console.log('Delete Cruise test successful.');
        } else {
            console.log('Delete Cruise test failed.');
        }

    }
    catch (err) {
        console.log('Delete Cruise test failed.');
        console.error('Error:', err);
    }

}

getData();

