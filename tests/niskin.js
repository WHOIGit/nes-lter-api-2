const fs = require('fs/promises');
const path = require('path');
console.log("Running Niskin Test.");

async function getData() {
  try {
    const response = await fetch('http://localhost:8000/api/ctd/niskins/get/all/ar77/10');
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();

    if (data.length == 24)
      {
        console.log('Niskins Get All test successful.');
    }
    else {
        console.log('Niskins for All are missing.');
        console.log('Niskins Get All test failed.');
    }
  } catch (err) {
    console.error('Error:', err);
  }

  try {
    const response = await fetch('http://localhost:8000/api/ctd/niskins/get/en608/10/1');
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();
   
      if (data.cruise_name === 'en608' && data.cast_number === '10' && data.number === 1) { 
        console.log('Niskin Get Single test successful.');
      } else {
          console.log('Niskin Get Single test failed.');
      }

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
        const response = await fetch('http://localhost:8000/api/ctd/niskins/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                "cruise_name": "ar77",
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

        if (data.status == 'success') {
            console.log('Add Niskin test successful.');
        } else {
            console.log('Add Niskin test failed.');
        }

    }
    catch (err) {
        console.error('Error:', err);
    }

    try {
        const response = await fetch('http://localhost:8000/api/ctd/niskins/update/ar77/1/99', {
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

        if (data.status == 'success') {
            console.log('Modify Niskin test successful.');
        } else {
            console.log('Modify Niskin test failed.');
        }

    }
    catch (err) {
        console.error('Error:', err);
    }

    try {
        const response = await fetch('http://localhost:8000/api/ctd/niskins/delete/ar77/1/99', {
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

        if (data.message == "Niskin 99 on cruise ar77 for cast 1 deleted.") {
            console.log('Delete Niskin test successful.');
        } else {
            console.log('Delete Niskin test failed.');
        }

    }
    catch (err) {
        console.error('Error:', err);
    }
  
}

getData();
