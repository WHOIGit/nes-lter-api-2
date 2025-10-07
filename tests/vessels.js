const fs = require('fs/promises');
const path = require('path');
console.log("Running Vessels Test.");

async function getData() {
  try {
    const response = await fetch('http://localhost:8000/api/ctd/vessels/get/all');
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();
    const vesselNames = data.map(v => v.short_name);

    if (vesselNames.includes("Armstrong") && vesselNames.includes("Atlantis") &&
        vesselNames.includes("Endeavor") && vesselNames.includes("Sharp") &&
        vesselNames.includes("Explorer"))
      {
        console.log('Vessel Get All test successful.');
    }
    else {
        console.log('Vessels are missing.');
        console.log('Vessel Get All test failed.');
    }
  } catch (err) {
    console.log('Vessel Get All test failed.');
    console.error('Error:', err);
  }


  try {
    const response = await fetch('http://localhost:8000/api/ctd/vessels/get/neil armstrong');
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();
   
    if (data.name.includes("Neil Armstrong")) {
        console.log('Vessel Get test successful.');
    }
    else {
        console.log('Vessel Armstrong is missing.');
        console.log('Vessel Get test failed.');
    }
  } catch (err) {
     console.log('Vessel Get test failed.');
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
    const response = await fetch('http://localhost:8000/api/ctd/vessels/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            "designation": 'R/V',
            "name": 'Test Vessel',
            "short_name": 'Test',
            "code": 'ts'
        })
    });
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();

    if (data.status == 'success') {
        console.log('Add Vessel test successful.');
    } else {
        console.log('Add Vessel test failed.');
    }

    }
  catch (err) {
        console.log('Add Vessel test failed.');
        console.error('Error:', err);
    }

    try {
        const response = await fetch('http://localhost:8000/api/ctd/vessels/update/Test Vessel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                "designation": 'R/V',
                "short_name": 'Test 2',
                "code": 'ts'
            })
        });
        if (!response.ok) {
            throw new Error('HTTP error ' + response.status);
        }
        const data = await response.json();

        if (data.short_name == 'Test 2') {
            console.log('Modify Vessel test successful.');
        } else {
            console.log('Modify Vessel test failed.');
        }

    }
    catch (err) {
        console.log('Modify Vessel test failed.');
        console.error('Error:', err);
    }

    try {
        const response = await fetch('http://localhost:8000/api/ctd/vessels/delete/test vessel', {
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

        if (data.message == "Vessel 'test vessel' deleted") {
            console.log('Delete Vessel test successful.');
        } else {
            console.log('Delete Vessel test failed.');
        }

    }
    catch (err) {
        console.log('Delete Vessel test failed.');
        console.error('Error:', err);
    }
}

getData();
