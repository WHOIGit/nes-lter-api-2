const fs = require('fs/promises');
const path = require('path');
console.log("Running Station Test.");

async function getData() {
  try {
    const response = await fetch('http://localhost:8000/api/stations/file');
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
      }

    const data = await response.text();

    const lines = data
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0); 

    if (lines.length == 81)
      {
        console.log('Stations File Get test successful');
    }
    else {
        console.log('Stations are missing');
        console.log('Station File Get test failed');
    }
  } catch (err) {
    console.log('Station File Get test failed');
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
      const response = await fetch('http://localhost:8000/api/stations/add_nearest', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
              "latitude": [41.1133],
              "longitude": [-70.8833],
              "timestamp": ["2018-01-01T14:33:29.527Z"]
          })
    });
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();
   
    if ((data.station == 'L1.5') && (data.distance_km == 0)) { 
        console.log('Station Get Nearest test successful');
    } else {
        console.log('Station Get Nearest test failed');
      }
  } catch (err) {
      console.log('Station Get Nearest test failed');
      console.error('Error:', err);
  }
 
/*  // Joe going to delete this

    try {
        const response = await fetch('http://localhost:8000/api/stations/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                "name": "test",
                "full_name": "test station"
            })
        });

        //TEMP UNTIL FIXED const data = await response.json();

        if (!response.ok) {             //duplicate key error - station file not updated on first run
            console.log(data.detail);
            throw new Error('HTTP error ' + response.status);
        }

        if (data.name == 'test') {
            console.log('Create Station test successful');
        } else {
            console.log('Create Station test failed');
        }

    }
    catch (err) {
        console.log('Create Station test failed');
        console.error('Error:', err);
    }

    try {
        const response = await fetch('http://localhost:8000/api/stations/set_location', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                "station_name": "test",
                "latitude": 41,
                "longitude": -70,
                "start_time": "2025-07-20T14:56:24.240Z",
                "end_time": "2025-08-20T14:56:24.240Z",
                "depth": 50,
                "comment": "this is a test station"
            })
        });

        const data = await response.json();  // THROWS ERROR instead of returning error:  204 error (no content) or A location already exists at the given start_time

        if (!response.ok) {             
            console.log(data.detail);
            throw new Error('HTTP error ' + response.status);
        }

        if (data.name == 'test') {
            console.log('Set Location Station test successful');
        } else {
            console.log('Set Location Station test failed');
        }

    }
    catch (err) {
        console.log('Set Location Station test failed');
        console.error('Error:', err);
    }

  */

   
}

getData();
