console.log("Running HPLC Test.");

async function getData() {
  try {
    const response = await fetch('http://localhost:8000/api/hplc/ar77');
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
      }

    const data = await response.text();

    const lines = data
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0); 

    if (lines.length == 34)
      {
        console.log('HPLC Get test successful.');
    }
    else {
        console.log('HPLC are missing.');
        console.log('HPLC Get test failed.');
    }
  } catch (err) {
    console.error('Error:', err);
  }


}

getData();
