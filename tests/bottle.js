async function getData() {
  try {
    const response = await fetch('http://localhost:8000/api/ctd/bottles/ar77');
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
      }

    const data = await response.text();

    const lines = data
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0); 

    if (lines.length == 310)
      {
        console.log('Bottles Get All test successful.');
    }
    else {
        console.log('Bottles for All are missing.');
        console.log('Bottles Get All test failed.');
    }
  } catch (err) {
    console.log('Bottles Get All test failed.');
    console.error('Error:', err);
  }


  try {
    const response = await fetch('http://localhost:8000/api/ctd/bottle_summary/ar77');
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.text();
   
    const lines = data
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);

    if (lines.length == 310) { 
        console.log('Bottle Summary test successful.');
    } else {
        console.log('Bottle Summary test failed.');
    }

  } catch (err) {
     console.log('Bottle Summary test failed.');
     console.error('Error:', err);
  }
}

getData();
