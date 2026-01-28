const fs = require(`fs/promises`);
const path = require('path');
console.log("Running Cast Test.");

const cruises = ["ar77", "en617", "hrs2303", "ae2426", "at46"];

const lineCounts = { ar77: 35, en617: 35, hrs2303: 12, ae2426: 17, at46: 23 };

var myArgs = process.argv.slice(2);

async function getData(cruise) {
  try {
      if (myArgs[0] == 'public') {
          url = `https://nes-lter-api.whoi.edu`;
      }
      else {
          url = `http://localhost:8000`;
      }

    const response = await fetch(`${url}/api/ctd/casts/get/${cruise}`);

    if (!response.ok) {
      throw new Error(`HTTP error ` + response.status);
    }
    const data = await response.json();

    const expected = lineCounts[cruise];

    if (data.length === expected) 
      {
        console.log(`${cruise} Casts Get All test successful.`);
    }
    else {
        console.log(`${cruise} Casts Get All are missing.`);
        console.log(`${cruise} Casts Get All test failed.`);
    }
  } catch (err) {
      console.log(`${cruise} Casts Get All test failed.`);
      console.error(`Error:`, err);
  }


  try {
    const response = await fetch(`${url}/api/ctd/cast/get/${cruise}/10`);

    if (!response.ok) {
        throw new Error(`HTTP error ` + response.status);
    }
    const data = await response.text();
   
    const lines = data
        .split(`\n`)
        .map(line => line.trim())
        .filter(line => line.length > 0); // Remove blank lines

    if (lines.length > 1) {
        console.log(`${cruise} Cast Get Single test successful.`);
    } else {
        console.log(`${cruise} Cast Get Single test failed.`);
    }

  } catch (err) {     
      console.log(`${cruise} Cast Get Single test failed.`);
      console.error(`Error:`, err);
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
        const response = await fetch(`${url}/api/ctd/casts/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                "cruise_name": `${cruise}`,
                "number": "99",
                "latitude": 40,
                "longitude": -70,
                "depth": 0,
                "start_time": "2024-08-19T14:17:02.878Z",
                "end_time": "2025-08-19T14:17:02.878Z"
            })
        });

        const data = await response.json();

        if (!response.ok) {
            console.log(data.detail);
            throw new Error(`HTTP error ` + response.status);
        }

        if (data.status === `success`) {
            console.log(`${cruise} Add Cast 99 test successful.`);
        } else {
            console.log(`${cruise} Add Cast 99 test failed.`);
        }

    }
    catch (err) {
        console.log(`${cruise} Add Cast 99 test failed.`);
        console.error(`Error:`, err);
    }

    try {
        const response = await fetch(`${url}/api/ctd/casts/update/${cruise}/99`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                "latitude": 41,
                "longitude": -72,
                "depth": 0,
                "start_time": "2024-08-19T14:17:02.878Z",
                "end_time": "2025-08-19T14:17:02.878Z"
            })
        });

        const data = await response.json();

        if (!response.ok) {
            console.log(data.detail);
            throw new Error(`HTTP error ` + response.status);
        }

        if (data.status === `success`) {
            console.log(`${cruise} Modify Cast 99 test successful.`);
        } else {
            console.log(`${cruise} Modify Cast 99 test failed.`);
        }

    }
    catch (err) {
        console.log(`${cruise} Modify Cast 99 test failed.`);
        console.error(`Error:`, err);
    }

    try {
        const response = await fetch(`${url}/api/ctd/casts/delete/${cruise}/99`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) {
            throw new Error(`HTTP error ` + response.status);
        }
        const data = await response.json();

        if (data.message === `Cast 99 on cruise ${cruise} deleted.`) {
            console.log(`${cruise} Delete Cast 99 test successful.`);
        } else {
            console.log(`${cruise} Delete Cast 99 test failed.`);
        }

    }
    catch (err) {
        console.log(`${cruise} Delete Cast 99 test failed.`);
        console.error(`Error:`, err);
    }

}


async function runAll() {
    for (const cruise of cruises) {
        await getData(cruise);
    }
}

runAll();