console.log("Running Underway Test.");

async function getData() {
  try {
    const response = await fetch('http://localhost:8000/api/underway/get/ar77');
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
      }

    const data = await response.text();

    const lines = data
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0); 

    if (lines.length == 8192)
      {
        console.log('Underway Get test successful.');
    }
    else {
        console.log('Underway are missing.');
        console.log('Underway Get test failed.');
    }
  } catch (err) {
    console.error('Error:', err);
  }


  try {
      const response = await fetch('http://localhost:8000/api/underway/get_column_headers/ar77');
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();
   
    if (data.metadata.num_columns == 40) { 
        console.log('Underway Get Column Headers test successful.');
    } else {
        console.log('Underway Get Column Headers test failed.');
      }
  } catch (err) {
      console.error('Error:', err);
  }

  try {
    const response = await fetch('http://localhost:8000/api/underway/find/2023-10-11/2023-10-13');
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();

      if (data[0].file_name == 'ar77_underway.csv') {
        console.log('Underway Find test successful.');
    } else {
        console.log('Underway Find test failed.');
    }

  } catch (err) {
     console.error('Error:', err);
    }


}

getData();
