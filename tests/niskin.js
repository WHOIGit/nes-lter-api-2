const fs = require('fs/promises');
const path = require('path');
console.log("Running Niskin Test.");

const cruises = ["ar77", "en617", "hrs2303", "ae2426", "at46"];

const lineCounts = { ar77: 24, en617: 6, hrs2303: 12, ae2426: 24, at46: 4 };

var myArgs = process.argv.slice(1);

async function getData(cruise) {

    if (myArgs[1] == 'public') {
        url = `https://mullen.whoi.edu`;
    }
    else {
        url = `http://localhost:8000`;
    }

    try {
        const response = await fetch(`${url}/api/ctd/niskins/get/all/${cruise}/10`);
        if (!response.ok) {
            throw new Error('HTTP error ' + response.status);
        }
        const data = await response.json();

        const expected = lineCounts[cruise];

        if (data.length === expected) {
            console.log(`${cruise} Niskins Get All test successful.`);
        }
        else {
            console.log(`${cruise} Niskins for All are missing.`);
            console.log(`${cruise} Niskins Get All test failed.`);
        }
    } catch (err) {
        console.log(`${cruise} Niskins Get All test failed.`);
        console.error('Error:', err);
    }

  try {
      const response = await fetch(`${url}/api/ctd/niskins/get/${cruise}/10/1`);
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();
   
      if (data.cruise_name === `${cruise}` && data.cast_number === '10' && data.number === 1) { 
          console.log(`${cruise} Niskin Get Single test successful.`);
      } else {
          console.log(`${cruise} Niskin Get Single test failed.`);
      }

  } catch (err) {
      console.log(`${cruise} Niskin Get Single test failed.`);
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
        const response = await fetch(`${url}/api/ctd/niskins/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                "cruise_name": `${cruise}`,
                "cast_number": "1",
                "number":99,
                "latitude": 40,
                "longitude": -70,
                "depth": 0
            })
        });

        const data = await response.json();

        if (!response.ok) {
            console.log(data.detail);
            throw new Error('HTTP error ' + response.status);
        }

        if (data.status === 'success') {
            console.log(`${cruise} Add Niskin 99 test successful.`);
        } else {
            console.log(`${cruise} Add Niskin 99 test failed.`);
        }

    }
    catch (err) {
        console.log(`${cruise} Add Niskin test failed.`);
        console.error('Error:', err);
    }

    try {
        const response = await fetch(`${url}/api/ctd/niskins/update/${cruise}/1/99`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                "latitude": 41,
                "longitude": -72,
                "depth": 0
            })
        });

        const data = await response.json();

        if (!response.ok) {
            console.log(data.detail);
            throw new Error('HTTP error ' + response.status);
        }

        if (data.status === 'success') {
            console.log(`${cruise} Modify Niskin 99 test successful.`);
        } else {
            console.log(`${cruise} Modify Niskin 99 test failed.`);
        }

    }
    catch (err) {
        console.log(`${cruise} Modify Niskin 99 test failed.`);
        console.error('Error:', err);
    }

    try {
        const response = await fetch(`${url}/api/ctd/niskins/delete/${cruise}/1/99`, {
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

        if (data.message === `Niskin 99 on cruise ${cruise} for cast 1 deleted.`) {
            console.log(`${cruise} Delete Niskin 99 test successful.`);
        } else {
            console.log(`${cruise} Delete Niskin 99 test failed.`);
        }

    }
    catch (err) {
        console.log(`${cruise} Delete Niskin 99 test failed.`);
        console.error('Error:', err);
    }
  
}

async function runAll() {
    for (const cruise of cruises) {
        await getData(cruise);
    }
}

runAll();
