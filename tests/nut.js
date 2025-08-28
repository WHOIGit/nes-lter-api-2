console.log("Running Nut Test.");

async function getData() {
  try {
    const response = await fetch('http://localhost:8000/api/nut/ar77');
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
      }

    const data = await response.text();

    const lines = data
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0); 

    if (lines.length == 143)
      {
        console.log('Nut Get test successful.');
    }
    else {
        console.log('Nut values are missing.');
        console.log('Nut Get test failed.');
    }
  } catch (err) {
    console.error('Error:', err);
  }

try {
    const response = await fetch('http://localhost:8000/api/nut/all');
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }

    const data = await response.text();

    const lines = data
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);

    if (lines.length == 4434) {
        console.log('Nut Get All test successful.');
    }
    else {
        console.log('Nut Get All values are missing.');
        console.log('Nut Get All test failed.');
    }
} catch (err) {
    console.error('Error:', err);
}
}

getData();
