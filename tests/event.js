const fs = require('fs/promises');
const path = require('path');
console.log("Running Event Test.");

const cruises = ["ar77", "en617", "hrs2303", "ae2426", "at46"];

const getCounts = { ar77: 166, en617: 111, hrs2303: 159, ae2426: 168, at46: 266 };
const instCounts = { ar77: 18, en617: 19, hrs2303: 20, ae2426: 21, at46: 19 };
const r2rEvent = {
    ar77: '20231011.1311.001', en617: 'en617-SE-20180720.1404.001', hrs2303: '20230502.1302.001',
    ae2426: '20241106.1442.001', at46: 'at46-SE-20220216.1627.001'
};
const readme = {
    ar77: '2023-11-29 Taylor', en617: 'README EN617', hrs2303: ' hrs2303 > elog',
    ae2426: 'Not Found', 'at46': '2025-10-29 Kate'
};

var myArgs = process.argv.slice(2);

async function getData(cruise) {

  if (myArgs[0] == 'public') {
      url = `https://nes-lter-api.whoi.edu`;
  }
  else {
      url = `http://localhost:8000`;
  }
  try {
    const response = await fetch(`${url}/api/events/get/${cruise}`);
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
      }

    const data = await response.text();

    const lines = data
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0); 

    const expected = getCounts[cruise];

    if (lines.length === expected) 
    {
        console.log(`${cruise} Events Get test successful.`);
    }
    else {
        // at46 has duplicate r2r_events which are suposed to be unique;
        // after edit elog, the duplicate events are not stored in the model
        if ((cruise === 'at46') && (lines.length === 228)) {
            console.log(`${cruise} Events Get test successful.`);
        }
        else { 
            console.log("lines, expected: ", lines.length, expected);
            console.log(`${cruise} Events are missing.`);
            console.log(`${cruise} Events Get test failed.`);
        }
    }
  } catch (err) {
    console.log(`${cruise} Events Get test failed.`);
    console.error('Error:', err);
  }


  try {
      const response = await fetch(`${url}/api/events/instruments/${cruise}`);
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();

    const expected = instCounts[cruise];

    if (data.length === expected) {
        console.log(`${cruise} Event Get Instruments test successful.`);
    } else {
        console.log(`${cruise} Event Get Instruments test failed.`);
      }
  } catch (err) {
      console.log(`${cruise} Event Get Instruments test failed.`);
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
      const response = await fetch(`${url}/api/events/filter/${cruise}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            "instrument": 'Ship',
            "action": 'startCruise'
        })
    });
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();

    if (data.length === 1) {
        console.log(`${cruise} Event Filter test successful.`);
    } else {
        console.log(`${cruise} Event Filter test failed.`);
    }

  }
  catch (err) {
      console.log(`${cruise} Event Filter test failed.`);
     console.error('Error:', err);
  }

try {
    const response = await fetch(`${url}/api/events/history/${cruise}`);
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();  // returned data can be any length, so just catch errors

    console.log(`${cruise} Events History test successful.`);

} catch (err) {
    console.log(`${cruise} Events History test failed.`);
    console.error('Error:', err);
    }

    try {
        const response = await fetch(`${url}/api/events/readme/${cruise}`);
        if (!response.ok) {
            if (cruise !== 'ae2426') {
                throw new Error('HTTP error ' + response.status);
            }
        }
        const data = await response.text();

        if (data.includes(readme[cruise])) {
            console.log(`${cruise} Events Get README test successful.`);
        } else {
            console.log(`${cruise} Events Get README test failed.`);
        }
    } catch (err) {
        console.log(`${cruise} Events Get README test failed.`);
        console.error('Error:', err);
    }

    const r2r = r2rEvent[cruise];

    try {
        const response = await fetch(`${url}/api/events/edit/${cruise}/${r2r}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                "message_id": 1,
                "instrument": "Ship",
                "action": "startCruise",
                "station": "",
                "cast": "",
                "latitude": 41.493007,
                "longitude": -70.680232,
                "comment": "",
                "datetime": null
            })
        });

        const data = await response.json();

        if (!response.ok) {
            console.log(data.detail);
            throw new Error('HTTP error ' + response.status);
        }

        if (data.instrument === 'Ship') {
            console.log(`${cruise} Edit Event test successful.`);
        } else {
            console.log(`${cruise} Edit Event test failed.`);
        }

    }
    catch (err) {
        console.log(`${cruise} Edit Event test failed.`);
        console.error('Error:', err);
    }
}

async function runAll() {
    for (const cruise of cruises) {
        await getData(cruise);
    }
}

runAll();
