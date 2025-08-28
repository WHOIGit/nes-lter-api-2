console.log("Running Chl Test.");

async function getData() {
  try {
    const response = await fetch('http://localhost:8000/api/chl/ar77');
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
      }

    const data = await response.text();

    const lines = data
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0); 

    if (lines.length == 315)
      {
        console.log('Chl Get test successful.');
    }
    else {
        console.log('Chl values are missing.');
        console.log('Chl Get test failed.');
    }
  } catch (err) {
    console.error('Error:', err);
  }

try {
    const response = await fetch('http://localhost:8000/api/chl/all');
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }

    const data = await response.text();

    const lines = data
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);

    if (lines.length == 7255) {
        console.log('Chl Get All test successful.');
    }
    else {
        console.log('Chl Get All values are missing.');
        console.log('Chl Get All test failed.');
    }
} catch (err) {
    console.error('Error:', err);
}
}

getData();
