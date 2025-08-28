const fs = require('fs/promises');
const path = require('path');
console.log("Running Event Test.");

async function getData() {
  try {
    const response = await fetch('http://localhost:8000/api/events/get/ar77');
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
      }

    const data = await response.text();

    const lines = data
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0); 

    if (lines.length == 166)
      {
        console.log('Events Get test successful.');
    }
    else {
        console.log('Events are missing.');
        console.log('Events Get test failed.');
    }
  } catch (err) {
    console.error('Error:', err);
  }


  try {
      const response = await fetch('http://localhost:8000/api/events/instruments/ar77', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json'
          },
    });
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();
   
    if (data.length == 18) { 
        console.log('Event Get Instruments test successful.');
    } else {
        console.log('Event Get Instruments test failed.');
      }
  } catch (err) {
      console.error('Error:', err);
  }

  try {
    const response = await fetch('http://localhost:8000/api/events/filter/ar77', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
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

    if (data.length == 1) {
        console.log('Event Filter test successful.');
    } else {
        console.log('Event Filter test failed.');
    }

  }
  catch (err) {
     console.error('Error:', err);
  }

try {
    const response = await fetch('http://localhost:8000/api/events/history/ar77');
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();  // returned data can be any length, so just catch errors

    console.log('Events History test successful.');

    } catch (err) {
        console.error('Error:', err);
    }

    var token;
    const tokenPath = path.resolve(__dirname, 'token.txt');
    if (path.basename(process.cwd()) === 'tests') {
        token = (await fs.readFile("token.txt", 'utf-8')).trim();
    }
    else {
        token = (await fs.readFile(tokenPath, 'utf-8')).trim();
    }      

    try {
        const response = await fetch('http://localhost:8000/api/events/edit/ar77/20231011.1311.001', {
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

        if (data.instrument == 'Ship') {
            console.log('Edit Event test successful.');
        } else {
            console.log('Edit Event test failed.');
        }

    }
    catch (err) {
        console.error('Error:', err);
    }

/*   FIX - NEED TO RUN IMPORT EVENTS AFTER THIS
     try {
        const response = await fetch('http://localhost:8000/api/events/delete/ar77', {
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

        if (data.message == "Events on cruise ar77 deleted.") {
            console.log('Delete Event test successful.');
        } else {
            console.log('Delete Event test failed.');
        }

    }
    catch (err) {
        console.error('Error:', err);
    } */
}

getData();
