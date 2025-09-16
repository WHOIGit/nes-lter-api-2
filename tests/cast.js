const fs = require('fs/promises');
const path = require('path');
console.log("Running Cast Test.");

async function getData() {
  try {
    const response = await fetch('http://localhost:8000/api/ctd/casts/get/ar77');
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();

    if (data.length == 35)
      {
        console.log('Casts Get All test successful');
    }
    else {
        console.log('Casts for All are missing');
        console.log('Casts Get All test failed');
    }
  } catch (err) {
    console.log('Casts Get All test failed');
    console.error('Error:', err);
  }


  try {
    const response = await fetch('http://localhost:8000/api/ctd/cast/get/en608/10');
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.text();
   
    const lines = data
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0); // Remove blank lines

      if (lines.length > 1) {
          console.log('Cast Get Single test successful');
      } else {
          console.log('Cast Get Single test failed');
      }

  } catch (err) {
     console.log('Cast Get Single test failed');
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
        const response = await fetch('http://localhost:8000/api/ctd/casts/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                "cruise_name": "ar77",
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
            throw new Error('HTTP error ' + response.status);
        }

        if (data.status == 'success') {
            console.log('Add Cast test successful.');
        } else {
            console.log('Add Cast test failed.');
        }

    }
    catch (err) {
        console.log('Add Cast test failed.');
        console.error('Error:', err);
    }

    try {
        const response = await fetch('http://localhost:8000/api/ctd/casts/update/ar77/99', {
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
            throw new Error('HTTP error ' + response.status);
        }

        if (data.status == 'success') {
            console.log('Modify Cast test successful.');
        } else {
            console.log('Modify Cast test failed.');
        }

    }
    catch (err) {
        console.log('Modify Cast test failed.');
        console.error('Error:', err);
    }

    try {
        const response = await fetch('http://localhost:8000/api/ctd/casts/delete/ar77/99', {
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

        if (data.message == "Cast 99 on cruise ar77 deleted.") {
            console.log('Delete Cast test successful.');
        } else {
            console.log('Delete Cast test failed.');
        }

    }
    catch (err) {
        console.log('Delete Cast test failed.');
        console.error('Error:', err);
    }

}

getData();
