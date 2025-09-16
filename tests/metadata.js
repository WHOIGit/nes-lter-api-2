console.log("Running Metadata Test.");

async function getData() {
  try {
    const response = await fetch('http://localhost:8000/api/ctd/metadata/ar77');
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
      }

    const data = await response.text();

    const lines = data
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0); 

    if (lines.length == 36)
      {
        console.log('Metadata test successful.');
    }
    else {
        console.log('Metadata test missing data.');
        console.log('Metadata test failed.');
    }
  } catch (err) {
    console.log('Metadata test failed.');
    console.error('Error:', err);
  }

}

getData();
